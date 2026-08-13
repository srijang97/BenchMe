"""Unit tests for runner._measure, with every container-facing call stubbed.

`_measure` needs Docker, so the pass-2 determinism decision it used to make
inline now lives in `adjudicate.check_pass2_determinism` and is pinned by
miner/tests/test_adjudicate.py (pure: dicts and lists in, a Pass2Check out).
This file tests `_measure` itself -- that the decided kind REACHES the record
through the stub-injected flow, which round 3 proved the pure function alone
cannot guarantee: `PASS2_UNSTABLE` sat below an early return that fired first
on the commonest unstable shape, so the verdict was real and unreachable.
"""
import json
import sys
from collections import namedtuple
from pathlib import Path
from typing import get_type_hints

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import outcomes  # noqa: E402
import adjudicate  # noqa: E402
import runner  # noqa: E402

A = "tests/test_a.py::test_one"
B = "tests/test_b.py::test_two"
C = "tests/test_c.py::test_three"


# --------------------------------------------------------------------------
# _measure: does the decided kind actually reach the record?
# --------------------------------------------------------------------------

SHA = "a" * 40
PARENT = "b" * 40


def _measure(monkeypatch, before, after, pass1_f2p=None, pass2=True,
             messages=None, before_collect=(), after_collect=(),
             collect_messages=None, runnable=None, checkout=None,
             apply_=None):
    """Run `runner._measure` with every container-facing call stubbed.

    Everything replaced here is I/O against Docker or git; the branch structure
    under test is untouched. `before` and `after` are collapsed status maps,
    exactly what `_pytest` returns in production.
    """
    messages = messages or {}
    collect_messages = collect_messages or {}
    if runnable is None:
        runnable = runner.RunnableTargets(["tests/test_a.py"], None, None, None)
    monkeypatch.setattr(runner, "_checkout", lambda *a, **k: checkout)
    monkeypatch.setattr(runner, "_apply", lambda *a, **k: apply_)
    monkeypatch.setattr(runner.validate, "make_patch", lambda *a, **k: "patch")
    monkeypatch.setattr(runner, "_runnable_targets", lambda *a, **k: runnable)
    monkeypatch.setattr(runner, "_pass2_targets",
                        lambda *a, **k: (["tests"], None))

    def fake_pytest(container, workdir, targets, log_path, phase,
                    timeout=300):
        status = before if phase == runner.BEFORE else after
        collect = before_collect if phase == runner.BEFORE else after_collect
        records = [outcomes.Record(n, "call", "failed", messages.get(n))
                   for n, s in status.items() if s == outcomes.FAILURE]
        errors = [n if isinstance(n, outcomes.Record) else outcomes.Record(n, "collect", "failed",
                                  collect_messages.get(n, "ImportError"))
                  for n in collect]
        # Mirrors runner._pytest's merged return contract: records carries
        # both the phase records and the collect records, so _measure forwards
        # the real-shaped collect Records into Measurements.before_records.
        return dict(status), [*records, *errors], errors, ""

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


def test_pass1_before_collection_error_with_oracle_is_not_apparatus(monkeypatch):
    # Row 9: an oracle found despite before collection errors still counts.
    # The aa7705f7 case -- 869 collected, 773 passing, discarded because 2 of
    # 4 touched files failed to import. The runner must now apply the patch
    # and run the after side so rows 9-11 can decide, not short-circuit.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.PASSED},
                   pass1_f2p=None, pass2=False,
                   before_collect=["tests/other.py"],
                   messages={A: "AssertionError: boom"})
    assert rec["status"] == "pass1_ok"
    assert rec["before_collect_errors"] == ["tests/other.py"]
    assert rec["after_collect_errors"] == []


def test_pass1_cleared_collect_error_is_base_import_blocked(monkeypatch):
    # Row 10 through runner: the code patch clears the import, so the block is
    # intrinsic to the commit. Runner must apply the patch and run after side
    # (not short-circuit), so the cleared error is categorised, not buried.
    # The collect record is a real-shaped reporter record, and _pytest must
    # carry it into before_records so import_block_kind can classify it: only
    # the nodeid used to travel, so live row-10 labels were always "other".
    # Direct adjudicate tests pin import_block_kind precisely.
    rec = _measure(monkeypatch,
                   before={}, after={"t.py::a": outcomes.PASSED},
                   pass1_f2p=None, pass2=False,
                   before_collect=["tests/test_f.py"], after_collect=[],
                   collect_messages={"tests/test_f.py":
                                     "ImportError: cannot import name 'NewThing'"})
    assert rec["status"] == "rejected:base_import_blocked"
    assert rec["before_collect_errors"] == ["tests/test_f.py"]
    assert rec["after_collect_errors"] == []
    assert rec["import_block_kind"] == "missing_symbol"


def test_pass1_cleared_warning_collect_error_is_warning_as_error(monkeypatch):
    # The other real row-10 mechanism, through the live runner: a
    # filterwarnings-['error'] project emits a Warning class at import, and
    # the reporter records it as a collect failure with the warning head. A
    # distinct classification branch from missing_symbol (suffix match rather
    # than the exception-name tuple), and cheap to prove end to end -- the
    # merged collect record must reach import_block_kind here too.
    rec = _measure(monkeypatch,
                   before={}, after={"t.py::a": outcomes.PASSED},
                   pass1_f2p=None, pass2=False,
                   before_collect=["tests/test_p.py"], after_collect=[],
                   collect_messages={"tests/test_p.py":
                                     "PydanticExperimentalWarning: This module is experimental"})
    assert rec["status"] == "rejected:base_import_blocked"
    assert rec["import_block_kind"] == "warning_as_error"


def test_pass1_persistent_collect_error_is_apparatus(monkeypatch):
    # Row 11 through runner: before and after share the same collect error,
    # nothing cleared, so the cause lives outside the commit.
    rec = _measure(monkeypatch,
                   before={}, after={"t.py::a": outcomes.PASSED},
                   pass1_f2p=None, pass2=False,
                   before_collect=["tests/test_f.py"], after_collect=["tests/test_f.py"])
    assert rec["status"] == "apparatus"
    assert rec["before_collect_errors"] == ["tests/test_f.py"]
    assert rec["after_collect_errors"] == ["tests/test_f.py"]


def test_pass1_empty_before_true_short_circuit_has_no_after(monkeypatch):
    # True short-circuit: empty before with NO collect errors. No patch, no after.
    rec = _measure(monkeypatch,
                   before={}, after={"t.py::a": outcomes.PASSED},
                   pass1_f2p=None, pass2=False,
                   before_collect=[])
    assert rec["status"] == "apparatus"
    assert "before side" in rec["reason"]
    # Even the true short-circuit now carries empty collect fields on every path (Task 2).
    assert rec["before_collect_errors"] == []
    assert rec["after_collect_errors"] == []


