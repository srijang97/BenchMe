# Miner stages 0–2 — design

**Date**: 2026-08-11 · **Author**: claude-code agent 2 · **Status**: approved design, not yet implemented
**Corpus repo**: `pydantic` (selected by the screener, 35.13 projected capsules)
**Depends on**: `docs/council/ROUND_01_SYNTHESIS.md` (oracle contract)

Turns pydantic's git history into validated fail-to-pass candidates with evidence.
Stops short of capsules: no task statements, no oracle controls, no capsule files.

---

## 1. Scope and what this deliberately does not do

Stages 0–2 answer one question: **which commits in this repository can become
evaluation tasks, and what does it cost to find out?**

Output is a validated candidate — base commit, fail-to-pass test node ids, the
regression set, the quarter environment it ran in, and the raw before/after test
output. Nothing more.

Everything the council's capsule contract requires beyond that — behavioural
specification, authored alternate, adversarial probe battery, near-misses per
requirement — depends on decisions not yet made. Council round 2 covers task
statement provenance. Writing those fields now would bake in answers nobody has
agreed to.

**Two numbers are the real deliverable**, because several council rulings are
explicitly conditional on them:

- the **real conversion rate** from candidate pairs to validated candidates,
  against the conservative 2.2% the screener's gate G2 assumed;
- the **curation cost per candidate**, against the project's pivot criterion of
  one engineer-day.

### Decisions taken during design

| Question | Answer | Consequence |
|---|---|---|
| Environment drift across history | repo-quarter profiles | ~8–12 environments cover 2–3 years; the only option that reaches 8+ capsules |
| Output of stages 0–2 | validated candidates plus evidence | no capsule files, no statements, no controls |
| "Fails for the right reason" strictness | assertion-only, **but count what that rejects** | corpus is bug-fix shaped; we learn what the rule costs |
| Execution architecture | one long-lived container per quarter | solves drift and startup cost with one move |
| Stage 1's role | score and stratify, never rank-and-truncate | guards against building a suite of easy tasks |

### Why recent history alone will not do

The screener measured 1,597 candidate pairs across pydantic's whole history but
only 35 in the three months since the model cutoff. At the conservative 2.2%
conversion that is roughly one capsule. Reaching the eight the pivot criterion
requires means going back two to three years, which makes environment drift
unavoidable rather than something the design can dodge.

---

## 2. Architecture

```
miner/
  mine.py          # CLI: enumerate | validate | report
  candidates.py    # stages 0-1: enumerate + structural score
  quarters.py      # repo-quarter profiles, image build, container lifecycle
  validate.py      # stage 2: patch split, two-pass execution, error2pass
  record.py        # candidate record + JSONL store
  report.py        # funnel report
  tests/           # three tests, see section 6
  out/
    candidates.jsonl    # every stage-0 survivor, with stage-1 scores
    validated.jsonl     # stage-2 results, appended per quarter
    logs/<sha>/         # raw before/after pytest output, verbatim
    REPORT.md
```

**Flow.** `enumerate` walks history once and writes every stage-0 survivor with
its stage-1 score — free, no execution, minutes. `validate --quarter 2025Q3`
builds that quarter's environment, opens one container, runs the two-pass check
over every candidate in that window, and appends results. Quarters run one at a
time so results are inspectable as they land. `report` renders the funnel.

**Reuse rather than rebuild.** `screener/metrics.py` already holds
`is_candidate_pair`, the authorship rules and source/test classification — these
are exactly the rules the plan always intended to harvest into the miner.
`screener/gitmeta.py` provides clone and log parsing. `screener/tierb.py`
provides `host_path()` and `docker_env()`, which encode two Windows landmines
already paid for once.

The miner **imports** these rather than copying them, so there is one definition
of a candidate pair rather than two that can drift. When the screener is deleted,
`metrics.py` moves into `miner/` — a file move, not a rewrite.

---

## 3. Stages 0 and 1

### Stage 0 — enumerate

Reuses `is_candidate_pair` unchanged: non-merge, human-authored, ≤10 files,
touching at least one source and one test file. Two mining-specific additions,
both free:

- **Skip deletion-only test changes.** A commit that only removes assertions has
  no fail-to-pass to offer, and would otherwise look valid until execution.
- **Skip reverts of another candidate.** Otherwise the same behaviour enters the
  corpus twice with opposite signs.

### Stage 1 — score and stratify

