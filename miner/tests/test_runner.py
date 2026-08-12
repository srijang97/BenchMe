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
                    timeout=1800):
        status = before if phase == runner.BEFORE else after
        collect = before_collect if phase == runner.BEFORE else after_collect
        records = [outcomes.Record(n, "call", "failed", messages.get(n))
                   for n, s in status.items() if s == outcomes.FAILURE]
        errors = [outcomes.Record(n, "collect", "failed",
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
    assert "0 vanished" in rec["reason"]


def test_regression_reason_does_not_call_a_vanished_node_a_failure(monkeypatch):
    # C passed before and is ABSENT after -- no exact-swap rename to excuse it,
    # so it is `broken`. It did not FAIL, though: saying so on the record was
    # false about the one number a reader uses to judge the verdict.
    rec = _measure(monkeypatch,
                   before={A: outcomes.FAILURE, C: outcomes.PASSED},
                   after={A: outcomes.PASSED},
                   pass1_f2p=[A])
    assert rec["status"] == "rejected:regression_broken"
    assert "0 previously-passing test(s) fail" in rec["reason"]
    assert "1 vanished" in rec["reason"]


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
    # THE LIVE DEFECT. dac3c437 and 568509c0 are on disk as terminal
    # `rejected:unchanged` records because their only test path lived under
    # tests/typechecking/ -- OUR hand-maintained NON_PYTEST_TEST_DIRS filter,
    # which candidates.py's own comment says must never become a verdict about
    # the commit.
    rec = _measure(
        monkeypatch, before={}, after={}, pass2=False,
        runnable=runner.RunnableTargets(
            [], None, runner.EMPTY_FILTERED,
            "every touched test path was dropped by OUR "
            "candidates.NON_PYTEST_TEST_DIRS filter: tests/typechecking/x.py"))
    assert rec["status"] == "apparatus"
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
    rec = _measure(
        monkeypatch, before={}, after={}, pass2=False,
        runnable=runner.RunnableTargets(
            [], None, runner.EMPTY_DELETED,
            "the commit deletes every test file it touches: tests/test_a.py"))
    assert rec["status"] == "rejected:unchanged"
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
    def exec_in(container, argv, timeout=1800):
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
