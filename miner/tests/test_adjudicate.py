"""Unit tests for the pure adjudicator.

`adjudicate` is the verdict logic extracted from runner._measure, which needs
Docker and was therefore untestable: every fix round in the previous phase was
an ORDERING bug that no unit test could catch. This module pins the current
behaviour arm by arm with plain dicts -- no container, no git, no filesystem.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adjudicate  # noqa: E402
import outcomes  # noqa: E402

A = "tests/test_a.py::test_one"
B = "tests/test_b.py::test_two"
C = "tests/test_c.py::test_three"


def _m(**kw):
    """A Measurements with harmless defaults; override what the test is about."""
    base = dict(
        pass2=False,
        targets=adjudicate.TargetSelection(["tests/test_a.py"], adjudicate.EMPTY_OK, None),
        before={}, after={}, before_records=[], before_collect=[],
        after_collect=[], pass1_f2p=None,
    )
    base.update(kw)
    return adjudicate.Measurements(**base)


def test_no_test_paths_is_a_verdict():
    v = adjudicate.adjudicate(_m(
        targets=adjudicate.TargetSelection([], adjudicate.EMPTY_NO_TEST_PATHS, None)))
    assert v.status == "rejected:unchanged"


def test_deleted_targets_are_a_verdict():
    # Pins CURRENT behaviour: EMPTY_DELETED books `rejected:unchanged` (the
    # reason the record already carries for this arm in _measure). The
    # `rejected:no_runnable_tests` rename is a LATER task, not this one.
    v = adjudicate.adjudicate(_m(
        targets=adjudicate.TargetSelection([], adjudicate.EMPTY_DELETED,
                                           "tests/test_gone.py")))
    assert v.status == "rejected:unchanged"


def test_absent_targets_are_ours():
    v = adjudicate.adjudicate(_m(
        targets=adjudicate.TargetSelection([], adjudicate.EMPTY_ABSENT, "tests/x.py")))
    assert v.status == "apparatus"


def test_empty_before_is_apparatus():
    v = adjudicate.adjudicate(_m(before={}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "apparatus"
    assert "before" in v.reason


def test_empty_after_is_apparatus():
    v = adjudicate.adjudicate(_m(before={"t.py::a": outcomes.PASSED}, after={}))
    assert v.status == "apparatus"
    assert "after" in v.reason


def test_no_f2p_is_unchanged():
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.PASSED}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "rejected:unchanged"


def test_pass1_success_records_the_oracle_and_its_label():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED},
        before_records=recs))
    assert v.status == "pass1_ok"
    assert v.fields["f2p"] == ["t.py::a"]
    assert v.fields["failure_labels"] == {"t.py::a": "assertion"}


def test_pass2_success_is_validated():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"], before_records=recs,
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "validated"
    assert v.fields["f2p_reproduced"] == ["t.py::a"]


def test_pass2_missing_pass1_oracle_is_a_miner_bug():
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=None,
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "error"


def test_pass2_unmeasured_oracle_is_apparatus():
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::gone"],
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "apparatus"


def test_pass2_measured_but_unreproduced_is_unstable():
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"],
        before={"t.py::a": outcomes.PASSED, "t.py::b": outcomes.FAILURE},
        after={"t.py::a": outcomes.PASSED, "t.py::b": outcomes.PASSED}))
    assert v.status == "rejected:unstable"
    assert v.fields["f2p"] == []


def test_pass2_regression_is_a_verdict():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"], before_records=recs,
        before={"t.py::a": outcomes.FAILURE, "t.py::keep": outcomes.PASSED},
        after={"t.py::a": outcomes.PASSED, "t.py::keep": outcomes.FAILURE}))
    assert v.status == "rejected:regression_broken"


def test_pass1_before_collection_error_is_apparatus():
    # In pass 1 the pytest targets ARE the candidate's own touched test files,
    # so a before-side collection error means one of THOSE files failed to
    # import. Under --continue-on-collection-errors its tests silently do not
    # run, the oracle is absent, and the candidate used to book
    # `rejected:unchanged` -- our dependency gap recorded as a terminal verdict
    # about the commit. Apparatus is the honest answer.
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.FAILURE},
        after={"t.py::a": outcomes.PASSED},
        before_collect=["tests/test_a.py", "tests/test_b.py"]))
    assert v.status == "apparatus"
    assert "2 of this candidate's own touched test file(s)" in v.reason
    assert "tests/test_a.py" in v.reason


def test_pass1_before_collection_error_outranks_empty_before():
    # Both arms would book apparatus, but the collection-error arm must win:
    # its reason names the file(s) that failed to import, which is the
    # diagnostic _measure's early return exists to surface.
    v = adjudicate.adjudicate(_m(
        before={}, after={},
        before_collect=["tests/test_a.py"]))
    assert v.status == "apparatus"
    assert "failed to collect" in v.reason
    assert "no test outcomes on the before side" not in v.reason


def test_pass2_before_collection_errors_are_not_apparatus():
    # DELIBERATELY NOT pass 2. The full suite in an anchored image carries
    # endemic collection errors from dependency drift that have nothing to do
    # with the candidate; a blanket rule there would terminally retire nearly
    # every candidate. The arm is guarded by `not m.pass2`, so pass 2 must
    # fall straight through to the measurement path.
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"],
        before={"t.py::a": outcomes.FAILURE},
        after={"t.py::a": outcomes.PASSED},
        before_collect=["tests/unrelated.py"]))
    assert v.status == "validated"


def test_a_collection_error_new_to_the_after_side_is_apparatus():
    # --continue-on-collection-errors means a file that stops importing after
    # the code patch does not FAIL -- its tests cease to exist. They vanish,
    # miss the rename rule, land in `broken`, and would book
    # `rejected:regression_broken` claiming tests "fail" that never ran. The
    # two sides were not measured comparably, so no verdict is honest.
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.FAILURE, "t.py::c": outcomes.PASSED},
        after={"t.py::a": outcomes.PASSED},
        after_collect=["tests/test_c.py"]))
    assert v.status == "apparatus"
    assert "not measured comparably" in v.reason
    assert "tests/test_c.py" in v.reason


def test_a_collection_error_on_both_sides_is_not_apparatus():
    # A constant of the environment removes the same nodes from both maps, so
    # the comparison stays symmetric. Booking apparatus on it would retire
    # every candidate in a suite with one permanently-broken import.
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"],
        before={"t.py::a": outcomes.FAILURE},
        after={"t.py::a": outcomes.PASSED},
        before_collect=["tests/test_c.py"],
        after_collect=["tests/test_c.py"]))
    assert v.status == "validated"


def test_a_collection_error_only_before_does_not_book_apparatus():
    # Only errors NEW to the after side are the asymmetry that invalidates the
    # comparison. A before-only collection error means the after side saw MORE
    # tests, which cannot manufacture a false regression.
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"],
        before={"t.py::a": outcomes.FAILURE},
        after={"t.py::a": outcomes.PASSED},
        before_collect=["tests/test_c.py"]))
    assert v.status == "validated"


def test_adjudicate_performs_no_io():
    """Guards the whole point of the extraction. If this module ever imports
    subprocess, quarters or record, the arms stop being testable without
    Docker and the ordering bugs come back."""
    src = (Path(__file__).resolve().parents[1] / "adjudicate.py").read_text(
        encoding="utf-8")
    for banned in ("import subprocess", "import quarters", "import record",
                   "import tierb", "open("):
        assert banned not in src, f"adjudicate.py must not use {banned!r}"


# --------------------------------------------------------------------------
# check_pass2_determinism (moved verbatim from test_runner.py with the
# extraction; the four outcomes are the contract that used to be pinned there)
# --------------------------------------------------------------------------

def test_missing_pass1_oracle_is_a_programming_error():
    # validate_quarter only reaches pass 2 through a pass1_ok record, which by
    # construction has a non-empty f2p, so an empty one here is a miner bug and
    # must be reported as itself rather than as apparatus or a rejection.
    for empty in (None, [], set()):
        check = adjudicate.check_pass2_determinism(empty, {A: "failed"}, [A])
        assert check.kind == adjudicate.PASS2_ERROR
        assert check.never_measured == []
        assert check.reproduced == []


def test_never_measured_pass1_node_is_apparatus():
    # A collection error in the full suite dropped A from pass 2 entirely,
    # while an unrelated node flipped. Absence from the before-run status map
    # is "never measured", which is a fact about us, not about the commit.
    check = adjudicate.check_pass2_determinism([A], {B: "failed"}, [B])
    assert check.kind == adjudicate.PASS2_APPARATUS
    assert check.never_measured == [A]
    assert check.reproduced == []


def test_apparatus_wins_when_pass2_measured_nothing_of_the_oracle():
    # The total case: pass 2's f2p is empty because every pass-1 oracle node
    # was dropped. This must NOT read as "nothing went fail->pass", which is a
    # verdict about the commit.
    check = adjudicate.check_pass2_determinism([A, B], {}, [])
    assert check.kind == adjudicate.PASS2_APPARATUS
    assert check.never_measured == [A, B]


def test_partially_measured_oracle_is_still_apparatus():
    # One of the two was measured and reproduced; the other was never measured.
    # Nothing can be concluded about the second, so the record cannot claim the
    # first as a validated oracle.
    check = adjudicate.check_pass2_determinism([A, B], {A: "failed"}, [A])
    assert check.kind == adjudicate.PASS2_APPARATUS
    assert check.never_measured == [B]
    assert check.reproduced == []


def test_all_measured_and_none_reproduced_is_unstable():
    # Both oracle nodes were measured this time and neither flipped: flaky or
    # selection-dependent, and that IS a verdict about the commit.
    check = adjudicate.check_pass2_determinism(
        [A, B], {A: "failed", B: "passed"}, [])
    assert check.kind == adjudicate.PASS2_UNSTABLE
    assert check.never_measured == []
    assert check.reproduced == []


def test_unstable_when_pass2_flips_only_unrelated_tests():
    other = "tests/test_c.py::test_three"
    check = adjudicate.check_pass2_determinism(
        [A], {A: "failed", other: "failed"}, [other])
    assert check.kind == adjudicate.PASS2_UNSTABLE
    assert check.reproduced == []


def test_reproduced_returns_the_intersection_sorted():
    # Only A reproduced; B was measured and did not flip; the unrelated node
    # pass 2 flipped on its own is not part of the oracle.
    other = "tests/test_c.py::test_three"
    check = adjudicate.check_pass2_determinism(
        [B, A], {A: "failed", B: "failed", other: "failed"}, [other, A])
    assert check.kind == adjudicate.PASS2_REPRODUCED
    assert check.never_measured == []
    assert check.reproduced == [A]


def test_reproduced_is_sorted_and_never_the_input_object():
    pass1 = [B, A]
    before = {A: "failed", B: "failed"}
    check = adjudicate.check_pass2_determinism(pass1, before, [B, A])
    assert check.reproduced == sorted([A, B])
    assert check.reproduced is not pass1


def test_a_non_skipped_before_status_still_counts_as_measured():
    # Presence in the map is enough for every status EXCEPT skipped: a node
    # that passed, failed or errored in pass 2's before run genuinely executed,
    # so "measured and did not flip" is a fact about the commit. Only `skipped`
    # is carved out (see the test below); this pins the other three so the
    # carve-out cannot quietly widen into "any status but failure".
    for status in (outcomes.PASSED, outcomes.FAILURE, outcomes.ERROR):
        check = adjudicate.check_pass2_determinism([A], {A: status}, [])
        assert check.kind == adjudicate.PASS2_UNSTABLE, status
        assert check.never_measured == []


def test_a_skipped_oracle_node_was_not_measured_and_is_apparatus():
    # The node was collected, so it IS in the status map -- but its body never
    # ran, so it cannot have flipped. Booking `rejected:unstable` off a skip
    # would state a verdict about the COMMIT on the strength of a marker or an
    # environment gate, which is a selection artefact and ours.
    check = adjudicate.check_pass2_determinism([A], {A: outcomes.SKIPPED}, [])
    assert check.kind == adjudicate.PASS2_APPARATUS
    assert check.never_measured == [A]
    assert check.reproduced == []


def test_a_skip_taints_the_record_even_when_the_rest_reproduced():
    # A was measured and reproduced; B was skipped. Nothing can be concluded
    # about B, so the record cannot claim A as a validated oracle -- the same
    # rule the never-measured case already follows.
    check = adjudicate.check_pass2_determinism(
        [A, B], {A: outcomes.FAILURE, B: outcomes.SKIPPED}, [A])
    assert check.kind == adjudicate.PASS2_APPARATUS
    assert check.never_measured == [B]
    assert check.reproduced == []


def test_a_skip_outranks_an_apparent_reproduction_of_the_same_node():
    # Defensive: if pass 2's diff somehow named a node its before run recorded
    # as skipped, the skip wins. Reproduction must never be concluded from a
    # node that did not execute on the before side.
    check = adjudicate.check_pass2_determinism([A], {A: outcomes.SKIPPED}, [A])
    assert check.kind == adjudicate.PASS2_APPARATUS
    assert check.reproduced == []
