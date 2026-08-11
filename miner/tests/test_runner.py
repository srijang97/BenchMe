"""Unit tests for the pass-2 determinism decision.

`_measure` needs Docker, so the decision it makes about pass 1's oracle lives
in `runner.check_pass2_determinism`, which is pure: dicts and lists in, a
Pass2Check out. These tests pin all four outcomes, because the whole point of
the check is that three DIFFERENT kinds of record come out of it -- `error`
(our bug), `apparatus` (our tooling did not measure it) and a verdict about the
commit -- and a regression that collapsed any two of them would be invisible in
the mined data.

The second half of the file tests `_measure` itself with every container-facing
call stubbed out. Deciding the right kind is only half the job: the kind then
has to REACH the record, and round 3 found it did not -- `PASS2_UNSTABLE` sat
below an early return that fired first on the commonest unstable shape, so the
verdict was real and unreachable. A test of the pure function alone cannot see
that, because the pure function was right.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import outcomes  # noqa: E402
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


def test_a_non_skipped_before_status_still_counts_as_measured():
    # Presence in the map is enough for every status EXCEPT skipped: a node
    # that passed, failed or errored in pass 2's before run genuinely executed,
    # so "measured and did not flip" is a fact about the commit. Only `skipped`
    # is carved out (see the test below); this pins the other three so the
    # carve-out cannot quietly widen into "any status but failure".
    for status in (outcomes.PASSED, outcomes.FAILURE, outcomes.ERROR):
        check = runner.check_pass2_determinism([A], {A: status}, [])
        assert check.kind == runner.PASS2_UNSTABLE, status
        assert check.never_measured == []


def test_a_skipped_oracle_node_was_not_measured_and_is_apparatus():
    # The node was collected, so it IS in the status map -- but its body never
    # ran, so it cannot have flipped. Booking `rejected:unstable` off a skip
    # would state a verdict about the COMMIT on the strength of a marker or an
    # environment gate, which is a selection artefact and ours.
    check = runner.check_pass2_determinism([A], {A: outcomes.SKIPPED}, [])
    assert check.kind == runner.PASS2_APPARATUS
    assert check.never_measured == [A]
    assert check.reproduced == []


def test_a_skip_taints_the_record_even_when_the_rest_reproduced():
    # A was measured and reproduced; B was skipped. Nothing can be concluded
    # about B, so the record cannot claim A as a validated oracle -- the same
    # rule the never-measured case already follows.
    check = runner.check_pass2_determinism(
        [A, B], {A: outcomes.FAILURE, B: outcomes.SKIPPED}, [A])
    assert check.kind == runner.PASS2_APPARATUS
    assert check.never_measured == [B]
    assert check.reproduced == []


def test_a_skip_outranks_an_apparent_reproduction_of_the_same_node():
    # Defensive: if pass 2's diff somehow named a node its before run recorded
    # as skipped, the skip wins. Reproduction must never be concluded from a
    # node that did not execute on the before side.
    check = runner.check_pass2_determinism([A], {A: outcomes.SKIPPED}, [A])
    assert check.kind == runner.PASS2_APPARATUS
    assert check.reproduced == []


# --------------------------------------------------------------------------
# _measure: does the decided kind actually reach the record?
# --------------------------------------------------------------------------

SHA = "a" * 40
PARENT = "b" * 40


def _measure(monkeypatch, before, after, pass1_f2p=None, pass2=True,
             messages=None):
    """Run `runner._measure` with every container-facing call stubbed.

    Everything replaced here is I/O against Docker or git; the branch structure
    under test is untouched. `before` and `after` are collapsed status maps,
    exactly what `_pytest` returns in production.
    """
    messages = messages or {}
    monkeypatch.setattr(runner, "_checkout", lambda *a, **k: None)
    monkeypatch.setattr(runner, "_apply", lambda *a, **k: None)
    monkeypatch.setattr(runner.validate, "make_patch", lambda *a, **k: "patch")
    monkeypatch.setattr(runner, "_runnable_targets",
                        lambda *a, **k: (["tests/test_a.py"], None))
    monkeypatch.setattr(runner, "_pass2_targets",
                        lambda *a, **k: (["tests"], None))

    def fake_pytest(container, workdir, targets, log_path, phase,
                    timeout=1800):
        status = before if phase == runner.BEFORE else after
        records = [outcomes.Record(n, "call", "failed", messages.get(n))
                   for n, s in status.items() if s == outcomes.FAILURE]
        return dict(status), records, [], ""

    monkeypatch.setattr(runner, "_pytest", fake_pytest)

    cand = {"sha": SHA, "parent": PARENT,
            "files": ["tests/test_a.py", "pydantic/main.py"]}
    # The same shape validate_one hands to _measure.
    out = dict(cand)
    out.update({"anchored": True, "pass": 2 if pass2 else 1,
                "before_failed": None})
    return runner._measure("cid", cand, "repo", out, "/work/x", pass2,
                           pass1_f2p=pass1_f2p)


def test_pass2_that_flips_nothing_at_all_is_unstable_not_unchanged(monkeypatch):
    # THE round-3 regression. Pass 1 saw A go fail->pass; pass 2 flips nothing,
    # so pass 2's own f2p is empty and the `rejected:unchanged` early return
    # used to fire before the unstable arm was ever reached. Both are verdicts
    # about the commit, so the discipline held -- but "no test went fail->pass"
    # is false on a record whose f2p_pass1 is non-empty, and the `unstable` row
    # in the funnel counted only the runs that happened to flip something
    # UNRELATED, which made the determinism rejection rate unmeasurable.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.FAILURE},
                   pass1_f2p=[A])
    assert rec["status"] == "rejected:unstable"
    assert rec["f2p"] == []
    assert rec["f2p_pass1"] == [A]
    assert rec["f2p_reproduced"] == []


def test_unstable_keeps_pass2s_raw_set_recoverable_from_the_labels(monkeypatch):
    # `f2p` is blanked so no reader can mistake an unreproduced set for an
    # oracle, which means `failure_labels` is the only remaining trace of what
    # pass 2 did see. It has to be built on this path, not just on the
    # qualifying one.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE, B: outcomes.FAILURE},
                   after={A: outcomes.FAILURE, B: outcomes.PASSED},
                   pass1_f2p=[A],
                   messages={B: "AssertionError: nope"})
    assert rec["status"] == "rejected:unstable"
    assert rec["f2p"] == []
    assert rec["failure_labels"] == {B: "assertion"}


def test_pass1_still_books_unchanged_when_nothing_flips(monkeypatch):
    # Pass 1 carries no oracle and must be completely unaffected by the
    # reordering: for pass 1, "no test went fail->pass" IS the verdict.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.FAILURE},
                   pass1_f2p=None, pass2=False)
    assert rec["status"] == "rejected:unchanged"
    assert rec["reason"].startswith("no test went fail->pass")
    assert "f2p_pass1" not in rec


def test_pass2_reproduced_still_validates_on_the_intersection(monkeypatch):
    other = "tests/test_c.py::test_three"
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE, other: outcomes.FAILURE},
                   after={A: outcomes.PASSED, other: outcomes.PASSED},
                   pass1_f2p=[A],
                   messages={A: "AssertionError: boom", other: "boom"})
    assert rec["status"] == "validated"
    assert rec["f2p"] == [A]
    # The labels are narrowed with the oracle, so report._composition cannot
    # count a label for a node that is not in the capsule.
    assert rec["failure_labels"] == {A: "assertion"}


def test_a_skipped_oracle_node_reaches_the_record_as_apparatus(monkeypatch):
    rec = _measure(monkeypatch,
                   before={A: outcomes.SKIPPED, B: outcomes.FAILURE},
                   after={A: outcomes.SKIPPED, B: outcomes.PASSED},
                   pass1_f2p=[A])
    assert rec["status"] == "apparatus"
    assert rec["f2p"] == []
    assert "skipped" in rec["reason"]


def test_an_unrecognised_check_kind_cannot_reach_validated(monkeypatch):
    # Pass2Check.kind is closed: PASS2_REPRODUCED is the only kind allowed to
    # continue, and it is asserted rather than fallen into. A fifth kind added
    # later must book `error` (our bug, non-terminal), never `validated`.
    monkeypatch.setattr(
        runner, "check_pass2_determinism",
        lambda *a, **k: runner.Pass2Check("brand_new_kind", [], []))
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.PASSED},
                   pass1_f2p=[A])
    assert rec["status"] == "error"
    assert "brand_new_kind" in rec["reason"]


def test_pass2_targets_add_touched_tests_that_live_outside_tests(monkeypatch):
    # Pass 1's oracle can come from any path metrics.is_test_file accepts, and
    # that predicate matches test_*.py anywhere in the tree. Such a node can
    # never appear under the bare "tests" target, so the determinism check
    # would book it never-measured -- apparatus, which is TERMINAL. The union
    # closes that at the source.
    monkeypatch.setattr(
        runner, "_runnable_targets",
        lambda *a, **k: (["tests/test_a.py", "docs/plugins/test_docs.py"],
                         None))
    targets, err = runner._pass2_targets("cid", "/work/x", [])
    assert err is None
    assert targets == ["tests", "docs/plugins/test_docs.py"]


def test_pass2_targets_propagate_a_probe_failure(monkeypatch):
    # Same contract as pass 1: a failed PROBE is not "no extra targets".
    monkeypatch.setattr(runner, "_runnable_targets",
                        lambda *a, **k: (None, "target probe failed (rc=3)"))
    targets, err = runner._pass2_targets("cid", "/work/x", [])
    assert targets is None
    assert "target probe" in err
