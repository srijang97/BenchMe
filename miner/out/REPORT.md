# Miner funnel - stages 0-2

## Funnel

- Candidates enumerated (stages 0-1): **1568**
- Attempted in stage 2: **21**
- Validated: **1**
- Rejected (a verdict about the commit): **10**
- Apparatus (a verdict about US -- excluded from every rate below): **10**
- Error (miner bug, non-terminal, retried after a fix -- also excluded): **0**
- Adjudicated (validated + rejected): **11**

**Conversion on adjudicated: 9.1%** (1/11). The screener assumed 2.2% on raw pairs.

For reference only, 1/21 of *attempted* is 4.8%. **That is not a conversion rate** and must not be quoted as one: its denominator includes 10 apparatus and 0 error records, which are candidates we failed to process, not candidates that failed to qualify.

> **The conversion rate below is a batch rate, not the corpus rate.** `candidates.stratified_order` walks the `(subsystem, size_bucket)` strata round-robin, which equalises strata rather than mass. 92% of all enumerated candidates sit in the top two subsystems (`pydantic`, `pydantic/_internal`), but a small batch draws only a token few from each. Reweighting by stratum mass is required before any of these percentages describe the corpus.

## All statuses

| status | kind | count |
|---|---|---|
| `apparatus` | **our fault** (terminal) | 10 |
| `rejected:other` | verdict on the commit | 4 |
| `rejected:unchanged` | verdict on the commit | 3 |
| `rejected:regression_broken` | verdict on the commit | 3 |
| `validated` | accepted | 1 |

## Oracle composition

How the fail-to-pass tests failed, across validated capsules. Descriptive only -- no label gates admission (`docs/council/ROUND_02_SYNTHESIS.md`).

_No validated capsules yet._

Apparatus: 10/21 adjudicated candidates (47.6%).

> **TRIPWIRE** apparatus is 47.6%, above the 10% threshold. Stop mining and fix tooling before spending more of the corpus.

## Rejections by class

| rejection class | count | what it means |
|---|---|---|
| `other` | 4 | no longer produced; a class from the retired base-negative classifier |
| `regression_broken` | 3 | code patch broke previously-passing tests |
| `unchanged` | 3 | no test went fail->pass (see the `before_failed` caveat) |
| `unstable` | 0 | pass 1's fail->pass set did not reproduce in the full-suite pass-2 run -- flaky or selection-dependent |

## Apparatus failures -- our fault, not the repo's

These are excluded from every rate above. Each one is a candidate we could not process; none is evidence about the commit.

| reason recorded | count |
|---|---|
| no test outcomes parsed on the before side | 10 |

### Root causes, recovered from the before logs

The recorded reason above is the symptom. These are the distinct causes behind it -- the breakdown that decides which of these are fixable.

| root cause | count |
|---|---|
| collection error aborted the session | 6 |
| missing dependency in the quarter image | 2 |
| pydantic-core version skew vs the pinned lockfile | 1 |
| pytest collected nothing from the touched test paths | 1 |

