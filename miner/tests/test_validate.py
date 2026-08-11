import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate  # noqa: E402


def test_split_paths_separates_tests_from_code():
    files = [
        "pydantic/main.py",
        "tests/test_main.py",
        "pydantic/_internal/_fields.py",
        "tests/benchmarks/test_north_star.py",
        "docs/index.md",
        "tests/fixtures/expected.json",
        "conftest.py",
    ]
    tests, code = validate.split_paths(files)
    assert tests == [
        "conftest.py",
        "tests/benchmarks/test_north_star.py",
        "tests/fixtures/expected.json",
        "tests/test_main.py",
    ]
    assert code == ["docs/index.md", "pydantic/_internal/_fields.py",
                    "pydantic/main.py"]
    assert not set(tests) & set(code)
    assert sorted(tests + code) == sorted(files)


def test_diff_outcomes_classifies_each_test():
    before = {
        "tests/test_a.py::test_new": "FAILED",
        "tests/test_a.py::test_old": "PASSED",
        "tests/test_a.py::test_breaks": "PASSED",
        "tests/test_a.py::test_skipped": "SKIPPED",
    }
    after = {
        "tests/test_a.py::test_new": "PASSED",
        "tests/test_a.py::test_old": "PASSED",
        "tests/test_a.py::test_breaks": "FAILED",
        "tests/test_a.py::test_skipped": "SKIPPED",
    }
    result = validate.diff_outcomes(before, after)
    assert result["f2p"] == ["tests/test_a.py::test_new"]
    assert result["p2p"] == ["tests/test_a.py::test_old"]
    assert result["broken"] == ["tests/test_a.py::test_breaks"]


SAMPLE = """
=========================== short test summary info ============================
FAILED test_sample.py::test_assertion - assert 1 == 2
FAILED test_sample.py::test_missing_attr - AttributeError: module 'json' has no attribute 'this_does_not_exist'
FAILED test_sample.py::test_missing_import - ModuleNotFoundError: No module named 'a_module_that_does_not_exist'
"""


def test_parse_and_classify_failures():
    parsed = validate.parse_failures(SAMPLE)
    assert validate.classify(parsed["test_sample.py::test_missing_attr"]) \
        == "missing_api"
    assert validate.classify(parsed["test_sample.py::test_missing_import"]) \
        == "missing_api"
    assert validate.classify(parsed["test_sample.py::test_assertion"]) \
        == "assertion"
    assert validate.classify("SyntaxError") == "structural"
    assert validate.classify("ValueError") == "other:ValueError"