The handoff names the hazard directly: *"Ranking biases the corpus, and the bias
is the falsification risk."* Scoring for "small diff, test-rich, clean flip"
builds a suite of small easy tasks — the representativeness failure in the
project's own kill criteria.

So stage 1 **scores and stratifies; it never ranks-and-truncates, and it kills
nothing on score.**

| Signal | Cost | Purpose |
|---|---|---|
| files touched, source files, test files | free | size stratum |
| test-to-source line ratio | free | how test-heavy the change is |
| subsystem (top-level dir under `pydantic/`) | free | subsystem stratum |
| risk class from path rules | free | reported, not filtering |
| reverted later? hotfixed within 48h? | free | history signals `research/05` calls underexploited |

The validation queue is built by **sampling within `subsystem × size` strata**,
never by taking the global top N. For a first batch of ten this matters: ten
candidates drawn from the easy tail would tell us very little, convincingly.

**`pydantic/v1/` is its own stratum.** It is a vendored compatibility tree
duplicating most module names. Its commits are real, but mixed in undifferentiated
a batch could come back disproportionately from a shim nobody actively develops.
This is the same tree that broke the screener's `test_map_ratio`.

---

## 4. Stage 2 — execution

### 4.1 Quarter profiles install dependencies only, never pydantic itself

The most important decision here. If the image carries pydantic in
`site-packages`, a candidate checked out at a different commit is not what gets
imported, and every result is silently about the wrong code. That is exactly the
bind-mount shadowing that produced zero collected tests twice during screening.

Avoided by construction: the image carries **only the dependency closure** from
that quarter's lockfile; each candidate runs with its own checkout on
`PYTHONPATH`.

Dependency resolution reuses what the screener established:

- `uv export --frozen` plus a system install — **not** `uv sync`, which builds a
  `.venv` that the working-directory swap destroys;
- pydantic needs `--all-groups --all-packages --all-extras`, matching its own
  Makefile, or the `email_validator` tests fail for reasons unrelated to pydantic;
- fall back through `uv.lock` → `requirements*.txt` → `pyproject.toml`, since
  older quarters predate the project's adoption of uv.

The **anchor commit** for a quarter is the last commit within it; that commit's
lockfile defines the environment for every candidate in the window.

### 4.2 Splitting the commit

For candidate `C` with parent `P`:

- **test patch** = `git diff P C` restricted to test paths
- **code patch** = `git diff P C` restricted to everything else

Check out `P` fresh, apply the test patch alone — the new tests now exist without
the fix. Apply the code patch as well and they should pass.

### 4.3 Finding fail-to-pass by diffing outcomes, not by parsing the diff

Run the **touched test files** on both sides and compare per-test results.
Fail→pass is the F2P set; passing on both sides is regression-set material.

Robust without a diff parser, and it handles the common case of a touched file
holding two hundred tests of which three are new.

### 4.4 Two passes

| Pass | Scope | Purpose |
|---|---|---|
| 1 | touched test files only, both sides | cheap; eliminates most candidates |
| 2 | full suite, survivors only | establishes pass-to-pass; catches a code patch that breaks something elsewhere |

Cheapest filter first, the same principle as the screener's tiers.

**A note on volume, because an earlier draft of this spec got it wrong.** The
handoff's funnel has stage 1 killing roughly 80% of candidates on structural
score. This design deliberately does not do that — §3 says stage 1 kills nothing,
because filtering on "small diff, test-rich, clean flip" is precisely how the
corpus becomes a set of easy tasks.

So pass 1's volume is set by **how large a stratified sample we choose to run**,
not by a quality filter. For reference: running the entire 1,597 candidates
through pass 1 at roughly 3 seconds per side is about 2.7 hours, which is
affordable — where the same population through the *full* suite would be about 9
hours. The first batch is far smaller than either. Coverage is a budget decision
made per batch and recorded, never a silent consequence of scoring.

### 4.5 Failure classification at the "before" side

| Failure shape | Classification | Verdict |
|---|---|---|
| assertion failure | `assertion` | qualifies |
| `AttributeError`, `ImportError`, `ModuleNotFoundError` | `missing_api` | rejected, counted |
| collection error, syntax error | `structural` | rejected, counted |
| anything else | recorded with exception type | rejected, counted |

The assertion-only rule comes from the council contract. It is right for bug
fixes, where the code exists and behaves wrongly — but a newly added feature's
test fails at the parent with `AttributeError`, because the API is not there yet.
Applied literally the rule filters pydantic's feature work out of the corpus.

