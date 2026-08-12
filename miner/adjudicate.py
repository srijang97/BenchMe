"""Pure verdict logic for stage 2. No I/O: no Docker, no git, no filesystem.

Split out of runner._measure, which had grown to 370 lines with 19 status
assignments and 13 early returns. Every fix round in the previous phase was an
ORDERING bug in that function -- an arm firing before another that should have
won -- and none was catchable by unit test, because _measure needs a container.

The three-way status discipline this module exists to protect:

  rejected:<reason>   a verdict about the COMMIT
  not_minable:<why>   the commit is outside what this method can measure
  apparatus           OUR tooling failed
  error               a miner bug or transient infrastructure; NON-terminal

Arm order is the design. Read `adjudicate` top to bottom; first match wins.
"""
from typing import NamedTuple

import outcomes

EMPTY_OK = "ok"                        # targets is non-empty
EMPTY_NO_TEST_PATHS = "no_test_paths"  # the commit changed no test files
EMPTY_FILTERED = "filtered"            # dropped by NON_PYTEST_TEST_DIRS
EMPTY_NOT_RUNNABLE = "not_runnable"    # fixtures/conftest only, nothing to run
EMPTY_ABSENT = "absent"                # not present, and not because of deletion
EMPTY_DELETED = "deleted"              # the COMMIT deleted its test files

# Only EMPTY_DELETED and EMPTY_NO_TEST_PATHS are verdicts about the commit
# (rejected:no_runnable_tests / rejected:unchanged); EMPTY_FILTERED is a
# not_minable routing, and everything else -- including an unrecognised
# `why`, which is the point of testing membership rather than inequality --
# is ours and books apparatus.

PASS2_ERROR = "error"
PASS2_APPARATUS = "apparatus"
PASS2_UNSTABLE = "unstable"
PASS2_REPRODUCED = "reproduced"


class TargetSelection(NamedTuple):
    paths: list
    why: str        # one of the EMPTY_* constants
    detail: str     # human string naming the paths involved, or None


class Measurements(NamedTuple):
    pass2: bool
    targets: TargetSelection
    before: dict            # nodeid -> outcomes status
    after: dict             # nodeid -> outcomes status
    before_records: list    # outcomes.Record
    before_collect: list    # file paths that failed to collect
    after_collect: list
    pass1_f2p: list         # None on pass 1


class Verdict(NamedTuple):
    status: str
    reason: str
    fields: dict


class Pass2Check(NamedTuple):
    kind: str
    never_measured: list
    reproduced: list


def check_pass2_determinism(pass1_f2p, before, f2p_now):
    """Decide what pass 2's measurement says about pass 1's fail->pass set.

    Pure by construction -- dicts and lists in, a Pass2Check out, no container
    and no I/O -- because `_measure` cannot be tested without Docker and this
    decision is the part that must not regress. See miner/tests/test_adjudicate.py.

    `pass1_f2p` is pass 1's oracle, `before` is pass 2's before-run status map,
    `f2p_now` is pass 2's own fail->pass list.

    The order of the three tests is the contract:

      1. no `pass1_f2p` at all -> PASS2_ERROR. A programming error, reported as
         itself rather than smuggled into apparatus.
      2. an oracle node that pass 2 did not actually measure -> PASS2_APPARATUS.
         Nothing can be concluded about it -- "measured and did not flip" is a
         fact about the commit, "not measured" is a fact about us. Checked
         before reproduction so an unmeasured node cannot fall through into it.

         Two things count as not measured, and only these two:

           * absence from `before` -- a collection error in the full suite
             dropped the node, or pass 2's selection never reached it.
           * a before status of outcomes.SKIPPED -- the node was collected but
             the body never ran (a marker, an environment gate, a skipif that
             is true in this image). A skip is a SELECTION artefact, exactly
             like absence: the test did not execute, so it cannot have flipped,
             and booking `rejected:unstable` off it would state a verdict about
             the commit on the strength of something the commit did not cause.

         Every other status IS a measurement, including PASSED: a node that
         passed in pass 2's before run genuinely ran and genuinely did not
         start from a failure.
      3. every node measured, none flipped -> PASS2_UNSTABLE; otherwise
         PASS2_REPRODUCED with the intersection.
    """
    if not pass1_f2p:
        return Pass2Check(PASS2_ERROR, [], [])
    never_measured = sorted(t for t in pass1_f2p
                            if before.get(t) is None
                            or before.get(t) == outcomes.SKIPPED)
    if never_measured:
        return Pass2Check(PASS2_APPARATUS, never_measured, [])
    now = set(f2p_now)
    reproduced = sorted(t for t in pass1_f2p if t in now)
    if not reproduced:
        return Pass2Check(PASS2_UNSTABLE, [], [])
    return Pass2Check(PASS2_REPRODUCED, [], reproduced)


