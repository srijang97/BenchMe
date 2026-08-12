# 2025Q3 Known-Answer Sweep Predictions

Committed BEFORE running stage 1 validation of the 21 2025Q3 candidates.

## Predictions Table

| Candidate | Predicted Status | Notes |
|---|---|---|
| `71a02fcf` | `validated` | Same oracle as today |
| `e28f7544` | `validated` | Same oracle as today |
| `eb2c860a` | `validated` | Same oracle as today |
| `a59dab90` | `validated` | Same oracle as today |
| `27aaf685` | `validated` | Same oracle as today |
| `8a62354c` | `validated` | Same oracle as today |
| `9c5eb6e5` | `validated` | Same oracle as today |
| `aa7705f7` | `validated` | Row 9 now beats the collection check |
| `f7a9b735` | `validated` | Its `broken` set was 7 vanished and 0 failed |
| `3a7fe26a` | `rejected:base_import_blocked` | `missing_symbol` sublabel |
| `eea593b0` | `not_minable:foreign_project` | Pydantic-core commit grafted into clone |
| `0801aebc` | `not_minable:foreign_project` | Pydantic-core commit grafted into clone |
| `7c40924a` | `not_minable:straddles_dependency_bump` | Exact pin change |
| `ac4f3ccb` | `not_minable:straddles_dependency_bump` | Exact pin change |
| `9b438b49` | `not_minable:no_pytest_tests` | Only touched NON_PYTEST_TEST_DIRS |
| `dac3c437` | `not_minable:no_pytest_tests` | Only touched NON_PYTEST_TEST_DIRS |
| `568509c0` | `not_minable:no_pytest_tests` | Only touched NON_PYTEST_TEST_DIRS |
| `4406b2be` | `rejected:unchanged` | Unchanged verdict |
| `b0175de4` | `rejected:unchanged` | Unchanged verdict |
| `4057cd2b` | `rejected:unchanged` | Unchanged verdict |
| `ba91a3c9` | `rejected:base_import_blocked` or `apparatus` | Collect error in `tests/test_types.py`; `base_import_blocked` if patch clears it, `apparatus` if not |

## Actual Results (2026-08-12 Stage 1 Run)

| Candidate | Predicted Status | Actual Status | Result | Notes |
|---|---|---|---|---|
| `71a02fcf` | `validated` | `validated` | HIT | 1/1 oracle reproduced |
| `e28f7544` | `validated` | `validated` | HIT | 1/1 oracle reproduced |
| `eb2c860a` | `validated` | `validated` | HIT | 1/1 oracle reproduced |
| `a59dab90` | `validated` | `validated` | HIT | 1/1 oracle reproduced |
| `27aaf685` | `validated` | `validated` | HIT | 2/2 oracle reproduced |
| `8a62354c` | `validated` | `validated` | HIT | 2/2 oracle reproduced |
| `9c5eb6e5` | `validated` | `validated` | HIT | 1/1 oracle reproduced |
| `aa7705f7` | `validated` | `validated` | HIT | 1/1 oracle reproduced (row 9 cleared collect error) |
| `f7a9b735` | `validated` | `validated` | HIT | 3/3 oracle reproduced (vanished tests not counted as broken) |
| `3a7fe26a` | `rejected:base_import_blocked` | `rejected:base_import_blocked` | HIT | `other` import block sublabel |
| `eea593b0` | `not_minable:foreign_project` | `not_minable:foreign_project` | HIT | Filtered before Docker |
| `0801aebc` | `not_minable:foreign_project` | `not_minable:foreign_project` | HIT | Filtered before Docker |
| `7c40924a` | `not_minable:straddles_dependency_bump` | `not_minable:straddles_dependency_bump` | HIT | Filtered before Docker |
| `ac4f3ccb` | `not_minable:straddles_dependency_bump` | `not_minable:straddles_dependency_bump` | HIT | Filtered before Docker |
| `9b438b49` | `not_minable:no_pytest_tests` | `not_minable:no_pytest_tests` | HIT | Filtered before Docker |
| `dac3c437` | `not_minable:no_pytest_tests` | `not_minable:no_pytest_tests` | HIT | Filtered before Docker |
| `568509c0` | `not_minable:no_pytest_tests` | `not_minable:no_pytest_tests` | HIT | Filtered before Docker |
| `4406b2be` | `rejected:unchanged` | `rejected:unchanged` | HIT | No test went fail->pass |
| `b0175de4` | `rejected:unchanged` | `rejected:unchanged` | HIT | No test went fail->pass |
| `4057cd2b` | `rejected:unchanged` | `rejected:unchanged` | HIT | No test went fail->pass |
| `ba91a3c9` | `rejected:base_import_blocked` or `apparatus` | `rejected:base_import_blocked` | HIT | Patch cleared collect error |

## Summary Metrics

- **Accuracy**: 21 / 21 exact hits (100%)
- **Apparatus rate**: **0.0%** (0 / 21 processed, down from 47.6%) — well below the 10.0% tripwire.
- **Validated count**: 9 / 21 candidates validated (up from 1).
- **Determinism**: 9 / 9 validated capsules reproduced in pass 2 (100%).
- **Not minable**: 7 / 21 candidates correctly routed before Docker (3 no pytest tests, 2 foreign project, 2 dependency bump straddles).
