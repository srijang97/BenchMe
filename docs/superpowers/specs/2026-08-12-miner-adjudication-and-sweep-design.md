# Miner adjudication and the v2-era sweep — design

**Date**: 2026-08-12 · **Author**: claude-code agent 2 · **Status**: approved design, not yet implemented
**Corpus repo**: `pydantic` · **Branch**: `feat/miner-adjudication`
**Depends on**: `docs/council/ROUND_02_SYNTHESIS.md`, `docs/miner/2025Q3-rerun.md`

Makes the miner's verdicts trustworthy, then sweeps pydantic's v2 era to produce
the two numbers the miner spec called its real deliverable: the **conversion
rate** and the **cost per candidate**.

---

## 1. Scope

Five defects and gaps found by *running* the miner, plus the sweep they unblock.

**In scope**

1. Extract the verdict logic out of `_measure` into a pure, testable adjudicator.
2. Categorise base-state collection errors instead of blaming them on ourselves.
3. Stop counting a vanished test as a failed one.
4. Three enumeration filters: foreign project, dependency boundary, non-pytest dirs.
5. A staged sweep of 2023Q3–2026Q3.

**Not in scope**

- **The stub-import near-miss probe.** Specified in §5.4 for a later phase. It is
  what would let `rejected:base_import_blocked` capsules be promoted into the
  corpus on evidence.
- **Stage 3 (capsules)**: task statements, oracle controls, capsule files. Still
  blocked on statement provenance, which the miner spec assumed council round 2
  would settle and which round 2 did not reach.
- **Narrowing the pass-2 collection-error predicate** to the candidate's own
  target files. Deliberately left broad; a blanket rule would retire nearly every
  candidate under endemic dependency drift.
- Per-commit environments. `docs/miner/2025Q3-rerun.md` records why the data does
  not justify abandoning repo-quarter profiles.

## 2. Why: what running the miner exposed

Every item below is measured, not inferred.

| finding | evidence |
|---|---|
| `_measure` is where the bugs live | 370 lines, 19 status assignments, 13 early returns. All three of Task 6's fix rounds were *ordering* bugs in it, and none was catchable by unit test because it needs Docker |
| Collection errors are miscategorised | `aa7705f7` had **869 tests collected and 773 passing** and was discarded because 2 of its 4 touched files failed to import |
| `missing_api = 0` is an artifact | Feature work whose test imports a new symbol at module top level dies at *collection*, never reaching the call-level check the rate is computed from. Verified on `3a7fe26a`, whose new test imports `UnsupportedFieldAttributeWarning`, a class the code patch adds |
| A vanished test is counted as a failed one | `f7a9b735`: *"0 previously-passing tests fail … and 7 vanished"*. `aa7705f7`: 9 "broken" tests, all docs examples whose line-range ids shifted when the commit deleted 12 lines of prose |
| Foreign commits are in the pool | 105 of 1,568 candidates have `name = 'pydantic_core'` in their `pyproject.toml` — a different project grafted into the clone |
| Some commits straddle an environment boundary | 2 of 21 change the pinned `pydantic-core` version, so before and after genuinely need different environments |

### One near-miss worth recording

The raw pin distribution said only **29%** of 2025Q3 candidates have a parent
pinned to the image's `pydantic-core`, which looked like it condemned the
repo-quarter design. Cross-referencing pins against outcomes disproved it —
capsules validated at every pin level. The real predictor is narrow: commits
that *change* the pin. **Do not re-derive this from the pin distribution alone.**

## 3. Architecture: the adjudicator split

`_measure` stops deciding anything. It becomes **gather → adjudicate → record**.

New pure module `miner/adjudicate.py`:

```python
class TargetSelection(NamedTuple):
    paths:  list          # what pytest will be pointed at
    why:    str           # OK | FILTERED | DELETED | ABSENT | PROBE_FAILED
                          # everything but OK explains why `paths` is empty
    detail: str | None    # matched filter prefix, probe stderr, etc.

class Measurements(NamedTuple):
    pass2:          bool
    targets:        TargetSelection
    before:         dict          # nodeid -> outcomes status
    after:          dict | None   # None when the after run never happened
    before_records: list          # outcomes.Record, for messages and labels
    before_collect: list          # file paths that failed to collect
    after_collect:  list
    pass1_f2p:      list | None

class Verdict(NamedTuple):
    status: str                   # validated | pass1_ok | rejected:* | not_minable:* | apparatus | error
    reason: str | None
    fields: dict                  # every derived record field
```