| sha | subsystem | root cause | evidence from before.log |
|---|---|---|---|
| `aa7705f7` | pydantic/experimental | collection error aborted the session | ERROR tests/test_experimental_arguments_schema.py - pydantic.warnings.PydanticExperimentalWarning: This module is experi |
| `eea593b0` | python | missing dependency in the quarter image | ModuleNotFoundError: No module named 'hypothesis' |
| `0801aebc` | python | missing dependency in the quarter image | ModuleNotFoundError: No module named 'hypothesis' |
| `9b438b49` | pydantic | collection error aborted the session | ERROR tests/mypy/modules/frozen_field.py - pydantic_core._pydantic_core.ValidationError: 1 validation error for Foo |
| `7c40924a` | pydantic/_internal | collection error aborted the session | ERROR tests/test_missing_sentinel.py - pydantic.errors.PydanticSchemaGenerationError: Unable to generate pydantic-core s |
| `ac4f3ccb` | pydantic/_internal | pydantic-core version skew vs the pinned lockfile | SystemError: The installed pydantic-core version (2 |
| `ba91a3c9` | pydantic | collection error aborted the session | ERROR tests/test_types.py |
| `3a7fe26a` | pydantic/_internal | collection error aborted the session | ERROR tests/test_fields.py |
| `dac3c437` | pydantic | collection error aborted the session | ERROR tests/typechecking/fields.py - TypeError: cannot specify both default and default_factory |
| `568509c0` | pydantic | pytest collected nothing from the touched test paths | no tests ran in 0.03s |

## Dependency drift on the before side (`before_failed`)

> **`before_failed` is a drift alarm, not a statistic.** The quarter image is anchored to the lockfile at the quarter's *last* commit, so a candidate from earlier in the window runs against dependencies that are slightly wrong for it -- measured at 840 of 6437 tests failing on the before side for `a59dab90`. If a candidate's own oracle test is among that drift, it fails on both sides, never becomes fail-to-pass, and is booked `rejected:unchanged`: an apparatus artefact wearing the shape of a verdict. Treat any `rejected:unchanged` with a high `before_failed` as unresolved rather than rejected. `anchored=true` does NOT clear this -- the image is anchored and still wrong for the commit.

| sha | status | before_failed / tests_seen | anchored | anchor |
|---|---|---|---|---|
| `a59dab90` | `validated` | 840 / 6437 | true | `c381a0032803` |
| `9c5eb6e5` | `rejected:regression_broken` | 7 / 6454 | true | `c381a0032803` |
| `27aaf685` | `rejected:other` | 2 / 229 | true | `c381a0032803` |
| `8a62354c` | `rejected:regression_broken` | 2 / 6508 | true | `c381a0032803` |
| `4406b2be` | `rejected:unchanged` | n/r | true | `c381a0032803` |
| `aa7705f7` | `apparatus` | n/r | true | `c381a0032803` |
| `eea593b0` | `apparatus` | n/r | true | `c381a0032803` |
| `0801aebc` | `apparatus` | n/r | true | `c381a0032803` |
| `9b438b49` | `apparatus` | n/r | true | `c381a0032803` |
| `7c40924a` | `apparatus` | n/r | true | `c381a0032803` |
| `ac4f3ccb` | `apparatus` | n/r | true | `c381a0032803` |
| `f7a9b735` | `rejected:other` | n/r | true | `c381a0032803` |
| `b0175de4` | `rejected:unchanged` | n/r | true | `c381a0032803` |
| `ba91a3c9` | `apparatus` | n/r | true | `c381a0032803` |
| `3a7fe26a` | `apparatus` | n/r | true | `c381a0032803` |
| `4057cd2b` | `rejected:unchanged` | n/r | true | `c381a0032803` |
| `71a02fcf` | `rejected:other` | n/r | true | `c381a0032803` |
| `e28f7544` | `rejected:other` | n/r | true | `c381a0032803` |
| `eb2c860a` | `rejected:regression_broken` | n/r | true | `c381a0032803` |
| `dac3c437` | `apparatus` | 0 | true | `c381a0032803` |
| `568509c0` | `apparatus` | 0 | true | `c381a0032803` |

`rejected:unchanged` records: 3; of those, 0 ran against a before side with at least one failing test and are therefore suspect rather than settled. `n/r` means the field was not recorded for that run and the drift is simply unknown -- it does not mean zero.

## `regression_broken` audit: real failure or vanished node id?

A broken node id that is ABSENT from the after log did not fail -- it was renamed. `test_docs.py::test_docstrings_examples` parametrises on source line ranges, so any code patch that shifts lines renames every id below it. A record with 0 genuinely-failing ids is apparatus wearing a verdict.

| sha | broken ids | failed in after | vanished from after | example |
|---|---|---|---|---|
| `eb2c860a` | 34 | 0 | 34 | `tests/test_docs.py::test_docstrings_examples[pydantic/types.py:1064-1069]` |
| `8a62354c` | 1 | 0 | 1 | `tests/test_docs.py::test_docstrings_examples[pydantic/json_schema.py:2689-2723` |
| `9c5eb6e5` | 1 | 0 | 1 | `tests/test_docs.py::test_docstrings_examples[pydantic/main.py:1177-1181]` |

## Validated candidates

| sha | subsystem | size | f2p tests | p2p | before_failed | anchored | subject |
|---|---|---|---|---|---|---|---|
| `a59dab90` | pydantic/_internal | s | 1 | 5277 | 840 / 6437 | true | Refactor logic to support Pydantic's `Field()` function in d |

The oracle node ids, so a reviewer can check them:

- `a59dab90` `tests/test_dataclasses.py::test_dataclasses_inheritance_bare_class_not_used` -> failed as `?` before the fix

## Candidates by quarter

| quarter | enumerated | attempted | validated |
|---|---|---|---|
| 2026Q3 | 22 | 0 | 0 |
| 2026Q2 | 16 | 0 | 0 |
| 2026Q1 | 19 | 0 | 0 |
| 2025Q4 | 36 | 0 | 0 |
| 2025Q3 | 21 | 21 | 1 |
| 2025Q2 | 31 | 0 | 0 |
| 2025Q1 | 52 | 0 | 0 |
| 2024Q4 | 72 | 0 | 0 |
| 2024Q3 | 95 | 0 | 0 |
| 2024Q2 | 40 | 0 | 0 |
| 2024Q1 | 77 | 0 | 0 |
| 2023Q4 | 64 | 0 | 0 |