def test_pass1_with_no_collection_errors_is_untouched(monkeypatch):
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.PASSED},
                   pass1_f2p=None, pass2=False,
                   messages={A: "AssertionError: boom"})
    assert rec["status"] == "pass1_ok"
    assert rec["before_collect_errors"] == []


def test_pass2_before_collection_errors_do_not_book_apparatus(monkeypatch):
    # DELIBERATELY NOT pass 2. The full suite in an anchored image carries
    # endemic collection errors from dependency drift that have nothing to do
    # with the candidate; a blanket rule there would terminally retire nearly
    # every candidate. Pass 2 still has its own guards -- `new_collect` for
    # errors new to the after side, and the determinism check for oracle nodes
    # the run did not measure.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.PASSED},
                   pass1_f2p=[A],
                   messages={A: "AssertionError: boom"},
                   before_collect=["tests/unrelated.py"],
                   after_collect=["tests/unrelated.py"])
    assert rec["status"] == "validated"
    assert rec["f2p"] == [A]


def test_an_unrecognised_check_kind_cannot_reach_validated(monkeypatch):
    # Pass2Check.kind is closed: PASS2_REPRODUCED is the only kind allowed to
    # continue, and it is asserted rather than fallen into. A fifth kind added
    # later must book `error` (our bug, non-terminal), never `validated`.
    # The check moved to adjudicate.py with the extraction, so the injection
    # point is adjudicate.check_pass2_determinism -- what _measure now calls
    # through adjudicate.adjudicate.
    monkeypatch.setattr(
        adjudicate, "check_pass2_determinism",
        lambda *a, **k: adjudicate.Pass2Check("brand_new_kind", [], []))
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
        lambda *a, **k: runner.RunnableTargets(
            ["tests/test_a.py", "docs/plugins/test_docs.py"], None, None, None))
    targets, err = runner._pass2_targets("cid", "/work/x", [])
    assert err is None
    assert targets == ["tests", "docs/plugins/test_docs.py"]


def test_pass2_targets_propagate_a_probe_failure(monkeypatch):
    # Same contract as pass 1: a failed PROBE is not "no extra targets".
    monkeypatch.setattr(
        runner, "_runnable_targets",
        lambda *a, **k: runner.RunnableTargets(
            None, "target probe failed (rc=3)", None, None))
    targets, err = runner._pass2_targets("cid", "/work/x", [])
    assert targets is None
    assert "target probe" in err


def test_pass2_regression_broken_reaches_the_record(monkeypatch):
    # THE MISSING PIN. `rejected:regression_broken` sits at the very bottom of
    # the reordered pass-2 decision block, below the determinism arms, below
    # the collection-error guard and below the `rejected:unchanged` return.
    # Nothing else in this file proves it is still reachable, so any future
    # arm inserted above it could shadow the only verdict the corpus has
    # against a fix that breaks something else.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE, C: outcomes.PASSED},
                   after={A: outcomes.PASSED, C: outcomes.FAILURE},
                   pass1_f2p=[A],
                   messages={A: "AssertionError: boom"})
    assert rec["status"] == "rejected:regression_broken"
    # Not shadowed by an earlier arm: the oracle really did reproduce, so the
    # record must NOT be apparatus, unstable, unchanged or error.
    assert rec["f2p_pass1"] == [A]
    assert rec["f2p_reproduced"] == [A]
    assert rec["broken"] == [C]
    # Finding 4b: the reason counts genuine failures and vanished ids apart.
    assert "1 previously-passing test(s) fail" in rec["reason"]
    assert rec["vanished"] == []
    # Vanished count is only mentioned when non-zero, so a reader cannot
    # mistake an absent mention for a dropped count.
    assert "vanished" not in rec["reason"]


def test_a_vanished_node_is_not_a_failure(monkeypatch):
    # C passed before and is ABSENT after -- no exact-swap rename to excuse it,
    # so it is `vanished`. It did not FAIL: it was never run on the after side,
    # so booking a regression off it would claim failures that never happened.
    # A vanished id alone must not yield `rejected:regression_broken`; the
    # oracle reproduced, so the verdict is validated and the vanished id stays
    # on the record.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE, C: outcomes.PASSED},
                   after={A: outcomes.PASSED},
                   pass1_f2p=[A])
    assert rec["status"] == "validated"
    assert rec["vanished"] == [C]
    assert rec["broken"] == []


def test_a_collection_error_new_to_the_after_side_is_apparatus(monkeypatch):
    # --continue-on-collection-errors means a file that stops importing after
    # the code patch does not FAIL -- its tests cease to exist. They vanish,
    # miss the rename rule, land in `broken`, and would book
    # `rejected:regression_broken` claiming tests "fail" that never ran. The
    # two sides were not measured comparably, so no verdict is honest.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE, C: outcomes.PASSED},
                   after={A: outcomes.PASSED},
                   pass1_f2p=[A],
                   after_collect=["tests/test_c.py"])
    assert rec["status"] == "apparatus"
    assert "not measured comparably" in rec["reason"]
    assert "tests/test_c.py" in rec["reason"]


def test_a_collection_error_on_both_sides_is_not_apparatus(monkeypatch):
    # A constant of the environment removes the same nodes from both maps, so
    # the comparison stays symmetric. Booking apparatus on it would retire
    # every candidate in a suite with one permanently-broken import.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.PASSED},
                   pass1_f2p=[A],
                   before_collect=["tests/test_c.py"],
                   after_collect=["tests/test_c.py"])
    assert rec["status"] == "validated"


def test_a_collection_error_only_before_does_not_book_apparatus(monkeypatch):
    # Only errors NEW to the after side are the asymmetry that invalidates the
    # comparison. A before-only collection error means the after side saw MORE
    # tests, which cannot manufacture a false regression.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE},
                   after={A: outcomes.PASSED},
                   pass1_f2p=[A],
                   before_collect=["tests/test_c.py"])
    assert rec["status"] == "validated"


# --------------------------------------------------------------------------
# Findings 2 and 3: our failures must not be booked as verdicts, and a
# transient one must not be booked as a terminal one.
# --------------------------------------------------------------------------

def test_a_failed_checkout_is_error_not_apparatus(monkeypatch):
    # apparatus is TERMINAL. A clone or checkout that failed is transient
    # infrastructure -- the same class of event as the ContainerLost timeout,
    # which validate_quarter books `error` precisely so a possibly-valid
    # candidate is not retired by a hiccup.
    rec = _measure(monkeypatch, before={}, after={}, pass2=False,
                   checkout=runner.Failure("error", "clone failed: disk full"))
    assert rec["status"] == "error"
    assert "clone failed" in rec["reason"]