def labels_for(before_records, f2p):
    """How each fail->pass node failed on the before side.

    LABEL, never gate. Round 1 required an assertion-class base negative;
    round 2 retired that rule because fail-to-pass against the genuine upstream
    fix already establishes the failure was caused by the missing fix. A node id
    with no reporter message still gets a label ("unlabelled") rather than being
    rejected or defaulted to a qualifying class -- see outcomes.label.

    A function rather than an inline block because two call sites need it: the
    qualifying path, and the `rejected:unstable` path, which blanks `f2p` and
    relies on these labels to keep pass 2's raw set recoverable from the record.
    """
    wanted = set(f2p)
    messages = {r.nodeid: r.message for r in before_records
                if r.nodeid in wanted}
    return {t: outcomes.label(messages.get(t)) for t in f2p}


# Warning classes promoted to errors by a project's filterwarnings config do
# not follow the Error/Exception naming convention -- pydantic's
# PydanticExperimentalWarning is the measured case -- so match on the suffix
# rather than on a name table.
def import_block_kind(records, cleared):
    """Why the base state could not import: missing_symbol | warning_as_error | other.

    Sub-label only. The class it describes, rejected:base_import_blocked, is
    already decided by the time this is called; getting the sub-label wrong
    misreports a statistic and never changes a verdict.
    """
    cleared = set(cleared)
    for rec in records:
        if rec.when != "collect" or rec.nodeid not in cleared:
            continue
        msg = rec.message or ""
        head = msg.split(":", 1)[0].rsplit(".", 1)[-1].strip()
        if head.endswith("Warning"):
            return "warning_as_error"
        if head in ("ImportError", "ModuleNotFoundError", "AttributeError",
                    "NameError"):
            return "missing_symbol"
    return "other"


