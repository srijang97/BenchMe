import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import outcomes  # noqa: E402


def _jsonl(*records):
    return "\n".join(json.dumps(r) for r in records) + "\n"


def test_parse_report_separates_collect_errors_from_tests():
    text = _jsonl(
        {"kind": "collect", "nodeid": "tests/test_bad.py", "when": "collect",
         "outcome": "failed", "message": "ImportError while importing..."},
        {"kind": "test", "nodeid": "tests/test_a.py::test_x", "when": "call",
         "outcome": "failed", "message": "assert 1 == 2"},
    )
    tests, collect = outcomes.parse_report(text)
    assert [r.nodeid for r in tests] == ["tests/test_a.py::test_x"]
    assert [r.nodeid for r in collect] == ["tests/test_bad.py"]
    assert collect[0].when == "collect"


def test_parse_report_tolerates_blank_lines_and_preserves_message():
    text = "\n" + _jsonl(
        {"kind": "test", "nodeid": "t.py::a", "when": "call",
         "outcome": "failed",
         "message": "Failed: DID NOT RAISE <class 'ValueError'>"},
    ) + "\n"
    tests, collect = outcomes.parse_report(text)
    assert collect == []
    assert tests[0].message == "Failed: DID NOT RAISE <class 'ValueError'>"


def test_parse_report_raises_on_malformed_line():
    # A truncated or interleaved write is OUR failure, not the commit's. It
    # must surface as apparatus, never be skipped into a smaller result set
    # that reads like "this commit changed nothing".
    try:
        outcomes.parse_report('{"kind": "test", "nodei')
    except ValueError:
        return
    raise AssertionError("expected ValueError on malformed JSONL")


def test_collapse_call_failure_is_a_failure():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.FAILURE}


def test_collapse_setup_failure_is_an_error_not_a_failure():
    # The whole admission gate. A broken fixture never reached an assertion,
    # so it is not evidence that the test detects the bug.
    recs = [outcomes.Record("t.py::a", "setup", "failed", "RuntimeError: boom")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.ERROR}


def test_collapse_attribute_error_in_body_is_a_failure():
    # Measured against pytest 8.3.4: an AttributeError raised inside a test
    # body reports at when="call". Round 1 rejected these as `missing_api`;
    # they are ordinary executed failures and must reach the label layer.
    recs = [outcomes.Record("t.py::a", "call", "failed",
                            "AttributeError: module 'json' has no attribute 'z'")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.FAILURE}


def test_collapse_teardown_failure_outranks_a_passing_call():
    recs = [outcomes.Record("t.py::a", "call", "passed", None),
            outcomes.Record("t.py::a", "teardown", "failed", "IOError: x")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.ERROR}


def test_collapse_records_passed_and_skipped():
    recs = [outcomes.Record("t.py::a", "call", "passed", None),
            outcomes.Record("t.py::b", "call", "skipped", "needs network")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.PASSED,
                                       "t.py::b": outcomes.SKIPPED}