def test_a_patch_write_failure_is_error_and_a_bad_patch_is_apparatus(
        monkeypatch):
    # The two halves of _apply are different kinds of failure and must stay
    # different kinds of record.
    rec = _measure(monkeypatch, before={}, after={}, pass2=False,
                   apply_=runner.Failure("error",
                                         "could not write test patch into the "
                                         "container (rc=1): broken pipe"))
    assert rec["status"] == "error"
    rec = _measure(monkeypatch, before={}, after={}, pass2=False,
                   apply_=runner.Failure("apparatus",
                                         "test patch would not apply: ..."))
    assert rec["status"] == "apparatus"


def test_our_own_path_filter_is_apparatus_not_a_verdict(monkeypatch):
    # Task 4: EMPTY_FILTERED is now not_minable:no_pytest_tests (a property of
    # the commit under our NON_PYTEST_TEST_DIRS policy), not apparatus. The old
    # rejected:unchanged records for dac3c437/568509c0 were the defect this
    # retires. Kept name as transition pin; see adjudicate 1e2e919.
    rec = _measure(
        monkeypatch, before={}, after={}, pass2=False,
        runnable=runner.RunnableTargets(
            [], None, runner.EMPTY_FILTERED,
            "every touched test path was dropped by OUR "
            "candidates.NON_PYTEST_TEST_DIRS filter: tests/typechecking/x.py"))
    assert rec["status"] == "not_minable:no_pytest_tests"
    assert "tests/typechecking/x.py" in rec["reason"]


def test_nothing_runnable_among_admitted_paths_is_apparatus(monkeypatch):
    # validate._belongs_to_test_side admits a JSON fixture and a conftest.py,
    # neither of which pytest can be pointed at. That is our path handling,
    # not a property of the commit.
    rec = _measure(
        monkeypatch, before={}, after={}, pass2=False,
        runnable=runner.RunnableTargets(
            [], None, runner.EMPTY_NOT_RUNNABLE, "conftest.py, tests/f.json"))
    assert rec["status"] == "apparatus"


def test_an_unexplained_absence_is_apparatus(monkeypatch):
    rec = _measure(
        monkeypatch, before={}, after={}, pass2=False,
        runnable=runner.RunnableTargets(
            [], None, runner.EMPTY_ABSENT, "tests/test_a.py"))
    assert rec["status"] == "apparatus"


def test_an_unrecognised_empty_reason_falls_to_apparatus(monkeypatch):
    # Membership, not inequality: a cause added later must not default into a
    # verdict about the commit.
    rec = _measure(
        monkeypatch, before={}, after={}, pass2=False,
        runnable=runner.RunnableTargets([], None, "brand_new_cause", "x"))
    assert rec["status"] == "apparatus"
    assert "brand_new_cause" in rec["reason"]


def test_a_commit_that_deleted_its_tests_is_the_only_unchanged_verdict(
        monkeypatch):
    # Task 4: EMPTY_DELETED is now rejected:no_runnable_tests (the one filter-
    # empty cause that is a verdict about the commit), distinct from generic
    # rejected:unchanged. Kept name as transition pin; see adjudicate 1e2e919.
    rec = _measure(
        monkeypatch, before={}, after={}, pass2=False,
        runnable=runner.RunnableTargets(
            [], None, runner.EMPTY_DELETED,
            "the commit deletes every test file it touches: tests/test_a.py"))
    assert rec["status"] == "rejected:no_runnable_tests"
    assert "deletes every test file" in rec["reason"]


# --------------------------------------------------------------------------
# Finding 3, at the source: _runnable_targets classifies its own empty result.
# --------------------------------------------------------------------------

_Proc = namedtuple("Proc", "returncode stdout stderr")


def _probe(monkeypatch, stdout, returncode=0):
    monkeypatch.setattr(runner.quarters, "exec_in",
                        lambda *a, **k: _Proc(returncode, stdout, ""))


def test_runnable_targets_reports_present_paths(monkeypatch):
    _probe(monkeypatch, "present tests/test_a.py\nabsent tests/test_b.py\n")
    found = runner._runnable_targets(
        "cid", "/work/x", ["tests/test_a.py", "tests/test_b.py"])
    assert found.paths == ["tests/test_a.py"]
    assert found.why is None and found.err is None


def test_runnable_targets_names_the_filter_that_emptied_it(monkeypatch):
    # tests/typechecking/ is in candidates.NON_PYTEST_TEST_DIRS for pydantic,
    # which is record.REPO.name. No probe should even run.
    found = runner._runnable_targets(
        "cid", "/work/x", ["tests/typechecking/test_x.py"])
    assert found.paths == []
    assert found.why == runner.EMPTY_FILTERED
    assert "tests/typechecking/test_x.py" in found.detail


def test_runnable_targets_flags_fixture_and_conftest_only_paths(monkeypatch):
    found = runner._runnable_targets(
        "cid", "/work/x", ["tests/conftest.py", "tests/data/case.json"])
    assert found.paths == []
    assert found.why == runner.EMPTY_NOT_RUNNABLE


def test_runnable_targets_calls_a_deleted_test_file_deleted(monkeypatch):
    # In HEAD (the parent) and gone from the worktree: the commit's own test
    # patch deleted it. The ONE cause that is a verdict about the commit.
    _probe(monkeypatch, "deleted tests/test_a.py\n")
    found = runner._runnable_targets("cid", "/work/x", ["tests/test_a.py"])
    assert found.why == runner.EMPTY_DELETED


def test_runnable_targets_calls_an_unexplained_absence_absent(monkeypatch):
    # Not in HEAD and not on disk: our picture of the tree is wrong. Ambiguity
    # resolves toward apparatus, so `absent` outranks `deleted` in a mix.
    _probe(monkeypatch, "absent tests/test_a.py\ndeleted tests/test_b.py\n")
    found = runner._runnable_targets(
        "cid", "/work/x", ["tests/test_a.py", "tests/test_b.py"])
    assert found.why == runner.EMPTY_ABSENT
    assert "tests/test_a.py" in found.detail


def test_runnable_targets_still_reports_a_failed_probe(monkeypatch):
    # The existing error channel is unchanged: a failed PROBE is not an empty
    # result, and must never be adjudicated as one.
    _probe(monkeypatch, "", returncode=3)
    found = runner._runnable_targets("cid", "/work/x", ["tests/test_a.py"])
    assert found.paths is None
    assert "target probe failed" in found.err
    assert found.why is None


# --------------------------------------------------------------------------
# Finding 1: a crashed session writes the terminator too.
# --------------------------------------------------------------------------

def _exec_for_pytest(monkeypatch, report_text, pytest_rc=1):
    def exec_in(container, argv, timeout=300):
        if argv[0] == "cat":
            return _Proc(0, report_text, "")
        return _Proc(pytest_rc, "pytest output", "")
    monkeypatch.setattr(runner.quarters, "exec_in", exec_in)


