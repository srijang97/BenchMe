"""Tier A metric definitions.

This module is the durable artifact. When the rest of the screener is thrown
away, these rules are harvested into the miner's stage 0. Change them
deliberately, and update screener/tests/test_metrics.py when you do.
"""
import re
from pathlib import PurePosixPath

# SWE-Next honest conversion from raw candidate pairs to valid capsules.
# A conservative floor, not a prediction. See spec section 9 item 2.
CONVERSION_RATE = 0.022

BOT_IDENTITY = re.compile(r"\[bot\]|dependabot|renovate|pre-commit-ci", re.I)

# Bot email anchors first: unambiguous, checked before the bare-name
# alternatives. The bare names are word-bounded so "Claude" as a human given
# name (e.g. "Co-authored-by: Claude Dubois <c.dubois@example.com>") does not
# match on name alone.
AI_TRAILER = re.compile(
    r"co-authored-by:[^\n]*"
    r"(noreply@anthropic\.com|devin-ai|copilot@|codex@"
    r"|\bcopilot\b|\bdevin\b|\bclaude\b|\bcodex\b)", re.I)
AI_MARKER = re.compile(
    r"generated with[^\n]*(claude code|codex|copilot)", re.I)

# Basenames that are Python but never behavioural source: packaging and
# tooling entry points. Matched against the file's basename only.
NON_SOURCE_NAMES = {"setup.py", "noxfile.py", "conftest.py"}

# Directories whose Python contents are never behavioural source, regardless
# of basename. Matched if any path segment equals one of these.
NON_SOURCE_DIRS = {"docs", "doc", "examples", "example", "scripts", "benchmarks"}


def is_test_file(path):
    p = PurePosixPath(path)
    if p.suffix != ".py":
        return False
    if "tests" in p.parts:
        return True
    return p.name.startswith("test_") or p.stem.endswith("_test")


def is_source_file(path):
    p = PurePosixPath(path)
    if p.suffix != ".py":
        return False
    if is_test_file(path):
        return False
    if p.name in NON_SOURCE_NAMES:
        return False
    if NON_SOURCE_DIRS & set(p.parts):
        return False
    return True


def is_human(commit):
    """False for bot identities, AI co-author trailers, and generation markers.

    This rule deliberately errs toward exclusion: wrongly dropping a human's
    commit costs one candidate out of hundreds, whereas wrongly admitting an
    agent's commit reintroduces the circularity the rule exists to prevent.
    """
    identity = f"{commit.author} {commit.committer}"
    if BOT_IDENTITY.search(identity):
        return False
    message = f"{commit.subject}\n{commit.body}"
    if AI_TRAILER.search(message) or AI_MARKER.search(message):
        return False
    return True


def is_candidate_pair(commit, max_files=10):
    """A commit that could in principle become a capsule.

    Self-enforcing on merges: a commit with 2 or more parents is excluded
    here directly, rather than relying on a caller to have passed
    `git log --no-merges` upstream.
    """
    if len(commit.parents) >= 2:
        return False
    if not is_human(commit):
        return False
    if len(commit.files) > max_files:
        return False
    has_source = any(is_source_file(f) for f in commit.files)
    has_test = any(is_test_file(f) for f in commit.files)
    return has_source and has_test