`adjudicate(m: Measurements) -> Verdict` owns the outcome diff, the failure
labelling and every decision arm. It performs no I/O — no Docker, no git, no
filesystem — so all arms are testable with plain dicts.

**Migration is two commits.** Extract with current behaviour pinned by tests
first; add the new arms second. Refactoring merged working code and changing its
semantics in one step is how the arms that already work get lost.

`check_pass2_determinism` (already extracted in Task 6) folds into
`adjudicate.py` rather than staying in `runner.py`.

## 4. The verdict table

Ordering **is** the design: ordering is where every defect lived. First match
wins, top to bottom.

| # | condition | status | whose failure |
|---|---|---|---|
| 1 | commit changed no test files | `rejected:unchanged` | commit |
| 2 | every touched test removed by our non-pytest filter | `rejected:no_runnable_tests` | commit¹ |
| 3 | touched tests existed at the parent, deleted by the commit | `rejected:no_runnable_tests` | commit |
| 4 | targets empty for any other reason | `apparatus` | ours |
| 5 | target probe itself failed | `error` | ours, transient |
| 6 | clone / checkout / patch-write failed | `error` | ours, transient |
| 7 | pytest exit outside `{0,1,5}`, or report unreadable / truncated | `apparatus` | ours |
| 8 | before or after produced no outcomes at all | `apparatus` | ours |
| **9** | **f2p non-empty** | **continue to 13** | — |
| **10** | **f2p empty, and before-collect errors cleared by the code patch** | **`rejected:base_import_blocked`** | **commit** |
| **11** | **f2p empty, and before-collect errors persist after** | `apparatus` | ours |
| 12 | f2p empty, no collect errors | `rejected:unchanged` | commit |
| 13 | pass 2: oracle absent from the run / did not reproduce | `apparatus` / `rejected:unstable` | ours / commit |
| 14 | tests that **ran and failed** after the patch | `rejected:regression_broken` | commit |
| 15 | otherwise | `validated` (pass 2) / `pass1_ok` (pass 1) | — |

¹ The reason names the matched config prefix, so a wrong filter entry is
auditable rather than silently blaming the commit.

### 4.1 Row 9 above rows 10–12

A collection error matters only when it left us **unable to conclude**. If an
oracle was found anyway, the errors cost us *potential extra* oracle tests, not
the answer. This is the `aa7705f7` fix, and it is the correction to the
over-broad rule added in the previous phase — a rule whose own reviewer had
warned in the same review that over-correcting into `apparatus` is also a defect,
because `apparatus` is terminal.

### 4.2 Row 10: the new class

**`rejected:base_import_blocked`** — the base state cannot import the test module
because of behaviour the fix changes.

Two verified shapes, deliberately not named after either one:

- **`missing_symbol`** — the test imports something the fix adds. `3a7fe26a`:
  `from pydantic.warnings import UnsupportedFieldAttributeWarning`, a class whose
  `+class …` line is in the code patch.
- **`warning_as_error`** — the test drops a suppression the fix makes
  unnecessary. `aa7705f7`: pydantic sets `filterwarnings = ['error']`, the parent
  still emits `PydanticExperimentalWarning` at import, and the test patch removes
  the `catch_warnings` wrapper that used to absorb it.

Naming the class after `missing_api` would repeat round 1's error of naming a
rule after one member of a family.

**Detection requires the after side.** These are indistinguishable from an
environment defect at the before side alone — both are just "ImportError while
collecting". The discriminator is whether the code patch clears the error:

- cleared → intrinsic to the commit → row 10
- persists → cause lives outside the commit → row 11, `apparatus`
- new errors appear after → row 11, `apparatus`, loud reason

**Cost**: one extra pytest run on candidates that currently die at the before
stage. Accepted — it is the only way to categorise at all, and it is what gives
`missing_api` a real denominator for the first time.

**These are excluded from the corpus**, honouring council decision 2: the
assertions never executed against unfixed code, so there is no evidence they
detect the bug. They are *counted* as their own class and become promotable when
the probe in §5.4 exists.

