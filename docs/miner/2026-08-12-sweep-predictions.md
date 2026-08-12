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
