import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import outcomes  # noqa: E402


_FINISH = {"kind": "sessionfinish", "exitstatus": 1}


def _jsonl(*records):
    """A COMPLETE report: the reporter's terminator is appended automatically.

    parse_report requires it, so a helper that omitted it would make every
    test here exercise the truncation path by accident. The tests that care
    about a missing terminator build their text without this helper.
    """
    return "\n".join(json.dumps(r) for r in (*records, _FINISH)) + "\n"


def test_parse_report_separates_collect_errors_from_tests():
    text = _jsonl(
        {"kind": "collect", "nodeid": "tests/test_bad.py", "when": "collect",
         "outcome": "failed", "message": "ImportError while importing..."},
        {"kind": "test", "nodeid": "tests/test_a.py::test_x", "when": "call",
         "outcome": "failed", "message": "assert 1 == 2"},
    )
    rep = outcomes.parse_report(text)
    assert [r.nodeid for r in rep.tests] == ["tests/test_a.py::test_x"]
    assert [r.nodeid for r in rep.collect] == ["tests/test_bad.py"]
    assert rep.collect[0].when == "collect"
    assert rep.exitstatus == 1


def test_parse_report_tolerates_blank_lines_and_preserves_message():
    text = "\n" + _jsonl(
        {"kind": "test", "nodeid": "t.py::a", "when": "call",
         "outcome": "failed",
         "message": "Failed: DID NOT RAISE <class 'ValueError'>"},
    ) + "\n"
    rep = outcomes.parse_report(text)
    assert rep.collect == []
    assert rep.tests[0].message == "Failed: DID NOT RAISE <class 'ValueError'>"


def test_parse_report_raises_on_malformed_line():
    # A truncated or interleaved write is OUR failure, not the commit's. It
    # must surface as apparatus, never be skipped into a smaller result set
    # that reads like "this commit changed nothing".
    try:
        outcomes.parse_report('{"kind": "test", "nodei')
    except ValueError as exc:
        # Pinned to the JSON complaint specifically: this input also lacks a
        # terminator, and without the check the test would pass for the wrong
        # reason once the truncation guard exists.
        assert "not valid JSON" in str(exc)
        return
    raise AssertionError("expected ValueError on malformed JSONL")


def test_parse_report_raises_when_the_sessionfinish_record_is_missing():
    # THE TRUNCATION DEFECT. If the plugin dies mid-session the JSONL can end
    # on a clean line boundary, so every line parses and the report looks like
    # a short-but-complete run. The candidate's oracle test is then simply
    # absent from `before`, no test goes fail->pass, and the commit books
    # `rejected:unchanged` -- our crash wearing the shape of a verdict. Only
    # the terminator's absence can tell the two apart.
    text = "\n".join(json.dumps(r) for r in (
        {"kind": "test", "nodeid": "t.py::a", "when": "call",
         "outcome": "passed", "message": None},
        {"kind": "test", "nodeid": "t.py::b", "when": "call",
         "outcome": "failed", "message": "assert 1 == 2"},
    )) + "\n"
    try:
        outcomes.parse_report(text)
    except ValueError as exc:
        assert "truncated" in str(exc)
        return
    raise AssertionError(
        "expected ValueError on a report with no sessionfinish record")


def test_parse_report_consumes_the_terminator_without_surfacing_it():
    # The terminator carries no nodeid, so leaking it into either list would
    # crash Record construction or fabricate a phantom outcome. It must be
    # consumed silently and the rest of the report parse normally.
    text = _jsonl(
        {"kind": "test", "nodeid": "t.py::a", "when": "call",
         "outcome": "passed", "message": None},
        {"kind": "collect", "nodeid": "t_bad.py", "when": "collect",
         "outcome": "failed", "message": "ImportError"},
    )
    rep = outcomes.parse_report(text)
    assert [r.nodeid for r in rep.tests] == ["t.py::a"]
    assert [r.nodeid for r in rep.collect] == ["t_bad.py"]
    assert outcomes.collapse(rep.tests) == {"t.py::a": outcomes.PASSED}