**Known inconsistency, recorded deliberately.** Move the same import from module
level into the test body and it becomes a call-phase `<failure>`, which decision
2 admits and labels. Same task, same oracle — different verdict based on where
the author typed `import`. This design does not resolve that; §5.4 is how it gets
resolved on evidence rather than convention.

### 4.3 Row 14: vanished is not failed

`broken` holds only tests that **ran and did not pass**. Ids present before and
absent after go to a separate `vanished` field and never produce a regression
verdict on their own.

The case where vanishing *is* breakage — the patch broke a file's import, so all
its tests disappear — is caught at row 11 by after-side collection errors. That
is the honest trigger and it does not depend on counting.

Safe because at mining time the tests are fixed: we apply the commit's real test
patch and nothing else, so a vanished id means the *reference patch* reshaped the
id space. It is not the failure mode of an agent deleting a test to go green —
the graded agent cannot touch tests at all.

**Why the existing rename reconciliation is insufficient on its own.** It groups
by `base_id`, everything before the first `[`, so every
`test_docs_examples[...]` across every documentation file lands in one bucket.
On `aa7705f7`: 9 vanished, 7 appeared, because each of the two edited markdown
files also *deleted* one code example along with 12 lines of prose. Two genuine
deletions poisoned the verdict for seven pure renames. Per-file keying is kept
for **reporting** — it correctly separates the deletions from the renames — but
it is no longer load-bearing for the verdict.

### 4.4 Status vocabulary after this change

```
validated  pass1_ok
rejected:unchanged  rejected:no_runnable_tests  rejected:base_import_blocked
rejected:unstable   rejected:regression_broken
not_minable:foreign_project  not_minable:straddles_dependency_bump
apparatus  error
```

`record.is_done` matches `rejected:` by prefix; **`not_minable:` must be added
there explicitly** — it is terminal, being a stable property of the commit.

## 5. Enumeration filters

All three produce **counted records, never silent drops.** Silent dropping is how
`missing_api` came to read zero.

### 5.1 Foreign project

Read the project name from `pyproject.toml` at the commit; if it is not the
expected name for this repo, record `not_minable:foreign_project`.

Config: expected project name, per repo, explicit. **Absence of `pyproject.toml`
is not foreignness** — pydantic v1 predates it. Out of range for this sweep, but
the rule must not misfire if the range is later widened.

Measured: 105 of 1,568 candidates overall; 2 of 21 in 2025Q3.

### 5.2 Dependency boundary

Compare exact `name==version` pins in `pyproject.toml` between parent and commit.
If any changes, record `not_minable:straddles_dependency_bump` naming the pin.

Correct by construction rather than a workaround: if a commit moves
`pydantic-core==2.37.2` to `==2.38.0`, the before state needs 2.37.2 and the
after state needs 2.38.0. No single quarter image can serve both, and the
container runs `--network none` by design so nothing can be installed at runtime.

Measured: 2 of 21 in 2025Q3, both currently apparatus, no false positives.

### 5.3 Non-pytest directories

Already built. `tests/mypy/` added alongside `tests/typechecking/`. Stays
explicit per-repo config, not a heuristic — a heuristic that guessed wrong would
silently drop real tests.

This one operates at **target selection**, not enumeration, because a commit can
touch both fixtures and real tests.

### 5.4 Deferred: the stub-import near-miss probe

Specified here, built later.

`rejected:base_import_blocked` capsules have an oracle-strength probe no other
class has, and it is mechanical. Because the test cannot import at base, there is
an obvious null patch: **declare the missing name, implement nothing.**

```python
class UnsupportedFieldAttributeWarning(CoreSchemaGenerationWarning):
    pass
```

If the tests then **pass**, the oracle only ever checked that a name exists —
worthless, discard the capsule. If they **fail**, the oracle tests real behaviour
and the capsule is sound and can be promoted into the corpus.

This is the "no-op / near-miss" control from the capsule schema, which has stood
marked *optional, not run* since the schema was written. For this one class it
can be generated from the failing import name with no human authoring. It also
separates the two sub-cases the council worried about: where the missing import
is *incidental* to the fix, stubbing it lets the file import and the real
assertions then run against unfixed code, so they should still fail.

## 6. The sweep

**Range: 2023Q3 – 2026Q3.** 13 quarters, 691 candidates, roughly 8 hours
including image builds.

