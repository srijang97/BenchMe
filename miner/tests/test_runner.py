"""Unit tests for the pass-2 determinism decision.

`_measure` needs Docker, so the decision it makes about pass 1's oracle lives
in `runner.check_pass2_determinism`, which is pure: dicts and lists in, a
Pass2Check out. These tests pin all four outcomes, because the whole point of
the check is that three DIFFERENT kinds of record come out of it -- `error`
(our bug), `apparatus` (our tooling did not measure it) and a verdict about the
commit -- and a regression that collapsed any two of them would be invisible in
the mined data.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import runner  # noqa: E402

A = "tests/test_a.py::test_one"
B = "tests/test_b.py::test_two"


def test_missing_pass1_oracle_is_a_programming_error():
    # validate_quarter only reaches pass 2 through a pass1_ok record, which by
    # construction has a non-empty f2p, so an empty one here is a miner bug and
    # must be reported as itself rather than as apparatus or a rejection.
    for empty in (None, [], set()):
        check = runner.check_pass2_determinism(empty, {A: "failed"}, [A])
        assert check.kind == runner.PASS2_ERROR
        assert check.never_measured == []
        assert check.reproduced == []


def test_never_measured_pass1_node_is_apparatus():
    # A collection error in the full suite dropped A from pass 2 entirely,
    # while an unrelated node flipped. Absence from the before-run status map
    # is "never measured", which is a fact about us, not about the commit.
    check = runner.check_pass2_determinism([A], {B: "failed"}, [B])
    assert check.kind == runner.PASS2_APPARATUS
    assert check.never_measured == [A]
    assert check.reproduced == []


def test_apparatus_wins_when_pass2_measured_nothing_of_the_oracle():
    # The total case: pass 2's f2p is empty because every pass-1 oracle node
    # was dropped. This must NOT read as "nothing went fail->pass", which is a
    # verdict about the commit.
    check = runner.check_pass2_determinism([A, B], {}, [])
    assert check.kind == runner.PASS2_APPARATUS
    assert check.never_measured == [A, B]


def test_partially_measured_oracle_is_still_apparatus():
    # One of the two was measured and reproduced; the other was never measured.
    # Nothing can be concluded about the second, so the record cannot claim the
    # first as a validated oracle.
    check = runner.check_pass2_determinism([A, B], {A: "failed"}, [A])
    assert check.kind == runner.PASS2_APPARATUS
    assert check.never_measured == [B]
    assert check.reproduced == []


def test_all_measured_and_none_reproduced_is_unstable():
    # Both oracle nodes were measured this time and neither flipped: flaky or
    # selection-dependent, and that IS a verdict about the commit.
    check = runner.check_pass2_determinism(
        [A, B], {A: "failed", B: "passed"}, [])
    assert check.kind == runner.PASS2_UNSTABLE
    assert check.never_measured == []
    assert check.reproduced == []


def test_unstable_when_pass2_flips_only_unrelated_tests():
    other = "tests/test_c.py::test_three"
    check = runner.check_pass2_determinism(
        [A], {A: "failed", other: "failed"}, [other])
    assert check.kind == runner.PASS2_UNSTABLE
    assert check.reproduced == []


def test_reproduced_returns_the_intersection_sorted():
    # Only A reproduced; B was measured and did not flip; the unrelated node
    # pass 2 flipped on its own is not part of the oracle.
    other = "tests/test_c.py::test_three"
    check = runner.check_pass2_determinism(
        [B, A], {A: "failed", B: "failed", other: "failed"}, [other, A])
    assert check.kind == runner.PASS2_REPRODUCED
    assert check.never_measured == []
    assert check.reproduced == [A]


def test_reproduced_is_sorted_and_never_the_input_object():
    pass1 = [B, A]
    before = {A: "failed", B: "failed"}
    check = runner.check_pass2_determinism(pass1, before, [B, A])
    assert check.reproduced == sorted([A, B])
    assert check.reproduced is not pass1


def test_membership_only_reads_the_status_map_keys():
    # The map's values are pytest statuses and the check must not depend on
    # them: a node that passed in pass 2's before run was still MEASURED.
    check = runner.check_pass2_determinism([A], {A: "passed"}, [])
    assert check.kind == runner.PASS2_UNSTABLE