def test_parse_report_carries_the_exit_status_out_of_the_terminator():
    # THE CRASHED-SESSION DEFECT. pytest calls pytest_sessionfinish from
    # wrap_session's `finally` whenever sessionstart ran, so an INTERRUPTED (2)
    # or INTERNAL_ERROR (3) session writes SOME records and then the
    # terminator: the report is well-formed and terminated, and it is still a
    # partial measurement. The terminator's presence cannot tell the two apart;
    # only the status it carries can, so it must not be discarded here.
    text = "\n".join(json.dumps(r) for r in (
        {"kind": "test", "nodeid": "t.py::a", "when": "call",
         "outcome": "passed", "message": None},
        {"kind": "sessionfinish", "exitstatus": 3},
    )) + "\n"
    rep = outcomes.parse_report(text)
    assert rep.exitstatus == 3
    assert rep.exitstatus not in outcomes.OK_EXIT_STATUSES
    assert [r.nodeid for r in rep.tests] == ["t.py::a"]


def test_a_terminator_with_no_usable_exit_status_reads_as_none():
    # A missing or mangled value must NOT default to something acceptable. None
    # is deliberately absent from OK_EXIT_STATUSES, so the caller books
    # apparatus rather than concluding from a session it cannot vouch for.
    for finish in ({"kind": "sessionfinish"},
                   {"kind": "sessionfinish", "exitstatus": None},
                   {"kind": "sessionfinish", "exitstatus": "boom"}):
        text = json.dumps(finish) + "\n"
        rep = outcomes.parse_report(text)
        assert rep.exitstatus is None, finish
        assert rep.exitstatus not in outcomes.OK_EXIT_STATUSES


def test_ok_exit_statuses_are_exactly_the_three_conclusive_ones():
    # 0 all passed, 1 tests failed, 5 nothing collected. 2 interrupted,
    # 3 internal error and 4 usage error mean the session did not complete.
    # Pinned so a future edit cannot quietly widen the set.
    assert set(outcomes.OK_EXIT_STATUSES) == {0, 1, 5}


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


def test_collapse_treats_a_setup_phase_skip_as_skipped():
    # @pytest.mark.skip, @pytest.mark.skipif and a fixture calling
    # pytest.skip() all report at when="setup" and emit NO call record, so a
    # call-only rule left the node absent from the map entirely. Absent and
    # SKIPPED are not the same downstream: a code patch that adds a skipif
    # turned a previously-passing test into a vanished id -> `broken` -> a
    # false `rejected:regression_broken`. Marker skips are the common case;
    # before this, `skipped_after` could only ever fire for an in-body skip.
    recs = [outcomes.Record("t.py::a", "setup", "skipped",
                            "Skipped: needs python>=3.13")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.SKIPPED}


def test_collapse_a_failed_setup_still_outranks_a_skip():
    # ORDERING. A test whose fixture blew up never asserted, so it is an ERROR
    # whatever else is reported for it, and the skip must not overwrite that in
    # either record order.
    boom = outcomes.Record("t.py::a", "setup", "failed", "RuntimeError: boom")
    skip = outcomes.Record("t.py::a", "teardown", "skipped", "Skipped: x")
    assert outcomes.collapse([boom, skip]) == {"t.py::a": outcomes.ERROR}
    assert outcomes.collapse([skip, boom]) == {"t.py::a": outcomes.ERROR}


def test_collapse_a_teardown_skip_does_not_hide_a_failed_teardown():
    recs = [outcomes.Record("t.py::a", "call", "passed", None),
            outcomes.Record("t.py::a", "teardown", "failed", "IOError: x")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.ERROR}


def test_diff_routes_a_marker_skip_added_by_the_patch_to_skipped_after():
    # End to end for the defect above: the before side ran the test, the code
    # patch added a skipif, and the after side reports only a setup skip. That
    # is `skipped_after` -- visible, not a regression -- and emphatically not
    # `broken`, which would book a false rejected:regression_broken.
    before = outcomes.collapse(
        [outcomes.Record("t.py::a", "call", "passed", None)])
    after = outcomes.collapse(
        [outcomes.Record("t.py::a", "setup", "skipped", "Skipped: gated")])
    d = outcomes.diff(before, after)
    assert d["skipped_after"] == ["t.py::a"]
    assert d["broken"] == []