pydantic v1 (pre-2023Q3) is excluded: it uses `setup.py`, those quarters fail
`uv export --frozen`, and an unanchored image is modern dependencies wearing an
old quarter's name — measuring against the wrong environment while every other
check still passes. Its API surface also no longer exists.

### 6.1 Three stages

**Stage 1 — 2025Q3 known-answer, ~20 min.** 21 candidates whose right answers we
established by hand.

**Predictions are written to `docs/miner/2026-08-12-sweep-predictions.md` and
committed BEFORE the run.** In the previous phase the predictions were partly
wrong and that was only noticed afterwards, which makes them a story rather than
a test. Recorded expectations:

| candidates | expected |
|---|---|
| the 7 currently validated | still validated, same oracles |
| `aa7705f7` | `validated` — row 9 now beats the collection check |
| `3a7fe26a` | `rejected:base_import_blocked` / `missing_symbol` |
| `eea593b0`, `0801aebc` | `not_minable:foreign_project` |
| `7c40924a`, `ac4f3ccb` | `not_minable:straddles_dependency_bump` |
| `9b438b49`, `dac3c437`, `568509c0` | `rejected:no_runnable_tests` |
| `f7a9b735` | `validated` — its recorded `broken` set was 7 vanished and **0 actually failed**, and its 3 oracle tests reproduced 1:1 in pass 2 |

A divergence from any row above is a finding to diagnose and write down, not a
number to adjust. The point of committing them first is that they can be wrong.

**Stage 2 — 2025Q4–2026Q3, 4 quarters, ~1 h.** Review the funnel together before
committing to the rest.

**Stage 3 — the remaining 8 quarters, unattended.**

### 6.2 What the sweep must produce

The two numbers the miner spec called its real deliverable, with denominators
pinned — this codebase has already carried two meanings of "adjudicated":

```
attempted    = entered a container
adjudicated  = attempted − apparatus − error
conversion   = validated / adjudicated
not_minable  = reported separately; never entered a container
```

Plus **cost per candidate** (wall-clock, container time) and **corpus composition
by failure label**, which is already a mandatory report section.

## 7. Testing

- **One unit test per verdict arm** — 15 arms, plain dicts, no Docker.
- **Explicit ordering tests** for the two pairs that have actually bitten us:
  row 9 must beat rows 10–12, and row 14 must ignore vanished ids. Ordering was
  the entire defect class in the previous phase.
- **Enumeration filters** unit-tested on the name and pin comparisons, including
  the negative cases: absent `pyproject.toml` is not foreign; a changed
  *non-pinned* dependency is not a boundary.
- **The known-answer run is the integration test.** `_measure` cannot be
  unit-tested end to end, and pretending otherwise is how the container-facing
  defects got through.
- The existing 90 tests must stay green throughout, and no assertion may be
  weakened to accommodate a new return shape.

## 8. Success criteria

1. 2025Q3 reproduces the committed predictions, or every divergence is diagnosed
   and written down.
2. Apparatus falls below the 10% tripwire. It is 47.6% today, and every one of
   those ten cases is addressed by an item in this spec.
3. The conversion rate and cost per candidate are measured across 13 quarters,
   with the denominators above.
4. `missing_api` has a real denominator for the first time, via
   `rejected:base_import_blocked` counts.
5. Enough validated capsules to run the model-tier experiment. The target is ~30;
   at 2025Q3's rate 691 candidates would far exceed it, but that rate is measured
   on 21 candidates and is not yet an estimate.

## 9. Open questions this design does not settle

- **Statement provenance.** The largest unmade decision before stage 3. The miner
  spec assumed council round 2 would cover it; round 2 was spent on the
  label-versus-gate question instead, because the evidence forced it.
- **The import-placement inconsistency** (§4.2). Resolved by §5.4, not here.
- **Docs-example tests as oracles.** Currently a non-issue: **0 of the 9 oracle
  tests on validated capsules are docs-example tests**, though thousands sit in
  the regression set. Their real damage was as the source of both false
  regressions, which §4.3 fixes. Revisit only if one ever carries a capsule.
- **`CONVERSION_RATE` recalibration** and the screener's `sqlalchemy` G7
  re-examination. Both wait on this sweep's numbers.
