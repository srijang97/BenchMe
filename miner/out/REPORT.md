# Miner funnel - stages 0-2

## Funnel

- Candidates enumerated (stages 0-1): **1568**
- Attempted in stage 2: **21**
- Validated: **7**
- Rejected (a verdict about the commit): **8**
- Apparatus (a verdict about US -- excluded from every rate below): **6**
- Error (miner bug, non-terminal, retried after a fix -- also excluded): **0**
- Adjudicated (validated + rejected): **15**

**Conversion on adjudicated: 46.7%** (7/15). The screener assumed 2.2% on raw pairs.

For reference only, 7/21 of *attempted* is 33.3%. **That is not a conversion rate** and must not be quoted as one: its denominator includes 6 apparatus and 0 error records, which are candidates we failed to process, not candidates that failed to qualify.

> **The conversion rate below is a batch rate, not the corpus rate.** `candidates.stratified_order` walks the `(subsystem, size_bucket)` strata round-robin, which equalises strata rather than mass. 92% of all enumerated candidates sit in the top two subsystems (`pydantic`, `pydantic/_internal`), but a small batch draws only a token few from each. Reweighting by stratum mass is required before any of these percentages describe the corpus.

## All statuses

| status | kind | count |
|---|---|---|
| `validated` | accepted | 7 |
| `rejected:unchanged` | verdict on the commit | 6 |
| `apparatus` | **our fault** (terminal) | 6 |
| `rejected:regression_broken` | verdict on the commit | 2 |

## Oracle composition

How the fail-to-pass tests failed, across validated capsules. Descriptive only -- no label gates admission (`docs/council/ROUND_02_SYNTHESIS.md`).

| label | count | share |
|---|---|---|
| `assertion` | 5 | 55.6% |
| `expectation` | 2 | 22.2% |
| `exception:PydanticDeprecatedSince20` | 1 | 11.1% |
| `exception:ValidationError` | 1 | 11.1% |

Apparatus: 6/21 adjudicated candidates (28.6%).

> **TRIPWIRE** apparatus is 28.6%, above the 10% threshold. Stop mining and fix tooling before spending more of the corpus.

## Rejections by class

| rejection class | count | what it means |
|---|---|---|
| `unchanged` | 6 | no test went fail->pass (see the `before_failed` caveat) |
| `regression_broken` | 2 | code patch broke previously-passing tests |
| `unstable` | 0 | pass 1's fail->pass set did not reproduce in the full-suite pass-2 run -- flaky or selection-dependent |

## Apparatus failures -- our fault, not the repo's

These are excluded from every rate above. Each one is a candidate we could not process; none is evidence about the commit.

| reason recorded | count |
|---|---|
| no test outcomes on the before side | 3 |
| before report: reporter wrote nothing for the before run (rc=1); pytest exited 4: ImportError while loading co | 2 |
| before report: reporter wrote nothing for the before run (rc=1); pytest exited 4: tic/version.py:95: in _ensur | 1 |

### Root causes, recovered from the before logs

The recorded reason above is the symptom. These are the distinct causes behind it -- the breakdown that decides which of these are fixable.

| root cause | count |
|---|---|
| not determined from the log | 3 |
| missing dependency in the quarter image | 2 |
| pydantic-core version skew vs the pinned lockfile | 1 |