def _report(exitstatus):
    lines = [json.dumps({"kind": "test", "nodeid": A, "when": "call",
                         "outcome": "failed", "message": "assert 0"})]
    finish = {"kind": "sessionfinish"}
    if exitstatus is not None:
        finish["exitstatus"] = exitstatus
    lines.append(json.dumps(finish))
    return "\n".join(lines) + "\n"


def test_pytest_accepts_the_three_conclusive_exit_statuses(monkeypatch,
                                                           tmp_path):
    for status in (0, 1, 5):
        _exec_for_pytest(monkeypatch, _report(status))
        collapsed, records, collect, _out = runner._pytest(
            "cid", "/work/x", ["tests"], tmp_path / "before.log", "before")
        assert collapsed == {A: outcomes.FAILURE}, status
        assert [r.nodeid for r in records] == [A]
        assert collect == []


def test_pytest_merges_collect_records_into_records(monkeypatch, tmp_path):
    # The wiring fix at the source: `_pytest` returns both report channels,
    # and `records` (what becomes Measurements.before_records) must carry the
    # real-shaped collect Records so adjudicate.import_block_kind can classify
    # a cleared row-10 block. Only the nodeids used to travel, which is why
    # live row-10 labels were always "other".
    lines = [
        json.dumps({"kind": "test", "nodeid": A, "when": "call",
                    "outcome": "failed", "message": "assert 0"}),
        json.dumps({"kind": "collect", "nodeid": "tests/test_f.py",
                    "when": "collect", "outcome": "failed",
                    "message": "ImportError: cannot import name 'NewThing'"}),
        json.dumps({"kind": "sessionfinish", "exitstatus": 1}),
    ]
    _exec_for_pytest(monkeypatch, "\n".join(lines) + "\n")
    collapsed, records, collect, _out = runner._pytest(
        "cid", "/work/x", ["tests"], tmp_path / "before.log", "before")
    assert collapsed == {A: outcomes.FAILURE}
    assert [r.when for r in records] == ["call", "collect"]
    assert [r.nodeid for r in collect] == ["tests/test_f.py"]


def test_pytest_rejects_a_session_that_did_not_complete(monkeypatch, tmp_path):
    # 2 interrupted, 3 internal error, 4 usage error -- and a terminator with
    # no status at all. Each one wrote a WELL-FORMED, TERMINATED report holding
    # a partial measurement; parsing alone cannot tell it from a short run, and
    # pass 1 would book `rejected:unchanged` -- a terminal verdict about the
    # commit caused by our crash. The caller turns this ValueError into
    # apparatus.
    for status in (2, 3, 4, None):
        _exec_for_pytest(monkeypatch, _report(status))
        try:
            runner._pytest("cid", "/work/x", ["tests"],
                           tmp_path / "before.log", "before")
        except ValueError as exc:
            assert "exit status" in str(exc), status
            continue
        raise AssertionError(f"expected ValueError for exit status {status}")


def test_a_crashed_before_session_books_apparatus(monkeypatch, tmp_path):
    # End to end through the real _pytest: the record must say apparatus, not
    # rejected:unchanged.
    monkeypatch.setattr(runner, "_checkout", lambda *a, **k: None)
    monkeypatch.setattr(runner, "_apply", lambda *a, **k: None)
    monkeypatch.setattr(runner.validate, "make_patch", lambda *a, **k: "patch")
    monkeypatch.setattr(
        runner, "_runnable_targets",
        lambda *a, **k: runner.RunnableTargets(["tests/test_a.py"], None,
                                               None, None))
    monkeypatch.setattr(runner.record, "LOGS", tmp_path)
    _exec_for_pytest(monkeypatch, _report(3))
    cand = {"sha": SHA, "parent": PARENT,
            "files": ["tests/test_a.py", "pydantic/main.py"]}
    out = dict(cand, anchored=True, **{"pass": 1, "before_failed": None})
    rec = runner._measure("cid", cand, "repo", out, "/work/x", False)
    assert rec["status"] == "apparatus"
    assert "before report" in rec["reason"]


# --------------------------------------------------------------------------
# Task 4b: not_minable candidates are recorded before any Docker work.
# --------------------------------------------------------------------------

def test_validate_quarter_all_not_minable_short_circuits_before_docker(monkeypatch, tmp_path):
    cand1 = {"sha": "a" * 40, "parent": "b" * 40, "quarter": "2025Q3",
             "files": ["pydantic/main.py"], "not_minable": "foreign_project"}
    cand2 = {"sha": "c" * 40, "parent": "d" * 40, "quarter": "2025Q3",
             "files": ["pydantic/main.py"], "not_minable": "straddles_dependency_bump"}
    candidates_path = tmp_path / "candidates.jsonl"
    validated_path = tmp_path / "validated.jsonl"
    candidates_path.write_text(
        "\n".join(json.dumps(c) for c in [cand1, cand2]) + "\n", encoding="utf-8")
    monkeypatch.setattr(runner.record, "CANDIDATES", candidates_path)
    monkeypatch.setattr(runner.record, "VALIDATED", validated_path)
    monkeypatch.setattr(runner.record, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner.record, "REPO", tmp_path / "repo")
    monkeypatch.setattr(runner.quarters, "preflight", lambda: None)

    def fail_build(*a, **k):
        raise AssertionError("build_quarter_image must not be called when all queue entries are not_minable")
    monkeypatch.setattr(runner.quarters, "build_quarter_image", fail_build)
    monkeypatch.setattr(runner.quarters, "start_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_container must not be called")))
    monkeypatch.setattr(runner.quarters, "install_reporter",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("install_reporter must not be called")))
    monkeypatch.setattr(runner.quarters, "stop_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("stop_container must not be called")))
    monkeypatch.setattr(runner.quarters, "remove_image",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("remove_image must not be called")))
    monkeypatch.setattr(runner, "validate_one",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("validate_one must not be called")))

    counts = runner.validate_quarter("2025Q3", limit=10, keep_images=False, force=False)

    assert counts == {"not_minable:foreign_project": 1, "not_minable:straddles_dependency_bump": 1}
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2
    recs = {json.loads(l)["sha"]: json.loads(l) for l in lines}
    for cand in [cand1, cand2]:
        rec = recs[cand["sha"]]
        assert rec["status"] == f"not_minable:{cand['not_minable']}"
        assert rec["before_failed"] is None
        assert cand["not_minable"] in rec["reason"]
        assert rec["quarter"] == cand["quarter"]
        assert rec["files"] == cand["files"]
        # preserves candidate fields
        assert rec["not_minable"] == cand["not_minable"]
        # Semantic: never entered Docker, so anchored is unknown (None), not False.
        # False means "an image ran without the frozen anchor"; None means no image ran.
        assert rec["anchored"] is None
        assert rec["anchor"] is None


