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
FAILED tests/test_p.py::test_case[a b] - AssertionError: boom
FAILED tests/test_q.py::test_range[1 - 2] - assert 1 == 2
FAILED tests/test_t.py::test_raises - Failed: DID NOT RAISE <class 'ValueError'>
ERROR tests/test_r.py::test_setup - RuntimeError: fixture blew up
ERROR tests/test_s.py
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

    # FIX D: node ids can contain spaces inside parametrised brackets. A
    # \S+ node-id pattern -- the same class of bug that dropped 1,604 of
    # 1,977 tests on the predecessor tool -- would truncate this node id to
    # "...test_case[a" and either miss the lookup or corrupt the key.
    assert "tests/test_p.py::test_case[a b]" in parsed
    assert validate.classify(parsed["tests/test_p.py::test_case[a b]"]) \
        == "assertion"

    # FIX E: parametrised brackets can themselves contain the literal " - "
    # separator, e.g. test_range[1 - 2] (confirmed against real pytest
    # output). A naive first-match split on " - " would cut the node id at
    # "...test_range[1" and leave "2] - assert 1 == 2" as a corrupted
    # "detail" -- the split must scan for a " - " that leaves brackets
    # balanced.
    assert "tests/test_q.py::test_range[1 - 2]" in parsed
    assert validate.classify(parsed["tests/test_q.py::test_range[1 - 2]"]) \
        == "assertion"

    # FIX A: only a genuine bare `assert` (or an empty detail) maps to
    # AssertionError. `Failed: DID NOT RAISE ...` from pytest.fail() has no
    # Error/Exception/Exit-suffixed name and does not start with "assert",
    # so it must NOT be silently admitted as a valid "assertion" base
    # negative -- it is unparseable and must be rejected and counted
    # instead.
    assert parsed["tests/test_t.py::test_raises"] == "unparsed"
    assert validate.classify(parsed["tests/test_t.py::test_raises"]) \
        == "other:unparsed"

    # FIX C: ERROR lines (fixture/setup errors and collection errors) never
    # reached an assertion, so they are always structural -- both the form
    # with a detail (setup error) and the form with none at all (a
    # collection error's real summary line is just "ERROR path", with no
    # " - detail" whatsoever).
    assert validate.classify(parsed["tests/test_r.py::test_setup"]) \
        == "structural"
    assert validate.classify(parsed["tests/test_s.py"]) == "structural"

    # FIX B: a FAILED line pytest actually emits always carries a detail.
    # One with no " - " separator can only be a terminal-width truncation
    # artifact and must raise rather than be silently skipped -- again the
    # same silent-drop failure class as the \S+ node-id regression.
    try:
        validate.parse_failures("FAILED tests/test_u.py::test_trunc\n")
    except RuntimeError:
        pass
    else:
        raise AssertionError(
            "expected RuntimeError for a FAILED line with no separator"
        )