def test_label_bare_assert():
    assert outcomes.label("assert 1 == 2") == "assertion"


def test_label_named_assertion_error():
    assert outcomes.label("AssertionError: values differ") == "assertion"


def test_label_pytest_expectation_protocol():
    # Round 1 rejected all three of these as `other:unparsed`. They were half
    # of the classified f2p tests in the first batch. They are pytest's own
    # idiom for "the expected thing did not happen".
    assert outcomes.label(
        "Failed: DID NOT RAISE <class 'ValueError'>") == "expectation"
    assert outcomes.label(
        "Failed: DID NOT WARN. No warnings of type (<class 'X'>,) were "
        "emitted.") == "expectation"
    assert outcomes.label("Failed: nope") == "expectation"


def test_label_missing_api_family():
    assert outcomes.label(
        "AttributeError: module 'json' has no attribute 'z'") == "missing_api"
    assert outcomes.label(
        "ModuleNotFoundError: No module named 'x'") == "missing_api"
    assert outcomes.label("ImportError: cannot import name 'y'") == "missing_api"
    assert outcomes.label("NameError: name 'q' is not defined") == "missing_api"


def test_label_type_error_is_its_own_bucket():
    # Kept separate from missing_api: a changed signature is not the same
    # claim as an absent attribute, and round 1 explicitly left this open.
    assert outcomes.label("TypeError: f() takes 1 arg") == "type_error"


def test_label_dotted_library_exception_keeps_the_leaf_name():
    assert outcomes.label(
        "pydantic_core._pydantic_core.ValidationError: 1 validation error "
        "for Model") == "exception:ValidationError"


def test_label_library_warning_class_without_an_error_suffix():
    # PydanticDeprecatedSince20 ends in neither Error nor Exception nor
    # Warning. Matching on a suffix would drop it to unlabelled; matching on
    # "dotted identifier followed by a colon" keeps it.
    assert outcomes.label(
        "pydantic.warnings.PydanticDeprecatedSince20: The `__fields__` "
        "attribute is deprecated") == "exception:PydanticDeprecatedSince20"


def test_label_unrecognised_message_is_unlabelled_not_an_error():
    assert outcomes.label("something we have never seen") == "unlabelled"
    assert outcomes.label(None) == "unlabelled"
    assert outcomes.label("") == "unlabelled"


def test_unlabelled_is_not_a_rejection_signal():
    # Guards the council's central decision against a future "tidy-up" that
    # reintroduces a qualifying-class check. If someone adds a set of
    # acceptable labels, this test should make them think twice.
    for message in ["assert x", "Failed: nope", "AttributeError: nope",
                    "TypeError: nope", "Zzz.Qqq: nope", "gibberish", None]:
        assert isinstance(outcomes.label(message), str)
        assert outcomes.label(message) != ""


def test_base_id_strips_parametrisation():
    assert outcomes.base_id("t.py::test_a[1-2]") == "t.py::test_a"
    assert outcomes.base_id("t.py::test_a") == "t.py::test_a"
    # Nested brackets: split on the FIRST "[", so the whole tail goes.
    assert outcomes.base_id("t.py::test_a[p[q]]") == "t.py::test_a"
    assert outcomes.base_id("t.py::C::test_a[x - y]") == "t.py::C::test_a"