def test_validate_quarter_no_pytest_tests_is_stamped_before_docker(monkeypatch, tmp_path):
    """A candidate whose touched tests are exclusively in NON_PYTEST_TEST_DIRS
    (stamped no_pytest_tests at stage 1 enumeration) must be recorded pre-Docker:
    no image build, no container, no validate_one -- and anchored stays None
    (no image ever ran), never False."""
    cand = {"sha": "e" * 40, "parent": "f" * 40, "quarter": "2025Q4",
            "files": ["tests/typechecking/fields.py", "pydantic/main.py"],
            "test_files": ["tests/typechecking/fields.py"],
            "not_minable": "no_pytest_tests"}
    candidates_path = tmp_path / "candidates.jsonl"
    validated_path = tmp_path / "validated.jsonl"
    candidates_path.write_text(json.dumps(cand) + "\n", encoding="utf-8")
    monkeypatch.setattr(runner.record, "CANDIDATES", candidates_path)
    monkeypatch.setattr(runner.record, "VALIDATED", validated_path)
    monkeypatch.setattr(runner.record, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner.record, "REPO", tmp_path / "repo")
    monkeypatch.setattr(runner.quarters, "preflight", lambda: None)
    monkeypatch.setattr(runner.quarters, "build_quarter_image",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("build_quarter_image must not be called "
                                           "for a no_pytest_tests candidate")))
    monkeypatch.setattr(runner.quarters, "start_container",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("start_container must not be called")))
    monkeypatch.setattr(runner.quarters, "install_reporter",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("install_reporter must not be called")))
    monkeypatch.setattr(runner.quarters, "stop_container",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("stop_container must not be called")))
    monkeypatch.setattr(runner.quarters, "remove_image",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("remove_image must not be called")))
    monkeypatch.setattr(runner, "validate_one",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("validate_one must not be called")))

    counts = runner.validate_quarter("2025Q4", limit=10, keep_images=False, force=False)

    assert counts == {"not_minable:no_pytest_tests": 1}
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["sha"] == cand["sha"]
    assert rec["status"] == "not_minable:no_pytest_tests"
    assert rec["before_failed"] is None
    assert "no_pytest_tests" in rec["reason"]
    assert rec["not_minable"] == "no_pytest_tests"
    assert rec["quarter"] == "2025Q4"
    assert rec["files"] == cand["files"]
    assert rec["anchored"] is None
    assert rec["anchor"] is None


def test_validate_quarter_mixed_queue_only_not_minable_before_docker(monkeypatch, tmp_path):
    cand_bad = {"sha": "a" * 40, "parent": "b" * 40, "quarter": "2025Q3",
                "files": ["pydantic/main.py"], "not_minable": "foreign_project"}
    cand_ok = {"sha": "c" * 40, "parent": "d" * 40, "quarter": "2025Q3",
               "files": ["tests/test_a.py", "pydantic/main.py"]}
    candidates_path = tmp_path / "candidates.jsonl"
    validated_path = tmp_path / "validated.jsonl"
    candidates_path.write_text(
        "\n".join(json.dumps(c) for c in [cand_bad, cand_ok]) + "\n", encoding="utf-8")
    monkeypatch.setattr(runner.record, "CANDIDATES", candidates_path)
    monkeypatch.setattr(runner.record, "VALIDATED", validated_path)
    monkeypatch.setattr(runner.record, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner.record, "REPO", tmp_path / "repo")
    monkeypatch.setattr(runner.quarters, "preflight", lambda: None)

    Img = namedtuple("Img", "tag anchored anchor skip reason")
    fake_img = Img(tag="benchme:2025q3", anchored=True, anchor="abc", skip=False, reason="")
    calls = {"build": 0, "start": 0, "install": 0, "validate_one": [], "stop": 0, "remove": 0}

    def fake_build(*a, **k):
        calls["build"] += 1
        return fake_img
    monkeypatch.setattr(runner.quarters, "build_quarter_image", fake_build)
    monkeypatch.setattr(runner.quarters, "start_container", lambda *a, **k: (calls.__setitem__("start", calls["start"] + 1), "cid123")[1])
    monkeypatch.setattr(runner.quarters, "install_reporter", lambda *a, **k: (calls.__setitem__("install", calls["install"] + 1), None)[1])
    monkeypatch.setattr(runner.quarters, "stop_container", lambda *a, **k: calls.__setitem__("stop", calls["stop"] + 1))
    monkeypatch.setattr(runner.quarters, "remove_image", lambda *a, **k: calls.__setitem__("remove", calls["remove"] + 1))

    def fake_validate_one(cid, cand, repo, anchored, pass2=False, pass1_f2p=None):
        calls["validate_one"].append(cand["sha"])
        out = dict(cand)
        out["anchored"] = anchored
        out["pass"] = 2 if pass2 else 1
        out["before_failed"] = 1
        out["status"] = "pass1_ok"
        out["reason"] = None
        out["f2p"] = ["tests/test_a.py::test_one"]
        return out
    monkeypatch.setattr(runner, "validate_one", fake_validate_one)

    counts = runner.validate_quarter("2025Q3", limit=10, keep_images=False, force=False)

    # not_minable was recorded, Docker was still used for the good candidate
    assert calls["build"] == 1
    assert calls["start"] == 1
    assert calls["install"] == 1
    assert cand_bad["sha"] not in calls["validate_one"]
    assert cand_ok["sha"] in calls["validate_one"]
    assert counts.get("not_minable:foreign_project") == 1
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    recs = {json.loads(l)["sha"]: json.loads(l) for l in lines}
    assert recs[cand_bad["sha"]]["status"] == "not_minable:foreign_project"
    assert recs[cand_bad["sha"]]["before_failed"] is None
    assert "foreign_project" in recs[cand_bad["sha"]]["reason"]
    assert recs[cand_bad["sha"]]["anchored"] is None
    assert recs[cand_bad["sha"]]["anchor"] is None
    # good candidate was also recorded (via fake_validate_one)
    assert cand_ok["sha"] in recs


# --------------------------------------------------------------------------
# Post-review queue/force and image-skip contracts (TDD RED -> production fix)
# --------------------------------------------------------------------------

def _write_candidates(path, cands):
    path.write_text("\n".join(json.dumps(c) for c in cands) + "\n", encoding="utf-8")