def adjudicate(m):
    """Decide a verdict from one candidate's measurements.

    Straight transcription of runner._measure's decision arms, in their
    current order. `fields` carries what a record must show beyond the
    evidence _measure already recorded (the diff, the blanked/narrowed oracle,
    the labels); _measure merges it into the record verbatim.
    """
    fields = {
        "before_collect_errors": list(m.before_collect),
        "after_collect_errors": list(m.after_collect),
    }

    # The selection arms. `_measure` reaches them with a TargetSelection built
    # from the probe; the no-test-paths arm is a fact about the commit, the
    # deleted arm is a fact about the commit, and EVERYTHING else -- including
    # an unrecognised `why`, which is the point of testing membership rather
    # than inequality -- is ours and books apparatus.
    if not m.targets.paths:
        if m.targets.why == EMPTY_NO_TEST_PATHS:
            return Verdict("rejected:unchanged", "no test paths", fields)
        if m.targets.why == EMPTY_FILTERED:
            return Verdict(
                "not_minable:no_pytest_tests",
                m.targets.detail,
                fields)
        if m.targets.why == EMPTY_DELETED:
            return Verdict(
                "rejected:no_runnable_tests",
                f"no runnable test file among the touched test "
                f"paths after the test patch: {m.targets.detail}",
                fields)
        return Verdict(
            "apparatus",
            f"OUR path selection left pass 1 with no target "
            f"({m.targets.why}): {m.targets.detail}"[:300],
            fields)

    if not m.before and not m.before_collect:
        return Verdict("apparatus", "no test outcomes on the before side",
                       fields)

    if not m.after:
        return Verdict("apparatus", "no test outcomes on the after side",
                       fields)

    # Collection errors were recorded and then ignored, which let them decide
    # verdicts silently. Under `--continue-on-collection-errors` a file that
    # imports on the before side and not on the after side does not FAIL -- its
    # tests simply cease to exist. They vanish, and even though outcomes.diff
    # now routes absent ids to `vanished` rather than `broken`, a vanished id
    # is still not evidence about the commit -- the node was never run on the
    # after side, so nothing can be concluded from its absence. The two sides
    # were not measured comparably, so NO comparison between them is honest --
    # apparatus, ours, not a verdict about the commit.
    #
    # Only errors NEW to the after side count. A collection error present on
    # both sides is a constant of the environment: it removes the same nodes
    # from both maps and the diff stays symmetric.
    new_after = [p for p in m.after_collect if p not in set(m.before_collect)]
    if new_after:
        return Verdict(
            "apparatus",
            f"{len(new_after)} file(s) failed to collect after the "
            f"code patch but not before, first {new_after[0]!r}; "
            f"the two sides were not measured comparably"[:300],
            fields)

    d = outcomes.diff(m.before, m.after)
    fields.update(
        f2p=d["f2p"],
        p2p_count=len(d["p2p"]),
        broken=d["broken"],
        renamed=d["renamed"],
        vanished=d["vanished"],
        error_base=d["error_base"],
        skipped_after=d["skipped_after"],
        tests_seen=len(m.before),
    )

    # ORDERING, deliberately explicit: the three outcomes below have to stay
    # distinguishable on the record's face.
    #
    #   error       OUR BUG -- the determinism check could not be made.
    #   apparatus   OUR TOOLING -- it did not measure what the check needs.
    #   rejected:*  a verdict about the COMMIT.
    #
    # ALL of pass 2's arms are decided BEFORE the `if not d["f2p"]` return
    # below, because that return is the wrong answer for every one of them.
    #
    # `--continue-on-collection-errors` means a collection error anywhere in
    # the full suite can drop pass-1's oracle nodes from pass 2's results, and
    # when it drops ALL of them d["f2p"] is empty and that return would book
    # `rejected:unchanged`: our tooling's failure wearing a verdict about the
    # commit, which is the precise failure class this redesign exists to
    # eliminate. Round 1 closed the partial case; round 2 closed the total one.
    #
    # The unstable arm has to come before it too. When pass 2 flips NOTHING AT
    # ALL -- the common shape of a flaky or selection-dependent oracle --
    # d["f2p"] is empty and this return fired first, so the record read
    # `rejected:unchanged, no test went fail->pass`, which is false on its face
    # for a record whose f2p_pass1 is non-empty: pass 1 saw exactly such a
    # test. Both are verdicts about the commit, so no discipline was broken,
    # but the `unstable` row counted only the pass-2 runs that happened to flip
    # some UNRELATED test, leaving the determinism rejection rate unmeasurable
    # -- which is the whole point of having the check.
    #
    # Pass 1 carries no pass1_f2p and never enters this block, so it still
    # books `rejected:unchanged` when nothing goes fail->pass -- for pass 1
    # that is a genuine verdict about the commit and is correct.
    #
    # For PASS 2 the `rejected:unchanged` return below is now UNREACHABLE, and
    # is retained only as a guard. The three arms above return on every other
    # kind, so a pass-2 record that reaches it must be PASS2_REPRODUCED, and
    # PASS2_REPRODUCED is only returned with a non-empty `reproduced`, which is
    # by construction a subset of d["f2p"] -- so d["f2p"] cannot be empty
    # there. If that return ever fires for a pass-2 record, the invariant has
    # been broken by an edit above and the record is telling the truth about
    # the diff while lying about the cause. Do not delete it: the cost of the
    # dead branch is nil and the cost of falling off the end of the function
    # is a record with no status at all.
    check = None
    if m.pass2:
        check = check_pass2_determinism(m.pass1_f2p, m.before, d["f2p"])
        # A pass-2 call carrying no pass-1 oracle is a MINER BUG, not a
        # property of the commit: validate_quarter only reaches pass 2 through
        # a `pass1_ok` record, which by construction has a non-empty f2p.
        # Skipping the check in that case would default a missing value toward
        # the qualifying outcome, which the project's global constraints forbid
        # outright. `error`, not apparatus and not rejected:*: it is our bug,
        # it is a programming error rather than a property of the commit or of
        # the environment, and `error` is non-terminal so the candidate is
        # retried once the bug is fixed.
        if check.kind == PASS2_ERROR:
            return Verdict(
                "error",
                "miner bug: pass 2 ran with no pass-1 fail->pass set, "
                "so the determinism check of decision 7 could not be "
                "made; refusing to book a validated record without it",
                fields)

        fields["f2p_pass1"] = sorted(m.pass1_f2p)
        fields["f2p_reproduced"] = check.reproduced

        # "Measured and did not flip" is not "not measured", and only the first
        # is a fact about the commit. A node missing from pass 2's before-run
        # status map, or present in it as SKIPPED, did not execute, so nothing
        # can be concluded about it: apparatus, which is ours and terminal.
        if check.kind == PASS2_APPARATUS:
            n_before = len(m.before_collect)
            n_after = len(m.after_collect)
            missing = check.never_measured
            reason = (
                f"{len(missing)} of {len(m.pass1_f2p)} pass-1 fail->pass "
                f"test(s) were not measured in pass 2 (absent from the "
                f"before run, or collected but skipped), so the "
                f"determinism check cannot be made (first: "
                f"{missing[0]}); pass-2 collection errors: "
                f"{n_before} before, {n_after} after")
            # Pass 2's own raw f2p set is not an oracle here either: the pass-1
            # nodes it would have to agree with were never measured, so nothing
            # in it has been confirmed by two runs. Blanked for the same reason
            # as the unstable path below -- a downstream reader must not be
            # able to mistake it for a usable oracle. What happened stays on
            # the record in f2p_pass1, f2p_reproduced and the collection-error
            # lists.
            fields["f2p"] = []
            return Verdict("apparatus", reason, fields)

        # Decision 7: the transition must reproduce. Pass 2 is an independent
        # measurement -- fresh clone, fresh patch, full-suite selection rather
        # than the touched files -- so an f2p that appears in pass 1 and not
        # here is either flaky or selection-dependent. Kimi's point in round
        # 2: flakiness, not taxonomy, is the plausible mechanism by which a
        # test "passes for unrelated reasons".
        #
        # This arm sits ABOVE the `rejected:unchanged` return, not below it:
        # the commonest unstable shape is pass 2 flipping nothing at all, and
        # from below this arm was unreachable on exactly that shape. See the
        # ordering note above.
        if check.kind == PASS2_UNSTABLE:
            reason = (
                f"all {len(m.pass1_f2p)} pass-1 fail->pass test(s) were "
                f"measured in the full-suite pass-2 run and none "
                f"reproduced the fail->pass transition")
            # Pass 2's own raw f2p set is not an oracle here -- nothing in it
            # reproduced -- and leaving it in place lets a downstream reader
            # mistake it for one while `f2p_reproduced` is empty. It stays
            # recoverable from `failure_labels`, whose keys are that set, which
            # is why the labels are built here rather than left to the
            # qualifying path below.
            fields["failure_labels"] = labels_for(m.before_records, d["f2p"])
            fields["f2p"] = []
            return Verdict("rejected:unstable", reason, fields)

        # Pass2Check.kind is CLOSED here. The three arms above have returned,
        # so only PASS2_REPRODUCED may continue -- and it must say so out loud.
        # Falling through implicitly would mean a fifth kind added later
        # reaches `validated` by default, i.e. an unrecognised value defaulting
        # to the qualifying outcome, which the project's global constraints
        # forbid. `error`, not apparatus: a kind this function does not
        # recognise is a miner bug, and `error` is non-terminal so the
        # candidate is retried once the bug is fixed.
        if check.kind != PASS2_REPRODUCED:
            return Verdict(
                "error",
                f"miner bug: unrecognised pass-2 determinism kind "
                f"{check.kind!r}; refusing to book a validated record "
                f"on a check outcome this code does not understand",
                fields)

    if not d["f2p"]:
        # ROW 9 -- an oracle was found, so the collection errors cost us potential
        # EXTRA oracle tests, not the answer. This ordering is the aa7705f7 fix:
        # it had 869 tests collected and 773 passing and was thrown away because 2
        # of its 4 touched files failed to import. The previous phase's own
        # reviewer warned in the same review that over-correcting into apparatus
        # is a defect too, because apparatus is terminal.
        # Rows 10-12 only run when no oracle was found.
        cleared = [p for p in m.before_collect if p not in set(m.after_collect)]
        if cleared:
            # ROW 10 -- the code patch fixed the import, so the block is
            # intrinsic to the commit. Excluded from the corpus per council
            # decision 2 (the assertions never ran against unfixed code) but
            # COUNTED, which is what finally gives missing_api a denominator.
            fields["import_block_kind"] = import_block_kind(
                m.before_records, cleared)
            return Verdict(
                "rejected:base_import_blocked",
                f"{len(cleared)} file(s) failed to collect on the before side "
                f"but not after, so the base state could not import the test "
                f"module ({fields['import_block_kind']}, first: {cleared[0]!r})"[:300],
                fields)
        if m.before_collect:
            # ROW 11 -- unchanged by the patch, so the cause is outside the commit
            return Verdict(
                "apparatus",
                f"{len(m.before_collect)} file(s) failed to collect on the before "
                f"side and still fail after the code patch, first {m.before_collect[0]!r}; "
                f"the cause lives outside the commit"[:300],
                fields)
        # ROW 12
        # error_base is spelled out in the reason because it is the one
        # rejection the new contract still makes on failure kind, and it is
        # the number a future audit of decision 2 will need.
        detail = "no test went fail->pass"
        if d["error_base"]:
            detail += (f"; {len(d['error_base'])} test(s) went error->pass, "
                       f"which is not an admissible base negative")
        return Verdict("rejected:unchanged", detail, fields)

    fields["failure_labels"] = labels_for(m.before_records, d["f2p"])

    if m.pass2:
        # Every pass-1 oracle node was measured and at least one reproduced.
        # The oracle is the INTERSECTION. A test that only flips in one of the
        # two runs is not something we are willing to grade an agent on. No
        # `if reproduced:` guard: the branch above already returned on empty,
        # and a guard here would read as though an empty intersection could
        # still reach `validated`.
        # A copy, not the same list object as f2p_reproduced: two record fields
        # aliasing one list is a trap for any later code that edits either.
        fields["f2p"] = list(check.reproduced)
        # failure_labels was built from the pass-2 f2p set a few lines up.
        # Narrowing the oracle without narrowing the labels would leave
        # report._composition counting labels for node ids that are not in
        # the capsule's oracle.
        fields["failure_labels"] = {
            t: lbl for t, lbl in fields["failure_labels"].items()
            if t in set(fields["f2p"])}

    if m.pass2 and d["broken"]:
        # `broken` is RAN AND FAILED only -- a vanished id never lands here, so
        # every id in this arm is a genuine after-side failure. The reason
        # states the failed count, and mentions the vanished count separately
        # when non-zero: the two have different causes (a real regression
        # versus a rename the exact-swap rule did not reconcile), and report._regressions
        # exists only because the recorded reason used to conflate them.
        reason = (f"{len(d['broken'])} previously-passing test(s) fail after "
                  f"the code patch")
        if d["vanished"]:
            reason += (f" and {len(d['vanished'])} test(s) vanished from the "
                       f"after run")
        return Verdict(
            "rejected:regression_broken",
            f"{reason} (first: {d['broken'][0]})"[:300],
            fields)

    return Verdict("validated" if m.pass2 else "pass1_ok", None, fields)