**Every rejection is counted by class**, so we learn what the rule actually costs
in yield rather than assuming it was well calibrated. A large `missing_api` count
is a finding to take back to the council, not a number to quietly absorb.

### 4.6 Container lifecycle

One long-lived container per quarter; a fresh checkout directory per candidate
inside it. The container is reused, the working tree never is. Checkout
directories are deleted immediately after each result is recorded.

---

## 5. Resource discipline

Measured on this machine at design time: 63.3 GB RAM with 13.0 GB free, 839 GB
disk free, no `.wslconfig` so WSL2 may claim up to roughly 31 GB. About 38 GB of
Docker build cache and dangling images — mostly screener leftovers — was
reclaimed before starting.

- **Never more than one container alive.** Quarters run strictly sequentially;
  the runner refuses to start a second while one is up.
- **Hard caps per container**: `--memory=4g`, `--memory-swap=4g` so it cannot
  silently spill to swap, `--cpus=4`, and a `--pids-limit`. pytest on pydantic
  needs nowhere near 4 GB; the cap exists so a pathological candidate fails fast
  and visibly instead of taking the machine down.
- **A container killed on OOM is an apparatus error against that candidate**, not
  a test failure.
- **Preflight per quarter**: refuse to start below 20 GB free disk or 6 GB free
  RAM, with a clear message rather than a mid-run crash.
- **Quarter images are removed after their quarter completes**, behind a
  `--keep-images` flag for iterating on a single quarter. Eight to twelve images
  at 1–2 GB each would otherwise idle at 8–24 GB.

### Failure semantics

| Status | Meaning |
|---|---|
| `validated` | fail-to-pass established, assertion-class failure, regression set clean |
| `rejected:<reason>` | a real verdict — `unchanged`, `missing_api`, `structural`, `regression_broken`, `flaky` |
| `apparatus` | our fault — OOM, image build failure, container died, patch would not apply |
| `error` | miner bug; traceback recorded, the sweep continues |

`rejected` and `apparatus` stay rigidly separate. The screener's central lesson
was that six of seven eliminations were the apparatus rather than the subject,
and that only became visible because the two were recorded differently.

---

## 6. Testing

Three tests, covering only logic that fails **silently** — the same argument that
justified testing `metrics.py` and nothing else. The counting rules stay covered
by the existing `screener/tests/` fixtures, because the miner imports them rather
than copying.

1. **Patch splitting** — given a commit touching both kinds of file, the test
   patch must contain only test paths and the code patch only the rest. Wrong
   here means either handing the agent the answer or stripping the fix so every
   candidate looks broken.
2. **Outcome diffing** — given before and after outcome maps, the F2P and P2P
   sets must come out right. Wrong here means recording the wrong tests as the
   oracle.
3. **Failure classification** — given real pytest output samples, assertion vs
   `missing_api` vs `structural` must be classified correctly. Wrong here means
   the assertion-only rule silently admits or rejects the wrong candidates, and
   the yield number we draw conclusions from is measuring a broken filter.

Nothing else gets a unit test. Container orchestration, image building and report
rendering are verified by running them against real pydantic commits.

**Acceptance**: the three tests pass, and one real pydantic candidate goes
end-to-end through both passes with its before/after output on disk.

---

## 7. How results are reviewed

**We stop after the first quarter, not at the end.** The output for review is:

- raw records — commit SHAs, stage-1 strata, verdicts;
- rejection counts by class, including `missing_api`;
- verbatim before/after pytest output for two or three candidates, so the
  classifier's calls can be judged rather than trusted.

Then we decide whether to continue, adjust the rules, or take a finding back to
the council before spending compute on remaining quarters.

`REPORT.md` shows the funnel: candidates enumerated, survivors at each stage, and
rejections by class.

---

## 8. Open questions, recorded not resolved

- **The real conversion rate is unknown.** 2.2% is a conservative floor from a
  broad corpus. If pydantic converts at 5%, screener gate G2 should be
  recalibrated and several eliminated repositories become viable again.
- **Curation cost per candidate is unmeasured**, and it is the arm of the pivot
  criterion that mandatory alternates load.
- **Quarter-boundary error is unquantified.** A candidate early in a quarter runs
  against an environment anchored at the quarter's end. Expected to be small
  relative to per-commit drift, but it is an assumption, and `apparatus` failures
  clustered at quarter starts would be the signal that it is wrong.
- **Flaky candidates are detected but not handled.** A candidate whose F2P set is
  unstable across repeats is rejected as `flaky`; whether it could be salvaged by
  excluding the unstable tests is left for later.