def test_validate_quarter_limit_counts_not_minable_before_docker(monkeypatch, tmp_path):
    """A 1-entry limit where the selected entry is not_minable must not trigger Docker."""
    cand_bad = {"sha": "a" * 40, "parent": "b" * 40, "quarter": "2025Q3",
                "files": ["pydantic/main.py"], "not_minable": "foreign_project"}
    cand_ok = {"sha": "c" * 40, "parent": "d" * 40, "quarter": "2025Q3",
               "files": ["tests/test_a.py", "pydantic/main.py"]}
    candidates_path = tmp_path / "candidates.jsonl"
    validated_path = tmp_path / "validated.jsonl"
    _write_candidates(candidates_path, [cand_bad, cand_ok])
    monkeypatch.setattr(runner.record, "CANDIDATES", candidates_path)
    monkeypatch.setattr(runner.record, "VALIDATED", validated_path)
    monkeypatch.setattr(runner.record, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner.record, "REPO", tmp_path / "repo")
    monkeypatch.setattr(runner.quarters, "preflight", lambda: None)
    monkeypatch.setattr(runner.quarters, "build_quarter_image",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("build must not be called when queue limited to not_minable")))
    monkeypatch.setattr(runner.quarters, "start_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_container must not be called")))
    monkeypatch.setattr(runner.quarters, "install_reporter",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("install_reporter must not be called")))
    monkeypatch.setattr(runner.quarters, "stop_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("stop_container must not be called")))
    monkeypatch.setattr(runner.quarters, "remove_image",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("remove_image must not be called")))
    monkeypatch.setattr(runner, "validate_one",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("validate_one must not be called")))
    counts = runner.validate_quarter("2025Q3", limit=1, keep_images=False, force=False)
    assert counts == {"not_minable:foreign_project": 1}
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["sha"] == cand_bad["sha"]
    assert rec["anchored"] is None
    assert rec["anchor"] is None


def test_validate_quarter_not_minable_retry_is_terminal(monkeypatch, tmp_path):
    """not_minable is terminal: force=False does not retry; force=True appends."""
    cand = {"sha": "a" * 40, "parent": "b" * 40, "quarter": "2025Q3",
            "files": ["pydantic/main.py"], "not_minable": "foreign_project"}
    candidates_path = tmp_path / "candidates.jsonl"
    validated_path = tmp_path / "validated.jsonl"
    _write_candidates(candidates_path, [cand])
    monkeypatch.setattr(runner.record, "CANDIDATES", candidates_path)
    monkeypatch.setattr(runner.record, "VALIDATED", validated_path)
    monkeypatch.setattr(runner.record, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner.record, "REPO", tmp_path / "repo")
    monkeypatch.setattr(runner.quarters, "preflight", lambda: None)
    # First run: writes one terminal not_minable record before Docker.
    monkeypatch.setattr(runner.quarters, "build_quarter_image",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("build must not be called when queue is only not_minable")))
    monkeypatch.setattr(runner.quarters, "start_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_container must not be called")))
    counts1 = runner.validate_quarter("2025Q3", limit=10, keep_images=False, force=False)
    assert counts1 == {"not_minable:foreign_project": 1}
    lines1 = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines1) == 1
    assert json.loads(lines1[0])["anchored"] is None
    # Second run force=False: no Docker, no write (already done, terminal).
    monkeypatch.setattr(runner.quarters, "build_quarter_image",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("build must not be called on retry with force=False")))
    monkeypatch.setattr(runner.quarters, "start_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_container must not be called on retry with force=False")))
    counts2 = runner.validate_quarter("2025Q3", limit=10, keep_images=False, force=False)
    assert counts2 == {}
    lines2 = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines2) == 1
    # Third run force=True: appends one further terminal record (append-only).
    monkeypatch.setattr(runner.quarters, "build_quarter_image",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("build must not be called when queue is only not_minable")))
    monkeypatch.setattr(runner.quarters, "start_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_container must not be called")))
    counts3 = runner.validate_quarter("2025Q3", limit=10, keep_images=False, force=True)
    assert counts3 == {"not_minable:foreign_project": 1}
    lines3 = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines3) == 2
    assert all(json.loads(l)["anchored"] is None for l in lines3)
    assert all(json.loads(l)["anchor"] is None for l in lines3)


def test_validate_quarter_image_skip_preserves_not_minable(monkeypatch, tmp_path):
    """Mixed queue: not_minable recorded before Docker; skip image returns counts unchanged and never starts a container."""
    cand_bad = {"sha": "a" * 40, "parent": "b" * 40, "quarter": "2025Q3",
                "files": ["pydantic/main.py"], "not_minable": "foreign_project"}
    cand_ok = {"sha": "c" * 40, "parent": "d" * 40, "quarter": "2025Q3",
               "files": ["tests/test_a.py", "pydantic/main.py"]}
    candidates_path = tmp_path / "candidates.jsonl"
    validated_path = tmp_path / "validated.jsonl"
    _write_candidates(candidates_path, [cand_bad, cand_ok])
    monkeypatch.setattr(runner.record, "CANDIDATES", candidates_path)
    monkeypatch.setattr(runner.record, "VALIDATED", validated_path)
    monkeypatch.setattr(runner.record, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner.record, "REPO", tmp_path / "repo")
    monkeypatch.setattr(runner.quarters, "preflight", lambda: None)
    Img = namedtuple("Img", "tag anchored anchor skip reason")
    skip_img = Img(tag=None, anchored=None, anchor=None, skip=True, reason="nothing to mine")
    monkeypatch.setattr(runner.quarters, "build_quarter_image", lambda *a, **k: skip_img)
    monkeypatch.setattr(runner.quarters, "start_container",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("start_container must not be called when image is skipped")))
    monkeypatch.setattr(runner.quarters, "install_reporter",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("install_reporter must not be called when image is skipped")))
    monkeypatch.setattr(runner, "validate_one",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("validate_one must not be called when image is skipped")))
    counts = runner.validate_quarter("2025Q3", limit=10, keep_images=False, force=False)
    assert counts == {"not_minable:foreign_project": 1}
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["sha"] == cand_bad["sha"]
    assert rec["anchored"] is None
    assert rec["anchor"] is None



# --------------------------------------------------------------------------
# Task 1: locked environment profile detection
# --------------------------------------------------------------------------

def test_detect_profile_selects_uv_and_pdm(tmp_path):
    uv_dir = tmp_path / "uv_anchor"
    uv_dir.mkdir()
    (uv_dir / "uv.lock").write_text("", encoding="utf-8")
    prof = runner.quarters.detect_profile(uv_dir)
    assert prof is not None
    assert prof.name == "uv_locked"
    assert prof.lockfile == "uv.lock"

    pdm_dir = tmp_path / "pdm_anchor"
    pdm_dir.mkdir()
    (pdm_dir / "pdm.lock").write_text("", encoding="utf-8")
    prof = runner.quarters.detect_profile(pdm_dir)
    assert prof is not None
    assert prof.name == "pdm_locked"
    assert prof.lockfile == "pdm.lock"


