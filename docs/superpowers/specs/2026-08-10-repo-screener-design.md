# Repo screener — design

**Date**: 2026-08-10 · **Author**: claude-code agent 2 · **Status**: approved design, not yet implemented

Selects the public Python repository BenchMe develops against, by measurement rather than
judgement. Produces a ranked, gated shortlist and the two wall-clock budget numbers that decide
whether a repo is affordable to build on.

---

## 1. Purpose and framing

### The decision this makes

Which repository does BenchMe build its first evaluation corpus on, and what does it cost to work
there?

Prior work selected `pallets/itsdangerous` for Demo 01 on the criteria "small enough to understand
in one evening, fast, deterministic, no external services." Those are criteria for a *development
rig*. Used to select a *corpus*, they produced two failures:

1. **No discrimination.** All three models solved the single task. A task everything solves carries
   zero information — Stet's bimodality problem, and a property of the repo more than the task.
2. **No harness headroom.** At 36 files the entire repository fits in one context window, so context
   assembly, navigation and retrieval strategy collapse to nothing. A repo that small cannot exhibit
   a harness effect at all.

The second point generalises into a rule that appears nowhere in the existing research corpus:
**repo size sets a floor on which effects are observable.** It binds hard on the harness axis and
weakly on the model-tier axis.

### Three roles, deliberately separated

| Role | Optimises for | Appears in a report? |
|---|---|---|
| **Rig** — build and debug the harness | seconds per iteration, boring, hermetic | never |
| **Fixture** — prove the harness is correct | pre-validated tasks with *published* external numbers | as a validity control |
| **Corpus** — produce the finding | yield, discrimination, freshness | yes; it *is* the finding |

This spec selects the **corpus**. `itsdangerous` is retained as the rig and must never again carry a
claim. The fixture is out of scope here and recorded as a recommendation in §9.

### Decisions taken before design

| Question | Answer | Consequence |
|---|---|---|
| Screener lifespan | throwaway now, harvest later | code may be scrappy; **the metric definitions are the durable artifact** and are specified to survive a rewrite |
| Publishable corpus? | no — R&D and demo only | licence and benchmark-overlap become recorded *labels*, never gates |
| Primary experimental axis | **model tier** (segment 1: cost-aware / gateway-instrumented orgs) | size floor relaxes; difficulty spread and freshness dominate |
| Corpus shape | top-1 now, diversity later | screener still ranks the full field and records a diversity axis so repos 2–3 need no re-run |
| Screener depth | two tiers: static, then execute survivors | Tier A free and safe; all execution confined to Tier B |
| Ranking rule | gate-and-rank on a single key | no composite score anywhere |

### Why the axis choice constrains everything downstream

At 30 tasks × k=5 the minimum detectable effect is ≈12.5 pp (`sqrt(7.84 × p_d / n)`, `p_d ≈ 0.30`).
Against the published noise floor of 2.2–6.0 pp single-run pass@1 range (arXiv 2602.07150), only
large effects are observable at all:

| Effect | Published size | Detectable at MDE 12.5 pp? |
|---|---|---|
| Harness swap | 23–27 pp | yes |
| Frontier vs cheap model tier | large | yes |
| Quantisation / serving stack | up to 54 pp | yes |
| Frontier vs frontier model | ~3 pp | **no** |
| Prompt or config tweak | ~2 pp | **no** |

Choosing the model-tier axis therefore means the corpus must supply **difficulty spread** (tasks that
separate tiers) and **freshness** (contamination differentially rewards memorisation, which would
fake a tier result). It does *not* need to be large, because the harness is held fixed.

### Why no composite score

`PROJECT_KNOWLEDGE_BASE.md` §12 lists "a single composite BenchMe score" as an explicit non-goal. A
screener that ranked repos by a weighted blend of dimensions would be the exact anti-pattern the
project sells against, and would let one strong dimension mask a fatal weak one — a repo with
enormous commit volume and a 4% flake rate would rank well and then waste a month. Hard gates
eliminate; a single named key ranks; every other dimension is reported.

---

## 2. Architecture

```
screener/
  candidates.yaml     # repo list: clone URL, diversity tag, notes
  screen.py           # CLI: tier-a | tier-b | report
  out/
    tier_a.jsonl      # one record per candidate
    tier_b.jsonl      # one record per finalist
    logs/<repo>/…     # raw command output, verbatim
    REPORT.md         # gate ledger + ranked table + recommendation
```