| sha | subsystem | root cause | evidence from before.log |
|---|---|---|---|
| `eea593b0` | python | missing dependency in the quarter image | ModuleNotFoundError: No module named 'hypothesis' |
| `0801aebc` | python | missing dependency in the quarter image | ModuleNotFoundError: No module named 'hypothesis' |
| `9b438b49` | pydantic | - | - |
| `7c40924a` | pydantic/_internal | - | - |
| `ac4f3ccb` | pydantic/_internal | pydantic-core version skew vs the pinned lockfile | SystemError: The installed pydantic-core version (2 |
| `ba91a3c9` | pydantic | - | - |

## Dependency drift on the before side (`before_failed`)

> **`before_failed` is a drift alarm, not a statistic.** The quarter image is anchored to the lockfile at the quarter's *last* commit, so a candidate from earlier in the window runs against dependencies that are slightly wrong for it -- measured at 840 of 6437 tests failing on the before side for `a59dab90`. If a candidate's own oracle test is among that drift, it fails on both sides, never becomes fail-to-pass, and is booked `rejected:unchanged`: an apparatus artefact wearing the shape of a verdict. Treat any `rejected:unchanged` with a high `before_failed` as unresolved rather than rejected. `anchored=true` does NOT clear this -- the image is anchored and still wrong for the commit.

| sha | status | before_failed / tests_seen | anchored | anchor |
|---|---|---|---|---|
| `a59dab90` | `validated` | 840 / 6261 | true | `05b973b30671` |
| `b0175de4` | `rejected:unchanged` | 492 / 768 | true | `05b973b30671` |
| `4057cd2b` | `rejected:unchanged` | 477 / 528 | true | `05b973b30671` |
| `f7a9b735` | `rejected:regression_broken` | 9 / 6281 | true | `05b973b30671` |
| `71a02fcf` | `validated` | 7 / 6278 | true | `05b973b30671` |
| `9c5eb6e5` | `validated` | 7 / 6276 | true | `05b973b30671` |
| `aa7705f7` | `rejected:regression_broken` | 6 / 6258 | true | `05b973b30671` |
| `3a7fe26a` | `rejected:unchanged` | 3 / 36 | true | `05b973b30671` |
| `27aaf685` | `validated` | 3 / 6283 | true | `05b973b30671` |
| `8a62354c` | `validated` | 2 / 6330 | true | `05b973b30671` |
| `e28f7544` | `validated` | 1 / 6332 | true | `05b973b30671` |
| `eb2c860a` | `validated` | 1 / 6331 | true | `05b973b30671` |
| `4406b2be` | `rejected:unchanged` | 0 / 711 | true | `05b973b30671` |
| `eea593b0` | `apparatus` | n/r | true | `05b973b30671` |
| `0801aebc` | `apparatus` | n/r | true | `05b973b30671` |
| `9b438b49` | `apparatus` | 0 | true | `05b973b30671` |
| `7c40924a` | `apparatus` | 0 | true | `05b973b30671` |
| `ac4f3ccb` | `apparatus` | n/r | true | `05b973b30671` |
| `ba91a3c9` | `apparatus` | 0 | true | `05b973b30671` |
| `dac3c437` | `rejected:unchanged` | n/r | true | `05b973b30671` |
| `568509c0` | `rejected:unchanged` | n/r | true | `05b973b30671` |

`rejected:unchanged` records: 6; of those, 3 ran against a before side with at least one failing test and are therefore suspect rather than settled. `n/r` means the field was not recorded for that run and the drift is simply unknown -- it does not mean zero.

## `regression_broken` audit: real failure or vanished node id?

A broken node id that is ABSENT from the after log did not fail -- it was renamed. `test_docs.py::test_docstrings_examples` parametrises on source line ranges, so any code patch that shifts lines renames every id below it. A record with 0 genuinely-failing ids is apparatus wearing a verdict.

| sha | broken ids | failed in after | vanished from after | example |
|---|---|---|---|---|
| `aa7705f7` | 9 | 0 | 9 | `tests/test_docs.py::test_docs_examples[docs/concepts/experimental.md:121-144]` |
| `f7a9b735` | 7 | 0 | 7 | `tests/test_docs.py::test_docs_examples[docs/concepts/serialization.md:722-745]` |

## Validated candidates

| sha | subsystem | size | f2p tests | reproduced | p2p | before_failed | anchored | subject |
|---|---|---|---|---|---|---|---|---|
| `71a02fcf` | pydantic/_internal | s | 1 | 1 / 1 | 6124 | 7 / 6278 | true | Update `__fields__` attribute deprecation message (#12157) |
| `e28f7544` | pydantic/_internal | xs | 1 | 1 / 1 | 6184 | 1 / 6332 | true | Warn if registering virtual subclasses on Pydantic models (# |
| `eb2c860a` | pydantic | xs | 1 | 1 / 1 | 6149 | 1 / 6331 | true | Fix `ImportString` JSON serialization for objects with a `na |
| `a59dab90` | pydantic/_internal | s | 1 | 1 / 1 | 5277 | 840 / 6261 | true | Refactor logic to support Pydantic's `Field()` function in d |
| `27aaf685` | pydantic | xs | 2 | 2 / 2 | 6133 | 3 / 6283 | true | Allow to use property setters on Pydantic dataclasses with ` |
| `8a62354c` | pydantic | xs | 2 | 2 / 2 | 6180 | 2 / 6330 | true | Respect custom title in functions JSON Schema (#11892) |
| `9c5eb6e5` | pydantic | xs | 1 | 1 / 1 | 6121 | 7 / 6276 | true | Fix `__getattr__()` behavior on Pydantic models when a prope |

The oracle node ids, so a reviewer can check them:

- `71a02fcf` `tests/test_deprecated.py::test_fields` -> failed as `exception:PydanticDeprecatedSince20` before the fix
- `e28f7544` `tests/test_abc.py::test_register_warning_on_abstract_base_classes_subclassing_model` -> failed as `expectation` before the fix
- `eb2c860a` `tests/test_types.py::test_import_string_thing_with_name` -> failed as `assertion` before the fix
- `a59dab90` `tests/test_dataclasses.py::test_dataclasses_inheritance_bare_class_not_used` -> failed as `assertion` before the fix
- `27aaf685` `tests/test_dataclasses.py::test_frozen_with_validate_assignment` -> failed as `expectation` before the fix
- `27aaf685` `tests/test_dataclasses.py::test_validate_assignment_properties` -> failed as `exception:ValidationError` before the fix
- `8a62354c` `tests/test_validate_call.py::test_json_schema_custom_title` -> failed as `assertion` before the fix
- `8a62354c` `tests/test_validate_call.py::test_json_schema_title_not_set_on_ref` -> failed as `assertion` before the fix
- `9c5eb6e5` `tests/test_fields.py::test_computed_field_raises_correct_attribute_error` -> failed as `assertion` before the fix

## Candidates by quarter

| quarter | enumerated | attempted | validated |
|---|---|---|---|
| 2026Q3 | 22 | 0 | 0 |
| 2026Q2 | 16 | 0 | 0 |
| 2026Q1 | 19 | 0 | 0 |
| 2025Q4 | 36 | 0 | 0 |
| 2025Q3 | 21 | 21 | 7 |
| 2025Q2 | 31 | 0 | 0 |
| 2025Q1 | 52 | 0 | 0 |
| 2024Q4 | 72 | 0 | 0 |
| 2024Q3 | 95 | 0 | 0 |
| 2024Q2 | 40 | 0 | 0 |
| 2024Q1 | 77 | 0 | 0 |
| 2023Q4 | 64 | 0 | 0 |