def test_detect_profile_returns_none_for_missing_or_ambiguous_lockfiles(tmp_path):
    empty_dir = tmp_path / "empty_anchor"
    empty_dir.mkdir()
    assert runner.quarters.detect_profile(empty_dir) is None

    ambig_dir = tmp_path / "ambig_anchor"
    ambig_dir.mkdir()
    (ambig_dir / "uv.lock").write_text("", encoding="utf-8")
    (ambig_dir / "pdm.lock").write_text("", encoding="utf-8")
    assert runner.quarters.detect_profile(ambig_dir) is None


def test_quarter_image_includes_profile_metadata():
    image = runner.quarters.QuarterImage(
        "benchme-miner/pydantic:2026q3", "ok", "a" * 40, True, False,
        "pdm_locked")
    assert image.profile == "pdm_locked"


def test_dockerfile_template_includes_profile_probes_and_profile_file():
    profile = runner.quarters.PDM_PROFILE
    rendered = runner.quarters.DOCKERFILE.format(
        base="python:3.12-slim",
        tool_install=profile.tool_install,
        export=profile.export_frozen,
        export_min=profile.export_frozen_min,
        fallback=profile.export_unfrozen,
        fallback_min=profile.export_unfrozen_min,
        mode_frozen=runner.quarters.MODE_FROZEN,
        mode_unfrozen=runner.quarters.MODE_UNFROZEN,
        mode_path=runner.quarters.EXPORT_MODE_PATH,
        profile_name=profile.name,
        profile_path=runner.quarters.PROFILE_PATH,
        profile_probes=runner.quarters._profile_probes_cmd(profile),
        user="1000:1000",
        wheels_download="")

    assert "RUN pip install --no-cache-dir uv pdm" in rendered
    assert "pdm export -g testing -g testing-extra --no-self" in rendered
    assert (
        "echo pdm_locked > /opt/miner/environment-profile" in rendered
    )
    assert "import dirty_equals; import pytest_examples" in rendered
    assert rendered.index("RUN rm -rf /src") < rendered.index(
        "import dirty_equals; import pytest_examples")


def test_profile_probes_cmd_has_explicit_type_contract():
    assert get_type_hints(runner.quarters._profile_probes_cmd) == {
        "profile": runner.quarters.EnvironmentProfile,
        "return": str,
    }


# --------------------------------------------------------------------------
# Task 2: wheel caching and pin alignment tests
# --------------------------------------------------------------------------

def test_align_core_pin_uses_exec_in_and_offline_install(monkeypatch):
    """The alignment step is a container-facing exec, so it must go through
    quarters.exec_in -- the single choke point that turns a timeout into
    ContainerLost (and hence `error`, non-terminal) instead of hanging the
    one-container-at-a-time slot. It must also target `sh`, not `bash`:
    python:3.12-slim ships only sh. And the install must be offline
    (--no-index --find-links /opt/miner/wheels) so the fix is the build-time
    cache, never a fresh resolve against a network the container does not
    have (--network none)."""
    calls = []

    def fake_exec_in(container, argv, timeout=300):
        calls.append((container, argv, timeout))
        return _Proc(0, "", "")

    monkeypatch.setattr(runner.quarters, "exec_in", fake_exec_in)
    result = runner._align_core_pin("cid123", "/work/x", "2.47.0")
    assert result is None
    assert len(calls) == 1
    cid, argv, timeout = calls[0]
    assert cid == "cid123"
    assert argv[0] == "sh"
    assert argv[1] == "-c"
    cmd = argv[2]
    # Idempotent offline install of the candidate's exact pin into the fixed
    # user-writable ALIGN_CORE_DIR (site-packages is root-owned under uid
    # 1000); `_pytest` prepends that dir to its own PYTHONPATH. No version
    # probe: nested quoting under sh -c / docker exec corrupts the string
    # literal on this host.
    assert "uv pip install --system --target /work/aligned-core --no-index --find-links /opt/miner/wheels" in cmd
    assert "pydantic-core==2.47.0" in cmd


def test_align_core_pin_failure_books_error_not_apparatus(monkeypatch):
    """A pin that differs and cannot be installed from the cache is OUR gap
    (a stale candidates file, a wheel the build did not cache), not a fact
    about the commit. `error` is non-terminal so the candidate is retried
    once the cache is rebuilt; `apparatus` would retire it for good."""
    monkeypatch.setattr(runner.quarters, "exec_in",
                        lambda *a, **k: _Proc(1, "", "no matching wheel"))
    fail = runner._align_core_pin("cid123", "/work/x", "2.47.0")
    assert fail is not None
    assert fail.status == "error"
    assert "2.47.0" in fail.reason


def test_align_core_pin_noop_without_a_pin(monkeypatch):
    calls = []
    monkeypatch.setattr(runner.quarters, "exec_in",
                        lambda *a, **k: calls.append(a))
    assert runner._align_core_pin("cid", "/work/x", None) is None
    assert runner._align_core_pin("cid", "/work/x", "") is None
    assert calls == []


def test_measure_books_error_when_core_pin_cannot_align(monkeypatch):
    """End to end through _measure: a candidate whose pin cannot be aligned
    must never reach pytest with the wrong core. The record says `error`
    (non-terminal), never apparatus and never a verdict about the commit."""
    monkeypatch.setattr(runner, "_checkout", lambda *a, **k: None)
    monkeypatch.setattr(runner.quarters, "exec_in",
                        lambda *a, **k: _Proc(1, "", "no wheel"))
    cand = {"sha": SHA, "parent": PARENT,
            "files": ["tests/test_a.py", "pydantic/main.py"],
            "core_pin": "2.47.0"}
    out = dict(cand, anchored=True, **{"pass": 1, "before_failed": None})
    rec = runner._measure("cid", cand, "repo", out, "/work/x", False)
    assert rec["status"] == "error"
    assert "2.47.0" in rec["reason"]
    # The align step ran before pytest, so no measurement happened.
    assert rec["before_failed"] is None


def test_wheels_download_cmd_builds_uv_download(tmp_path, monkeypatch):
    cands_file = tmp_path / "candidates.jsonl"
    cand1 = {"sha": "a"*40, "quarter": "2026Q3", "core_pin": "2.47.0"}
    cand2 = {"sha": "b"*40, "quarter": "2026Q3", "core_pin": "2.48.0"}
    _write_candidates(cands_file, [cand1, cand2])
    monkeypatch.setattr(runner.quarters.record, "CANDIDATES", cands_file)
    cmd = runner.quarters._wheels_download_cmd("2026Q3")
    assert "pydantic-core==2.47.0" in cmd
    assert "pydantic-core==2.48.0" in cmd
    assert "pip download" in cmd