No database, no schema library, no package. Plain files; every artifact is sufficient to regenerate
the report without re-running anything.

Three commands, run independently, each resumable. `tier-a` is idempotent per repo, so candidates
can be added and the sweep re-run without redoing completed work.

### Data flow

```
candidates.yaml
  → Tier A  (blobless clone + git plumbing, all candidates)
  → tier_a.jsonl
  → apply hard gates G1–G7
  → rank survivors by projected_capsules
  → take top N (default 4, configurable)
  → Tier B  (container build + 5 suite runs, finalists only)
  → tier_b.jsonl
  → REPORT.md
```

### Tier separation is strict

Tier A **never executes repository code**. It reads git metadata and the file tree only, which makes
it safe to point at any candidate and cheap enough to re-run freely. All execution is confined to
Tier B, inside a container, on a handful of finalists.

### The clone constraint

Tier A needs the full commit graph and almost none of the file contents.
`git clone --filter=blob:none` fetches every commit and tree while deferring blobs — minutes and a
few hundred MB rather than hours.

This imposes a rule on Tier A: **use `git log --name-only`, never `--numstat`.** Line counts force
blob fetches and would silently undo the saving. Tier A therefore counts *files* touched, never
lines. Any future metric requiring line counts belongs in Tier B or the miner, not here.

### Environment

Verified available on the development machine as of 2026-08-10: Docker 29.3.1 (WSL2 backend,
`docker-desktop` distro present), Python 3.14.4, Git 2.53.0. Tier B requires the Docker daemon
running; Tier A does not.

---

## 3. Tier A — rules

These definitions are the durable artifact. They are specified to be reimplementable from this
document alone.

### 3.1 The central definition

A **candidate pair** is a commit that could in principle become a capsule:

- not a merge commit;
- touches ≥1 source file **and** ≥1 test file;
- touches ≤10 files in total (self-containment; matches Databricks' published filter);
- **human-authored**.

`human-authored` excludes a commit when any of the following hold:

- author or committer identity matches `[bot]`, `dependabot`, `renovate`, or `pre-commit-ci`;
- the message carries a `Co-authored-by:` trailer naming Copilot, Devin, Claude, or Codex;
- the message contains a generation marker such as `Generated with Claude Code`.

This filter is non-negotiable: training the corpus on agent-authored commits in order to evaluate
agents is circular. It is also the rule most likely to be quietly wrong, and in a 2026 repository it
may remove a large fraction of history. **The excluded count is reported as a first-class metric**,
not merely applied — it is itself a finding about how much of modern OSS history is machine-written.

### 3.2 Metrics recorded per repo

| Group | Fields |
|---|---|
| Volume | `commits_total`, `commits_180d`, `commits_since_cutoff`, `candidate_pairs`, `candidate_pairs_fresh`, `excluded_nonhuman` |
| Yield | `projected_capsules = candidate_pairs × 0.022`, `projected_fresh`, `fresh_share` |
| Discrimination | files-touched distribution over candidate pairs: p50, p90, `frac_multifile` (≥3 source files touched) |
| Free labels | `revert_commits` (message matches `^Revert "`), `hotfix_commits` (message matches `hotfix\|regression\|fixup`, case-insensitive) |
| Hardening cost | `test_map_ratio` — fraction of test files resolvable to **exactly one** source file by naming convention (`tests/test_X.py` ↔ `**/X.py`; `test_X.py` adjacent to `X.py`). `conftest.py` is excluded from the population; a stem matching several source files is counted ambiguous, not mapped, and reported as `test_map_ambiguous` |
| Environment | lockfile kind (`uv.lock`/`poetry.lock`/`requirements*.txt`), `pyproject.toml` present, CI config present, devcontainer or Dockerfile present, compiled-extension markers (`*.pyx`, `Cargo.toml`, `CMakeLists.txt`, `ext_modules` in `setup.py`), service-dependency markers (postgres/mysql/redis/docker-compose referenced in CI or test config) |
| Labels only | licence, known-benchmark overlap (SWE-bench 12 / SWE-bench Pro / SWE-smith), `diversity_tag` |
| Scale | tracked file count, Python LOC |

Licence and benchmark overlap are recorded but never gate — a direct consequence of the "no
publishing" decision. If publishing returns they promote to gates without changing any measurement.

`diversity_tag` is hand-assigned in `candidates.yaml` from the set
`{logic, io, framework, coupling, cli, app}`. It carries no weight in ranking; it exists so repos 2
and 3 can be chosen for maximum difference later without re-running Tier A.

### 3.3 Hard gates

| # | Gate | Rationale |
|---|---|---|
| G1 | Python + pytest detected | v1 ecosystem, per decision register in `PROJECT_KNOWLEDGE_BASE.md` §17 |
| G2 | `candidate_pairs ≥ 360` | ≥8 capsules at the conservative 2.2% conversion — the stated pivot floor |
| G3 | `commits_since_cutoff ≥ 30` | a fresh, contamination-resistant stream exists at all |
| G4 | `test_map_ratio ≥ 0.5` | mutation hardening is affordable only with targeted test selection |
| G5 | no compiled extension built **from source** in this repo | environment reconstruction cost |
| G6 | no service dependency on the default test path | hermeticity |
| G7 | lockfile present or dependencies fully pinned | determinism |

**G5 reads narrowly and deliberately.** It excludes repos that build C/Rust/Cython *as part of their
own package* — where you would spend the project debugging a build toolchain. It does not exclude
repos with compiled *dependencies* installed as pinned wheels. This is what keeps `pydantic`
eligible while excluding `numpy`-shaped repos.

`cutoff` defaults to `2026-05-01` and is configurable. See §9 on why a single date is used.

### 3.4 Ranking

Survivors rank on **`projected_capsules`**, single key, descending. Everything else is a report
column.

**Freshness ranks; it does not gate.** For a model-tier comparison contamination is the dominant
confound, so the instinct is a hard gate on fresh candidate pairs. The arithmetic kills that idea: a
high-velocity repo produces on the order of 150 candidate pairs in the months since the cutoff,
i.e. ~3 projected fresh capsules, so a fresh-only gate eliminates the entire field. Therefore:

- G3 checks only that the repo is genuinely alive post-cutoff;
- `fresh_share` and `projected_fresh` are prominent report columns;
- the corpus will be **mostly pre-cutoff**, and the honest response is to report the fresh/stale
  split beside every downstream result rather than claim a clean stream that cannot be obtained.

---

## 4. Tier B — rules

Runs on the top N survivors only (default N=4), inside a Linux container, pinned to the repo's HEAD SHA at
screening time. The SHA is recorded and never re-floated; a later re-screen produces a new record
rather than mutating the old one.

### 4.1 The environment ladder

Tier B does not *synthesise* an environment. It **reuses what the repo already ships**, descending a
ladder and recording which rung worked. This is the OSS analogue of the enterprise architecture
decision — reuse the customer's CI rather than solve containerisation — and the rung is the headline
qualification signal.

| Rung | Source | Meaning |
|---|---|---|
| 1 | `devcontainer.json` | literally a spec for this; near-free |
| 2 | Dockerfile or compose file in repo | explicit image; near-free |
| 3 | CI workflow setup steps | replay python-version and install command; brittle but usually works |
| 4 | `pyproject.toml` + lockfile via `uv sync --frozen` | last resort, still deterministic |
| ✗ | none of the above succeeds | eliminate (`gated:B1`) |

Alongside the rung, one hand-recorded field: **`operator_minutes`** — how long the operator spent
patching to get the suite green. It cannot be automated and is typed in. It is the only honest
measure of onboarding cost and the leading indicator on the services-trap gate ("if onboarding costs
more than two engineer-days per customer, the business is a consultancy").

### 4.2 Measurements

Five suite runs at the pinned SHA in the same container:

| Field | Definition | Why it matters |
|---|---|---|
| `head_green` | all tests pass at HEAD, modulo a recorded skip list | without a green baseline the P2P regression control has nothing to compare against |
| `flake_rate` | fraction of tests with non-constant outcome across 5 runs | a flaky P2P test manufactures false regressions and corrupts the negative control |
| `randomly_present`, `xdist_present` | `pytest-randomly` / `pytest-xdist` in the test stack | both are flake sources better controlled than inherited |
| `suite_runtime_p50` | median full-suite wall clock | drives verification cost |
| `targeted_latency_cold`, `targeted_latency_warm` | wall clock for a single test node-id, first invocation and steady-state | drives mutation-hardening cost; decides whether hardening is affordable at all. **`_warm` feeds the budget formula**, since hardening runs thousands of invocations in one container |
| `net_dependent_tests` | failures under network-denied minus failures under network-allowed | the runner denies egress by design, so these become phantom failures that look like agent mistakes |

`net_dependent_tests` measures compatibility with the project's own leakage controls before anything
is built on top. A large but cleanly marker-excludable set is a very different verdict from a
scattered one, so the report records both the count and whether a single marker or path expression
covers it.

### 4.3 Derived budgets

Both reported in hours; both more decision-relevant than any raw metric. Latency and runtime inputs
are in seconds, so both formulas divide by 3600:

```
hardening_hours    = (60 mutants × 30 tasks × targeted_latency_warm) / 3600
verification_hours = (suite_runtime_p50 × 30 tasks × k=5 × 4 configs) / 3600
```

At a 5-second targeted latency hardening is ~2.5 hours and fine; at 60 seconds it is ~30 hours and
the repo is effectively disqualified for mutation work regardless of its Tier A rank. **Tier B is
expected to overturn the Tier A ranking. That is why it exists.**

### 4.4 Tier B gates

| # | Gate |
|---|---|
| B1 | environment builds at rung ≤4 with `operator_minutes ≤ 120` |
| B2 | `head_green`, with any skips recorded |
| B3 | `flake_rate ≤ 0.5%` |
| B4 | `net_dependent_tests` ≤2% of tests, or cleanly marker-excludable |

`hardening_hours` and `verification_hours` are reported with soft thresholds, not hard gates. They
are derived estimates, and converting an estimate into an automatic elimination is the false
precision the project sells against.

---

## 5. Candidate set

All entries are **priors to be falsified, not pre-screened facts**. The author's knowledge runs to
approximately May 2026; velocity, layout and dependency choices may have moved. Several confident
picks are expected to die at Tier A.

Tier A costs one blobless clone per candidate. Pre-filtering by judgement is therefore strictly worse
than letting the gates work, and is how selection bias enters. Eighteen candidates.

| # | Repo | Tag | Rationale / doubt |
|---|---|---|---|
| 1 | `pydantic/pydantic` | logic | Default pick. High velocity, conventional layout, Rust core arrives as a pinned wheel so G5 holds |
| 2 | `python-attrs/attrs` | logic | Clean and hermetic; doubt it clears G2 |
| 3 | `marshmallow-code/marshmallow` | logic | Same shape, same volume doubt |
| 4 | `pypa/packaging` | logic | Very clean, probably too quiet for G2 |
| 5 | `python-jsonschema/jsonschema` | logic | Spec-driven tests; `test_map_ratio` uncertain |
| 6 | `encode/httpx` | io | Mock transports should keep it hermetic; B4 is the question |
| 7 | `encode/starlette` | io | TestClient-based, likely hermetic |
| 8 | `pallets/werkzeug` | io | Socket-level tests; B4 risk |
| 9 | `urllib3/urllib3` | io | Spins a local test server; expect B4 trouble |
| 10 | `tiangolo/fastapi` | framework | High velocity, hermetic, large test count — strong candidate |
| 11 | `sqlalchemy/sqlalchemy` | coupling | Best coupling in the list; expect G4 and suite runtime to bite |
| 12 | `pallets/jinja` | framework | Moderate volume |
| 13 | `pallets/flask` | framework | Carries a SWE-bench-overlap label; small, likely fails G2 |
| 14 | `pallets/click` | cli | Very hermetic, clean layout |
| 15 | `psf/black` | cli | Excellent test discipline; velocity may have flattened with maturity |
| 16 | `Textualize/rich` | cli | Snapshot-based oracles are a different class — worth seeing even if not chosen |
| 17 | `pre-commit/pre-commit` | app | Application-shaped, git-heavy |
| 18 | `mkdocs/mkdocs` | app | Application-shaped, hermetic |

### Known selection bias

Sixteen of eighteen are **libraries**; customers' repositories are applications and services. Repos
that screen well are by construction the ones already most agent-ready — Factory's thesis, and a real
threat to external validity.

Entries 17 and 18 are deliberate probes: they exist to discover whether the pipeline survives
application-shaped code, not because they are expected to win. **If both wash out at Tier A, that is
a finding and belongs in any report this corpus later supports.**

### Sets for the other segments (not screened now)

- **Segment 2, harness axis** — needs size and coupling, because harness effects arise from context
  assembly and vanish when the repo fits in one context window: `sqlalchemy`, `django`, `mypy`,
  `sphinx`, `transformers`. `mypy` is attractive on volume but its `.test` data-file suite fails G4 —
  a clear illustration of a gate doing real work.
- **Segment 3, quantisation axis** — not primarily a repo-selection problem. What matters is *task*
  shape (long-horizon, tool-call-heavy) plus GPU serving infrastructure not currently available.
  Deferred; revisit only if the on-prem segment becomes live.

---

## 6. Failure semantics

Every candidate reaches exactly one terminal state. The sweep never aborts.

| Status | Meaning |
|---|---|
| `passed` | cleared all gates at that tier |
| `gated:<G#>` | failed a named gate — **a result, not an error** |
| `unavailable` | clone failed after one retry |
| `error` | screener bug; record traceback and continue |

The `gated` / `error` distinction is load-bearing. A repo that cannot build a container has not
crashed the tool — it has produced the qualification signal, and it belongs in the output with its
reason string intact.

Raw stdout and stderr for every command are persisted under `out/logs/<repo>/` so a surprising
verdict can be audited without re-running. Records are keyed by repo; re-running skips anything
already terminal unless `--force` is passed.

---

## 7. Testing

The code is disposable; the counting rules are not. The test suite therefore covers **exactly the
rules and nothing else** — three synthetic git repositories constructed inside the tests with
known-answer histories:

1. **Authorship exclusion** — dependabot commits, a `Co-authored-by: Claude` commit, and human
   commits → assert only human commits are counted, and `excluded_nonhuman` matches.
2. **Candidate-pair definition** — a merge commit, a source-only commit, a test-only commit, one
   valid src+test commit, and an 11-file commit → assert `candidate_pairs == 1`.
3. **Test-map ratio** — conventional and unconventional test naming → assert the computed ratio.

Nothing else is tested: not report formatting, not container orchestration, not ranking arithmetic.

The justification is narrow: a wrong counting rule fails *silently*, selects the wrong repository,
and is then harvested into the miner where it poisons the corpus. That is the only place in this
tool where a bug is expensive.

---

## 8. Output

`REPORT.md`, five sections:

1. **Run metadata** — date, freshness cutoff used, screener git SHA, candidate count, pinned HEAD SHA
   per repo.
2. **Gate ledger** — *every* candidate including eliminated ones, with terminal status and first
   failing gate. Eliminated candidates are never silently dropped: a screener that reports only
   survivors is indistinguishable from one with a bug in its gates.
3. **Ranked survivors** — full dimension table sorted by `projected_capsules`.
4. **Tier B finalists** — environment rung, `operator_minutes`, flake rate, and both budget numbers.
5. **Recommendation** — top-1 with reasoning, plus named runners-up tagged by diversity axis so repos
   2 and 3 can be chosen later without re-running Tier A.

### Explicit non-goals

No database. No web UI. No schema-validation library. No LLM calls anywhere in the screener. No
per-commit checkout in Tier A. No attempt to mine or validate capsules — that is the miner. No
languages beyond Python. No composite score.

---

## 9. Open questions — recorded, not resolved

1. **Which harness is fixed** for the model-tier experiment, and whether it can address open-model
   endpoints natively or needs the Inspect AI agent bridge (`sandbox_agent_bridge()`). Affects the
   experiment, not repo selection, so it does not block this work.
2. **The 2.2% conversion is a conservative floor, not a prediction.** It comes from SWE-Next's honest
   pipeline over a broad corpus; a curated, test-disciplined repo may convert several times better.
   Recalibrate `projected_capsules` after the miner runs for real, and treat the first miner run as
   the calibration experiment.
3. **Cutoff dates vary across the model fleet.** A single configurable date is used and reported,
   rather than claiming a per-model freshness guarantee that cannot be verified for closed models.
4. **The fixture repo is unselected.** Recommendation: import ~20 SWE-bench Verified instances from a
   single pure-Python repo (`sympy` preferred — BSD, hermetic, no compiled build; `django` second) to
   debug the runner and verifier against pre-validated tasks with published pass rates. This
   decouples "is my machine correct?" from "is my mining any good?", which Demo 01 could not separate.
   Out of scope for this spec.

---

## 10. Relationship to existing plans

This work sits **before** build-queue item 4 (miner stages 0–2) in
`research/claude/COWORK_AGENT_1_HANDOFF.md` §9, and supplies the repo that items 1–3 and 7 operate
on. Tier A's candidate-pair definition is the specification for miner stage 0; the metric definitions
in §3 are what gets harvested when the throwaway code is replaced.

It does not modify or supersede any prior decision. It records one new rule not present in the
research corpus: **repo size sets a floor on which effects are observable**, derived from the Demo 01
failure analysis in §1.
