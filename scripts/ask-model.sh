#!/usr/bin/env bash
# Ask a single council member a question. Prompt on stdin, answer on stdout.
#
#   ./scripts/ask-model.sh <model-slug> [reasoning-effort] < prompt.md
#
# Codex models route through the local codex-router, which exposes both the
# OpenAI models and the opencode-go/* namespace. We pass --ignore-user-config
# because ~/.codex/config.toml currently carries an [agents] table that
# codex-cli 0.144.2 cannot parse (written by codex-router); the router's
# base_url and model catalog are re-supplied here so nothing is lost and the
# user's config is never modified.
set -uo pipefail

MODEL="${1:?usage: ask-model.sh <model-slug> [effort]}"
EFFORT="${2:-high}"
# CODEX_BIN may already be exported in the environment pointing at a path that
# no longer exists, so validate it rather than trusting it.
CODEX="/c/Users/Srijan/.codex/.sandbox-bin/codex.exe"
if [ -n "${COUNCIL_CODEX_BIN:-}" ] && [ -x "${COUNCIL_CODEX_BIN}" ]; then
  CODEX="${COUNCIL_CODEX_BIN}"
fi
[ -x "$CODEX" ] || { echo "codex binary not found at $CODEX" >&2; exit 127; }
CFG="$HOME/.codex/config.toml"

PROMPT_FILE="$(mktemp)"
trap 'rm -f "$PROMPT_FILE"' EXIT
cat > "$PROMPT_FILE"

case "$MODEL" in
  agy:*)
    AGY_MODEL="${MODEL#agy:}"
    # NOTE: ~/tools/bin is in the registry PATH but may be missing from an
    # inherited (stale) process PATH, so agy is addressed by absolute path.
    # This is the Antigravity agent CLI, NOT the Antigravity IDE launcher in
    # AppData\Local\Programs\Antigravity\bin -- that one is Electron and
    # silently forwards --print to Chromium.
    AGY_BIN="${AGY_BIN:-/c/Users/Srijan/tools/bin/agy.exe}"
    "$AGY_BIN" --sandbox --print-timeout "${AGY_TIMEOUT:-10m0s}" \
      --model "$AGY_MODEL" --print "$(cat "$PROMPT_FILE")"
    ;;
  *)
    BASEURL=$(grep -E '^openai_base_url' "$CFG" | sed 's/.*= *"//; s/"$//')
    CATALOG=$(grep -E '^model_catalog_json' "$CFG" | sed 's/.*= *"//; s/"$//')
    "$CODEX" exec --ignore-user-config \
      -c openai_base_url="$BASEURL" \
      -c model_catalog_json="$CATALOG" \
      -c model_reasoning_effort="$EFFORT" \
      -c sandbox_mode="read-only" \
      -c approval_policy="never" \
      --skip-git-repo-check --ephemeral \
      -m "$MODEL" - < "$PROMPT_FILE" 2>&1 \
      | grep -vE 'failed to connect to websocket|Reconnecting\.\.\.'
    ;;
esac