def test_wheels_download_cmd_skips_not_minable_and_bad_lines(tmp_path,
                                                             monkeypatch):
    """The cache is built for candidates the validator will actually measure:
    not_minable candidates never reach a container, so their pins must not
    bloat the image. A malformed line must be skipped, never fatal --
    candidates.jsonl is append-only output, and one corrupted record must not
    take the quarter's build down with it. A quarter with no pins emits no
    wheel layer at all."""
    cands_file = tmp_path / "candidates.jsonl"
    cands_file.write_text(
        "this is not json\n"
        + json.dumps({"sha": "a" * 40, "quarter": "2026Q3",
                      "core_pin": "2.47.0"}) + "\n"
        + json.dumps({"sha": "b" * 40, "quarter": "2026Q3",
                      "core_pin": "2.48.0",
                      "not_minable": "no_pytest_tests"}) + "\n"
        + json.dumps({"sha": "c" * 40, "quarter": "2025Q3",
                      "core_pin": "2.30.0"}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(runner.quarters.record, "CANDIDATES", cands_file)
    cmd = runner.quarters._wheels_download_cmd("2026Q3")
    assert "pydantic-core==2.47.0" in cmd
    assert "pydantic-core==2.48.0" not in cmd  # not_minable: no wheel needed
    assert "2.30.0" not in cmd                  # other quarter
    assert "pip download" in cmd
    # A quarter with no pinned candidates must not emit a wheel layer.
    assert runner.quarters._wheels_download_cmd("2020Q1") == ""


def test_guard_raises_container_lost_on_no_such_container():
    import pytest
    class Proc:
        returncode = 1
        stdout = ""
        stderr = "Error response from daemon: No such container: abc123"
    with pytest.raises(runner.ContainerLost) as exc_info:
        runner._guard(Proc(), "test_op")
    assert "container lost during test_op" in str(exc_info.value)


def test_measure_records_first_collect_error(monkeypatch):
    rec_err = outcomes.Record(
        nodeid="tests/test_fail.py",
        when="collect",
        outcome="failed",
        message="ModuleNotFoundError: No module named 'bar'\nExtra info",
    )
    res = _measure(
        monkeypatch,
        before={},
        after={},
        before_collect=[rec_err],
        collect_messages={"tests/test_fail.py": "ModuleNotFoundError: No module named 'bar'\nExtra info"},
    )
    assert res.get("first_collect_error") == "tests/test_fail.py: ModuleNotFoundError: No module named 'bar'"


def test_validate_quarter_stamps_profile_in_written_records(monkeypatch, tmp_path):
    cand = {
        "sha": "a" * 40,
        "parent": "b" * 40,
        "quarter": "2025Q3",
        "files": ["tests/test_a.py", "pydantic/main.py"],
    }
    candidates_path = tmp_path / "candidates.jsonl"
    validated_path = tmp_path / "validated.jsonl"
    _write_candidates(candidates_path, [cand])
    monkeypatch.setattr(runner.record, "CANDIDATES", candidates_path)
    monkeypatch.setattr(runner.record, "VALIDATED", validated_path)
    monkeypatch.setattr(runner.record, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(runner.record, "REPO", tmp_path / "repo")
    monkeypatch.setattr(runner.quarters, "preflight", lambda: None)

    Img = namedtuple("Img", "tag anchored anchor profile skip reason")
    fake_img = Img(
        tag="benchme:2025q3",
        anchored=True,
        anchor="abc",
        profile="uv_locked",
        skip=False,
        reason="",
    )
    monkeypatch.setattr(runner.quarters, "build_quarter_image", lambda *a, **k: fake_img)
    monkeypatch.setattr(runner.quarters, "start_container", lambda *a, **k: "cid123")
    monkeypatch.setattr(runner.quarters, "install_reporter", lambda *a, **k: None)
    monkeypatch.setattr(runner.quarters, "stop_container", lambda *a, **k: None)
    monkeypatch.setattr(runner.quarters, "remove_image", lambda *a, **k: None)

    def fake_validate_one(cid, cand, repo, anchored, pass2=False, pass1_f2p=None):
        out = dict(cand)
        out["status"] = "rejected:unchanged"
        out["before_failed"] = 0
        out["reason"] = "no test went fail->pass"
        return out

    monkeypatch.setattr(runner, "validate_one", fake_validate_one)

    counts = runner.validate_quarter("2025Q3", limit=10, keep_images=False, force=False)
    assert counts == {"rejected:unchanged": 1}
    lines = [l for l in validated_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["profile"] == "uv_locked"

def test_pdm_rerun_queue_selector_logic():
    import compare_rerun
    cand_a = {'sha': 'sha1', 'quarter': '2023Q3'}

    # 1. No existing record -> True
    assert runner.is_pdm_rerun_eligible(cand_a, None) is True

    # 2. Status error -> True
    assert runner.is_pdm_rerun_eligible(cand_a, {'status': 'error', 'anchored': True}) is True

    # 3. Entered container but anchored is False -> True
    assert runner.is_pdm_rerun_eligible(cand_a, {'status': 'apparatus', 'anchored': False}) is True

    # 4. Anchored is True -> False
    assert runner.is_pdm_rerun_eligible(cand_a, {'status': 'validated', 'anchored': True}) is False
    assert runner.is_pdm_rerun_eligible(cand_a, {'status': 'rejected:unchanged', 'anchored': True}) is False

    # 5. Pre-Docker not-minable (anchored is None) -> False
    assert runner.is_pdm_rerun_eligible(cand_a, {'status': 'not_minable:no_pytest_tests', 'anchored': None}) is False

    # Test select_pdm_rerun_queue
    all_cands = [
        {'sha': 'sha_new', 'quarter': '2023Q3'},
        {'sha': 'sha_err', 'quarter': '2023Q4'},
        {'sha': 'sha_unanchored', 'quarter': '2024Q1'},
        {'sha': 'sha_anchored', 'quarter': '2024Q1'},
        {'sha': 'sha_not_minable', 'quarter': '2024Q2'},
        {'sha': 'sha_wrong_quarter', 'quarter': '2025Q3'},
    ]
    done_recs = {
        'sha_err': {'status': 'error', 'anchored': True},
        'sha_unanchored': {'status': 'apparatus', 'anchored': False},
        'sha_anchored': {'status': 'validated', 'anchored': True},
        'sha_not_minable': {'status': 'not_minable:foreign_project', 'anchored': None},
        'sha_wrong_quarter': {'status': 'error', 'anchored': False},
    }
    quarters_set = {'2023Q3', '2023Q4', '2024Q1', '2024Q2'}

    queue = compare_rerun.select_pdm_rerun_queue(all_cands, done_recs, quarters_set)
    shas = [c['sha'] for c in queue]
    assert shas == ['sha_new', 'sha_err', 'sha_unanchored']