def test_diff_finds_fail_to_pass_and_pass_to_pass():
    before = {"t.py::new": outcomes.FAILURE, "t.py::old": outcomes.PASSED}
    after = {"t.py::new": outcomes.PASSED, "t.py::old": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["f2p"] == ["t.py::new"]
    assert d["p2p"] == ["t.py::old"]
    assert d["broken"] == []


def test_diff_excludes_an_error_base_from_f2p_and_records_it():
    # Decision 2: a test that could not run is not a usable base negative.
    # It is counted separately so a later audit can measure what the gate
    # costs -- the mistake round 1 made was rejecting without counting.
    before = {"t.py::a": outcomes.ERROR}
    after = {"t.py::a": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["f2p"] == []
    assert d["error_base"] == ["t.py::a"]


def test_diff_reports_a_genuinely_broken_test():
    before = {"t.py::a": outcomes.PASSED}
    after = {"t.py::a": outcomes.FAILURE}
    assert outcomes.diff(before, after)["broken"] == ["t.py::a"]


def test_diff_treats_a_renumbered_parametrisation_as_a_rename():
    # THE MEASURED DEFECT. Line numbers shift when the patch is applied, so
    # the parametrised ids change while the same number of cases still pass.
    # Booking this as `broken` fabricated 3 of the 10 rejections in the
    # 2025Q3 batch.
    before = {
        "t.py::test_docs[pydantic/types.py:1064-1069]": outcomes.PASSED,
        "t.py::test_docs[pydantic/types.py:2001-2010]": outcomes.PASSED,
    }
    after = {
        "t.py::test_docs[pydantic/types.py:1071-1076]": outcomes.PASSED,
        "t.py::test_docs[pydantic/types.py:2008-2017]": outcomes.PASSED,
    }
    d = outcomes.diff(before, after)
    assert d["broken"] == []
    assert d["renamed"] == [
        "t.py::test_docs[pydantic/types.py:1064-1069]",
        "t.py::test_docs[pydantic/types.py:2001-2010]",
    ]


def test_diff_does_not_hide_a_real_loss_behind_a_rename():
    # Two passed before, only one passes after. The count dropped, so this
    # is a genuine loss and must NOT be excused as a rename. Without this the
    # reconciliation would become a blanket amnesty for vanished tests.
    before = {"t.py::test_d[a]": outcomes.PASSED,
              "t.py::test_d[b]": outcomes.PASSED}
    after = {"t.py::test_d[c]": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["renamed"] == []
    assert d["broken"] == ["t.py::test_d[a]", "t.py::test_d[b]"]


def test_diff_treats_a_wholly_vanished_test_as_broken():
    before = {"t.py::gone": outcomes.PASSED}
    after = {}
    assert outcomes.diff(before, after)["broken"] == ["t.py::gone"]


def test_diff_requires_an_exact_nodeid_match_for_f2p():
    # A rename is forgivable for a regression test, which only needs to show
    # nothing was lost. It is NOT forgivable for the oracle: claiming f2p
    # across two differently-named tests would put a test in the oracle that
    # never failed on the before side.
    before = {"t.py::test_d[old]": outcomes.FAILURE}
    after = {"t.py::test_d[new]": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["f2p"] == []


def test_diff_ignores_skipped_tests_entirely():
    before = {"t.py::s": outcomes.SKIPPED}
    after = {"t.py::s": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert all(d[k] == [] for k in ("f2p", "p2p", "broken", "renamed",
                                    "error_base", "skipped_after"))


def test_diff_rename_reconciliation_requires_an_exact_swap():
    # THE REVIEWER'S DEFECT. A "count did not drop" rule can be satisfied by
    # an unrelated gain masking a genuine loss: test_a[2] vanishes but two
    # unrelated cases (test_a[3], test_a[4]) appear under the same function,
    # so the naive count check (2 before -> 3 after) would excuse it. The
    # reconciliation must instead require the vanished and appeared counts to
    # be exactly equal before excusing anything as a rename.
    before = {"t.py::test_a[1]": outcomes.PASSED,
              "t.py::test_a[2]": outcomes.PASSED}
    after = {"t.py::test_a[1]": outcomes.PASSED,
             "t.py::test_a[3]": outcomes.PASSED,
             "t.py::test_a[4]": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["renamed"] == []
    assert d["broken"] == ["t.py::test_a[2]"]


def test_diff_routes_a_newly_skipped_test_to_its_own_bucket():
    # A test that was passing and is now skipped is not broken -- it never
    # failed -- but it must not vanish either. It gets its own bucket so a
    # patch that skips a previously-passing test stays visible.
    before = {"t.py::a": outcomes.PASSED}
    after = {"t.py::a": outcomes.SKIPPED}
    d = outcomes.diff(before, after)
    assert d["skipped_after"] == ["t.py::a"]
    assert d["broken"] == []
    assert d["p2p"] == []
