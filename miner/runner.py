"""Stage 2 orchestration: two passes over one quarter's candidates.

Pass 1 runs only the test files the commit touched -- cheap, and it eliminates
most candidates. Pass 2 runs the full suite on survivors only, to establish the
pass-to-pass set, catch a code patch that breaks something elsewhere, and --
because it is a fresh clone, a fresh patch application and a different
selection -- serve as the independent rerun that pass 1's fail-to-pass set has
to reproduce (decision 7). The oracle is the intersection of the two runs; a
transition that does not reproduce is `rejected:unstable`.

Both passes run inside ONE long-lived container for the quarter, torn down in a
`finally` no matter how a candidate ends.

Two distinctions are load-bearing here and are never allowed to blur:

  rejected:<reason>   a verdict about the COMMIT -- it does not qualify.
                      TERMINAL.
  apparatus           a verdict about US, and a DURABLE one -- the patch would
                      not apply, nothing parsed, our path filters left no
                      target, validate.py raised. Also TERMINAL: rerunning it
                      unchanged would fail the same way.
  error               a verdict about US that a rerun may not repeat -- a miner
                      bug, or transient infrastructure (the container timed
                      out, the clone failed, the patch could not be streamed
                      in). NON-terminal in record.is_done, so the candidate is
                      retried once the tooling is fixed. When in doubt between
                      apparatus and error, prefer error: the cost of a retry is
                      one run, the cost of a wrong `apparatus` is a candidate
                      retired for good.

  anchored=True       the image was built from the quarter's frozen lockfile.
  anchored=False      it was resolved fresh: a MODERN environment wearing the
                      quarter's name. Every other check still passes, including
                      the import probe, so nothing but this flag can tell the
                      reader that the results were measured against the wrong
                      dependencies. It is therefore stamped onto EVERY record
                      this module writes, at the single point of writing, so no
                      future branch can forget it.
"""
import json
import shlex
import subprocess
import sys
import traceback
from collections import namedtuple
from pathlib import Path, PurePosixPath
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import metrics  # noqa: E402
import tierb  # noqa: E402

import adjudicate  # noqa: E402
from adjudicate import (EMPTY_ABSENT, EMPTY_DELETED, EMPTY_FILTERED,
                        EMPTY_NOT_RUNNABLE)  # noqa: E402
import candidates  # noqa: E402
import outcomes  # noqa: E402
import quarters  # noqa: E402
import record  # noqa: E402
import validate  # noqa: E402

BEFORE, AFTER = "before", "after"

# The reporter plugin reads its destination from this variable; the runner
# passes a distinct path per phase so the two runs cannot append to one file.
#
# COLUMNS/CI are gone: they existed only to stop pytest truncating the
# short-summary detail to terminal width. The reporter takes its message from
# report.longrepr.reprcrash, which is never truncated -- verified against
# pytest 8.3.4, including under the --tb=no already in tierb.PYTEST_ARGV.
#
# `-p no:pretty` is also gone as a correctness measure. pytest-pretty replaced
# the summary block, which used to blind the old parser completely; the
# reporter hooks pytest_runtest_logreport and is indifferent to whatever the
# terminal reporter does.
#
# `--continue-on-collection-errors` is load-bearing. Measured: with one broken
# import present, a 20-test run reported 1 test -- a single collection error
# aborts the whole session, so an unrelated bad file silently zeroes a
# candidate's outcomes and it books as apparatus or `rejected:unchanged`.
PYTEST_EXTRA = ["--continue-on-collection-errors"]


class ContainerLost(Exception):
    """The container can no longer be trusted, so the quarter stops here.

    Raised on an exec timeout. Per `quarters.exec_in`'s caller contract,
    killing `docker exec` does NOT kill the process inside the container: it
    keeps running, keeps burning the capped CPU and memory, and holds the
    one-container-at-a-time slot. Continuing to the next candidate in that
    container would measure it against a machine already under an unknown
    load, so the run ends and the container is torn down.
    """


def _guard(proc, what):
    """Turn an exec timeout into ContainerLost; otherwise hand the result back."""
    if proc.returncode == tierb.TIMEOUT_RETURNCODE:
        raise ContainerLost(f"{what} timed out; container is not reusable")
    return proc


# What a container-side step failed AS, carried alongside the reason so the
# call site cannot flatten the distinction back out. `status` is "apparatus"
# (ours and TERMINAL -- an un-retryable fact, e.g. the patch does not apply to
# this tree) or "error" (ours and NON-terminal -- transient infrastructure, so
# the candidate is retried). See record.is_done.
Failure = namedtuple("Failure", "status reason")


def _checkout(container, sha, workdir):
    """None on success, else a Failure.

    A clone or checkout that fails is TRANSIENT INFRASTRUCTURE, not a fact
    about the commit and not an un-retryable fact about our tooling: the disk
    filled, the promisor was unreachable, the container's git was wedged. It is
    the same class of event as the ContainerLost timeout, which
    validate_quarter deliberately books as `error` precisely so that
    infrastructure loss does not permanently retire a possibly-valid candidate.
    `error` is non-terminal in record.is_done, so the candidate comes back on
    the next sweep; `apparatus` would retire it for good.
    """
    r = _guard(quarters.exec_in(container, ["git", "clone", "--quiet",
                                            "--no-checkout", "/repo", workdir]),
               "git clone")
    if r.returncode != 0:
        return Failure("error", f"clone failed: {(r.stdout + r.stderr)[:200]}")
    r = _guard(quarters.exec_in(
        container, ["git", "-C", workdir, "checkout", "--quiet", sha]),
        "git checkout")
    if r.returncode != 0:
        return Failure("error",
                       f"checkout failed: {(r.stdout + r.stderr)[:200]}")
    return None


def _apply(container, workdir, patch_text, label):
    """None on success, else a Failure. Two very different failures:

      * the patch could not be WRITTEN into the container -- the `docker exec
        -i` that streams it died. Transient infrastructure, exactly like
        _checkout and like the ContainerLost timeout validate_quarter books as
        `error`, so it is `error`: non-terminal, retried on the next sweep.
        Booking it apparatus would retire a possibly-valid candidate on the
        strength of a hiccup in a pipe.
      * the patch would not APPLY. That is a durable fact about our capture --
        the same diff against the same tree will fail the same way -- so it
        stays `apparatus`, terminal, and is not retried until the capture is
        fixed.
    """
    if not patch_text.strip():
        return None
    path = f"{workdir}/.{label}.patch"
    # Written via `docker exec -i` rather than quarters.exec_in because the
    # patch text has to arrive on stdin; exec_in captures output but pipes
    # nothing in.
    #
    # BYTES, not text=True. subprocess wraps stdin in a TextIOWrapper with
    # newline=None, which on Windows translates every "\n" to "\r\n" on the
    # way out. The patch then lands in the container with CRLF line endings
    # its pre-image does not have, and `git apply` rejects it -- measured:
    # "patch failed: tests/test_docs.py:97 ... patch does not apply", which
    # reads exactly like a real 3-way conflict and would have been written off
    # as one candidate after another going apparatus. Bytes also keep
    # make_patch's --binary hunks intact.
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "sh", "-c", f"cat > {path}"],
        input=patch_text.encode("utf-8"), capture_output=True,
        env=tierb.docker_env())
    if proc.returncode != 0:
        # Transient: see the docstring. `error`, not apparatus.
        return Failure("error",
                       f"could not write {label} patch into the container "
                       f"(rc={proc.returncode}): "
                       f"{proc.stderr.decode('utf-8', 'replace')[:200]}")
    r = _guard(quarters.exec_in(
        container, ["git", "-C", workdir, "apply", "--3way", path]),
        f"git apply ({label})")
    if r.returncode != 0:
        return Failure(
            "apparatus",
            f"{label} patch would not apply: {(r.stdout + r.stderr)[:200]}")
    return None


def _pytest(container, workdir, targets, log_path, phase, timeout=1800):
    """Run pytest on `targets`; return
    (status_map, records, collect_errors, output).

    `status_map` is node id -> one of outcomes.FAILURE/ERROR/PASSED/SKIPPED.
    `records` is the raw list of outcomes.Record, kept because labelling needs
    each failing node's message and the collapsed map does not carry it, and
    because `adjudicate.import_block_kind` classifies row-10 blocks from the
    collect records. The test and collect record lists are merged here -- the
    single point where both exist -- so `Measurements.before_records` (and the
    labels built from it) see the actual before-side collect Records in live
    runs. The two lists are the two report channels: `rep.tests` holds the
    phase records (`when` in call/setup/teardown), `rep.collect` the
    collection errors (`when == "collect"`); a labeler that only ever sees
    `rep.tests` would classify every cleared import block as "other".

    Raises ValueError when the session cannot be concluded from, in three
    ways, ALL of which the caller books as apparatus:

      * the report is malformed -- a partial or interleaved line;
      * the report is truncated -- the plugin never wrote its sessionfinish
        terminator, so the session did not run to the end;
      * the session finished on an exit status outside
        outcomes.OK_EXIT_STATUSES. The terminator's presence does NOT prove
        completion: pytest calls pytest_sessionfinish from wrap_session's
        `finally` whenever sessionstart ran, including on INTERRUPTED (2) and
        INTERNAL_ERROR (3). Such a session writes some records and then the
        terminator, the report parses as complete, the candidate's oracle test
        is silently missing, and pass 1 books `rejected:unchanged` -- a
        terminal verdict about the COMMIT caused by OUR crash. Only 0 (all
        passed), 1 (tests failed) and 5 (nothing collected) are conclusions;
        5 stays acceptable because the `if not before` / `if not after` guards
        in _measure describe that case far better than this check could.

    The checkout goes on PYTHONPATH because the image deliberately does NOT
    contain the project itself -- see quarters' module docstring. The reporter
    directory goes on PYTHONPATH too, so `-p benchme_reporter` can import it.
    """
    report_path = f"/tmp/benchme-{phase}-{PurePosixPath(workdir).name}.jsonl"
    wd = shlex.quote(workdir)
    # `|| exit 3` is the same idiom _runnable_targets uses. The point is that
    # a failed `cd` must not let the `cat` below read a STALE report -- one
    # left at this exact path by an earlier run of the same candidate and
    # phase, reachable on a `--force` re-run inside one container. Under the
    # old `cd && rm -f && pytest`, a failed cd skipped both the rm and pytest,
    # the stale file survived, and the cat returned the PREVIOUS run's data as
    # this run's measurement.
    #
    # The `rm -f` goes BEFORE the cd, not after it: `exit 3` terminates the
    # shell, so an rm sequenced after the cd is skipped on exactly the branch
    # that needs it (verified). Unlinking first means a failed cd leaves no
    # report at all, the cat fails, and _pytest raises -- apparatus, which is
    # the honest answer. The path is absolute, so removing it before the cd is
    # safe.
    cmd = (
        "rm -f {rp}; cd {wd} || exit 3; {env}={rp} PYTHONPATH={rd}:{wd} "
        "{argv} -p {plugin} {t} 2>&1"
    ).format(
        wd=wd, rp=shlex.quote(report_path), env=quarters.REPORT_ENV,
        rd=quarters.REPORTER_DIR, plugin=quarters.PLUGIN_MODULE,
        argv=" ".join([*tierb.PYTEST_ARGV, *PYTEST_EXTRA]),
        t=" ".join(shlex.quote(t) for t in targets))
    r = _guard(quarters.exec_in(container, ["sh", "-c", cmd], timeout=timeout),
               "pytest")
    out = r.stdout + r.stderr
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(log_path).write_text(f"$ {cmd}\n{out}", encoding="utf-8")

    # Read the report as a SEPARATE exec. Interleaving it into the pytest
    # command would mix it with pytest's own stdout, which is exactly the
    # coupling this redesign removes.
    rr = _guard(quarters.exec_in(container, ["cat", report_path]),
                "read report")
    if rr.returncode != 0:
        # An empty or absent report is indistinguishable from "no tests ran"
        # to every downstream check, so it must surface here rather than
        # become `rejected:unchanged`.
        raise ValueError(
            f"reporter wrote nothing for the {phase} run (rc={rr.returncode}); "
            f"pytest exited {r.returncode}: {out[-300:]}")
    rep = outcomes.parse_report(rr.stdout)
    if rep.exitstatus not in outcomes.OK_EXIT_STATUSES:
        # None (no usable status in the terminator) lands here too: a missing
        # value must never default to the acceptable case.
        raise ValueError(
            f"the {phase} pytest session finished on exit status "
            f"{rep.exitstatus} (acceptable: "
            f"{sorted(outcomes.OK_EXIT_STATUSES)}), so it did not run to the "
            f"end and nothing may be concluded from its "
            f"{len(rep.tests)} test and {len(rep.collect)} collect record(s); "
            f"pytest exited {r.returncode}: {out[-200:]}")
    return (outcomes.collapse(rep.tests),
            [*rep.tests, *rep.collect],
            rep.collect,
            out)


# Why _runnable_targets came back with nothing to run: the EMPTY_* constants
# (EMPTY_FILTERED, EMPTY_NOT_RUNNABLE, EMPTY_ABSENT, EMPTY_DELETED) and the
# verdict-membership rule now live in adjudicate.py, alongside the arm that
# turns them into verdicts. This file only imports them back for
# _runnable_targets' own reporting.


class RunnableTargets(NamedTuple):
    """`paths` is empty exactly when `why` is set; `err` means the probe broke.

    Three channels rather than two, because "we found nothing to run" has four
    causes that must not be flattened -- see the EMPTY_* constants. `detail` is
    a human string naming the paths involved, ready to drop into a record's
    reason.
    """
    paths: list
    err: str
    why: str
    detail: str


def _runnable_targets(container, workdir, tests):
    """The touched test paths pytest can actually be pointed at, that exist.

    `validate.split_paths` uses the deliberately broader `_belongs_to_test_side`
    (fixture data under tests/, a root conftest.py), which is right for
    deciding which side of the patch a path belongs on and wrong for deciding
    what to hand pytest: a JSON fixture or a conftest as the only target
    collects nothing, pytest exits with no outcomes, and a perfectly good
    candidate is booked as apparatus. Same for a test file the commit DELETES
    -- it is gone once the test patch applies, and for a path under
    candidates.NON_PYTEST_TEST_DIRS, which looks like a test file to
    metrics.is_test_file but is a static type-checker fixture pytest collects
    nothing from. Filtering here keeps all of those out of the apparatus
    column.

    Returns a RunnableTargets. `err` is not None when the PROBE ITSELF failed:
    an unchecked probe returns an empty set on failure, which is
    indistinguishable from "the commit touches no runnable test" and lands as
    `rejected:unchanged` -- the same shape as the `_numstat` defect fixed in
    Task 2. The loop is written with `if ... then` rather than `[ -e p ] && ...`
    precisely so the shell's exit status reports the probe, not whether the
    last path happened to exist.

    `why` is what makes the empty result legible to the caller. The probe
    classifies every path it cannot find: a path that IS in the parent commit
    (`git cat-file -e HEAD:<p>`, HEAD being the parent, since the workdir is a
    checkout of it with the test patch applied but not committed) and is now
    gone was deleted by the commit's own test patch -- the one genuine verdict.
    A path that is in neither is unexplained, which is ours.
    """
    filtered = [t for t in tests
                if candidates.is_non_pytest_test(record.REPO.name, t)]
    dropped = set(filtered)
    wanted = [t for t in tests
              if t not in dropped
              and metrics.is_test_file(t)
              and PurePosixPath(t).name != "conftest.py"]
    if not wanted:
        # Both branches are OURS. The first is the hand-maintained config
        # filter, known incomplete; the second is validate._belongs_to_test_side
        # admitting a path (a non-.py fixture, a conftest.py) that is real but
        # not something pytest can be pointed at on its own.
        if filtered:
            rest = sorted(set(tests) - dropped)
            return RunnableTargets(
                [], None, EMPTY_FILTERED,
                "OUR candidates.NON_PYTEST_TEST_DIRS filter dropped "
                + ", ".join(sorted(filtered)[:8])
                + (", and nothing runnable remains among "
                   + ", ".join(rest[:8]) if rest
                   else ", which was every test path the commit touched"))
        return RunnableTargets(
            [], None, EMPTY_NOT_RUNNABLE,
            "no runnable pytest target among the touched test paths (all are "
            "fixtures, non-.py assets or conftest.py): "
            + ", ".join(sorted(tests)[:8]))
    script = (
        "cd {wd} || exit 3; "
        "for p in {ps}; do "
        "if [ -e \"$p\" ]; then echo \"present $p\"; "
        "elif git cat-file -e \"HEAD:$p\" 2>/dev/null; then echo \"deleted $p\"; "
        "else echo \"absent $p\"; fi; done"
    ).format(wd=shlex.quote(workdir),
             ps=" ".join(shlex.quote(p) for p in wanted))
    r = _guard(quarters.exec_in(container, ["sh", "-c", script]), "target probe")
    if r.returncode != 0:
        return RunnableTargets(None, "target probe failed (rc={}): {}".format(
            r.returncode, (r.stdout + r.stderr)[:200]), None, None)
    seen = {}
    for line in r.stdout.splitlines():
        state, _, path = line.strip().partition(" ")
        if state in ("present", "deleted", "absent") and path:
            seen[path] = state
    present = [t for t in wanted if seen.get(t) == "present"]
    if present:
        return RunnableTargets(present, None, None, None)
    # Nothing to run. `absent` outranks `deleted`: a path the probe cannot
    # explain means our picture of the tree is wrong, and ambiguity resolves
    # toward apparatus, never toward a verdict about the commit.
    unexplained = [t for t in wanted if seen.get(t) != "deleted"]
    if unexplained:
        return RunnableTargets(
            [], None, EMPTY_ABSENT,
            "the existence probe found no runnable test path present, and "
            "these are not explained by a deletion in the commit: "
            + ", ".join(sorted(unexplained)[:8]))
    return RunnableTargets(
        [], None, EMPTY_DELETED,
        "the commit deletes every test file it touches: "
        + ", ".join(sorted(wanted)[:8]))


def validate_one(container, cand, repo, anchored, pass2=False, pass1_f2p=None):
    """Returns a record dict. Never raises for a candidate-level problem.

    Raises ContainerLost when the container itself is gone; that is a run-level
    problem, not a candidate-level one.

    Owns the workdir's lifetime. The checkout is ~430 MB, so removing it only
    on the success path lets a long `--limit` fill the disk; the clone then
    starts failing and every later candidate is recorded `apparatus`, which
    reads as a property of the candidates rather than of the run.
    """
    workdir = f"/work/{cand['sha'][:12]}"
    out = dict(cand)
    out["anchored"] = anchored
    out["pass"] = 2 if pass2 else 1
    # Always present, so a reader can tell "no before run happened" (None)
    # from "the before run had no failures" (0). See _measure.
    out["before_failed"] = None
    lost = False
    try:
        return _measure(container, cand, repo, out, workdir, pass2,
                        pass1_f2p=pass1_f2p)
    except ContainerLost:
        # The container is about to be destroyed by validate_quarter; an exec
        # against it would at best waste the timeout.
        lost = True
        raise
    finally:
        if not lost:
            # Unguarded on purpose: raising ContainerLost out of a `finally`
            # would replace the candidate's real outcome with the cleanup's.
            quarters.exec_in(container, ["rm", "-rf", workdir], timeout=300)


# Pass 2's determinism decision and the failure labels now live in
# adjudicate.py; _pass2_targets below is the only pass-2 logic left here
# because it probes the container.


def _pass2_targets(container, workdir, tests):
    """(targets, err) for the full-suite pass.

    "tests" alone is NOT enough. Pass 1 points pytest at the touched test files
    and its oracle can therefore come from any path `metrics.is_test_file`
    accepts -- and that predicate matches `test_*.py` ANYWHERE in the tree, not
    only under `tests/`. An oracle node from such a file can never appear in
    pass 2's before-run map, so the determinism check books it as never
    measured, which is `apparatus` and TERMINAL: a fixable gap in OUR selection
    would permanently retire a candidate that may be perfectly good.

    Fixed at the source rather than at the check. The union keeps "tests" -- the
    full suite still runs, which is what makes pass 2 an independent
    measurement and what catches a code patch that breaks something elsewhere --
    and adds the touched test files that live outside it. `_runnable_targets`
    is reused rather than reimplemented so the conftest, deleted-file and
    NON_PYTEST_TEST_DIRS filters and the existence probe all still apply, and
    its probe error is handled exactly as pass 1 handles it.

    `why` is deliberately ignored here: pass 2 always has the "tests" target, so
    an empty extra set is not an empty selection and says nothing about the
    candidate. Only pass 1 has to adjudicate it.
    """
    found = _runnable_targets(container, workdir, tests)
    if found.err:
        return None, found.err
    targets = ["tests"]
    for t in found.paths:
        # Anything already under tests/ is covered by the "tests" target;
        # naming it twice makes pytest collect the file a second time.
        if PurePosixPath(t).parts[:1] == ("tests",) or t in targets:
            continue
        targets.append(t)
    return targets, None


def _measure(container, cand, repo, out, workdir, pass2, pass1_f2p=None):
    """The body of validate_one, minus the workdir lifetime."""
    sha, parent = cand["sha"], cand["parent"]
    logs = record.LOGS / sha[:12]

    tests, code = validate.split_paths(cand["files"])
    if not tests:
        # The commit changed no test files: a verdict about the commit, and
        # nothing has been measured yet, so there is nothing to adjudicate.
        verdict = adjudicate.adjudicate(adjudicate.Measurements(
            pass2=pass2,
            targets=adjudicate.TargetSelection([], adjudicate.EMPTY_NO_TEST_PATHS,
                                               None),
            before={}, after={}, before_records=[], before_collect=[],
            after_collect=[], pass1_f2p=pass1_f2p))
        out.update(status=verdict.status, reason=verdict.reason)
        out.update(verdict.fields)
        return out

    # `fail.status` is "error" here, not "apparatus": a clone or checkout that
    # failed is transient infrastructure, and `error` is non-terminal so the
    # candidate is retried. See _checkout.
    fail = _checkout(container, parent, workdir)
    if fail:
        out.update(status=fail.status, reason=fail.reason)
        return out

    # validate.make_patch raises when a non-empty pathspec yields an empty
    # diff, and outcomes.parse_report raises on a truncated or interleaved
    # reporter line. Both mean OUR capture is wrong, so both are apparatus --
    # never a verdict about the commit. Anything else escaping is a miner bug
    # and is booked as `error` by validate_quarter.
    try:
        test_patch = validate.make_patch(repo, parent, sha, tests)
        code_patch = validate.make_patch(repo, parent, sha, code)
    except RuntimeError as exc:
        out.update(status="apparatus", reason=f"make_patch: {exc}"[:300])
        return out

    # "could not write the patch" is transient and books `error`; "the patch
    # would not apply" is durable and books `apparatus`. _apply decides which,
    # because only _apply can tell them apart.
    fail = _apply(container, workdir, test_patch, "test")
    if fail:
        out.update(status=fail.status, reason=fail.reason)
        return out

    if pass2:
        targets, probe_err = _pass2_targets(container, workdir, tests)
        if probe_err:
            out.update(status="apparatus", reason=probe_err)
            return out
        selection = adjudicate.TargetSelection(targets, adjudicate.EMPTY_OK,
                                               None)
    else:
        found = _runnable_targets(container, workdir, tests)
        if found.err:
            out.update(status="apparatus", reason=found.err)
            return out
        targets = found.paths
        selection = adjudicate.TargetSelection(found.paths, found.why,
                                               found.detail)
        if not selection.paths:
            # The empty-selection decision (deleted -> verdict about the
            # commit; filtered / not-runnable / absent / unrecognised -> our
            # tooling) lives in adjudicate. Membership, not inequality: an
            # EMPTY_* value this code does not recognise must fall to
            # apparatus, never to a verdict.
            verdict = adjudicate.adjudicate(adjudicate.Measurements(
                pass2=pass2, targets=selection, before={}, after={},
                before_records=[], before_collect=[], after_collect=[],
                pass1_f2p=pass1_f2p))
            out.update(status=verdict.status, reason=verdict.reason)
            out.update(verdict.fields)
            return out

    try:
        before, before_records, before_collect, _ = _pytest(
            container, workdir, targets, logs / f"{BEFORE}.log", BEFORE)
    except ValueError as exc:
        out.update(status="apparatus", reason=f"before report: {exc}"[:300])
        return out
    # Recorded on every candidate that got a before run, because it is the
    # only way to audit a `rejected:unchanged` afterwards. The image is
    # anchored to the lockfile at the quarter's LAST commit, so a candidate
    # from mid-quarter can see hundreds of failures that have nothing to do
    # with it (measured: 840 of 6437 on 2025Q3, from a pydantic-core version
    # skew).
    out["before_failed"] = sum(1 for v in before.values()
                               if v == outcomes.FAILURE)
    out["before_collect_errors"] = [r.nodeid for r in before_collect]

    # Narrowed guard (Task 2 amendment). Only an empty `before` with NO
    # before-side collection errors may short-circuit before the after run.
    # Any before_collect candidate -- including an empty `before` -- must
    # apply the code patch and run the after side so rows 9-11 can decide
    # whether the errors cleared (row 10) or persisted (row 11), and so the
    # after-side evidence exists on the record. This is the "one extra pytest
    # run" cost the spec accepts in §4.2: without it rows 10 vs 11 are
    # indistinguishable at the before side alone.
    #
    # `adjudicate` now owns every status/reason for this arm too; _measure
    # only decides WHEN it has enough evidence to call adjudicate.
    if not before and not before_collect:
        verdict = adjudicate.adjudicate(adjudicate.Measurements(
            pass2=pass2,
            targets=selection,
            before=before,
            after={},
            before_records=before_records,
            before_collect=[r.nodeid for r in before_collect],
            after_collect=[],
            pass1_f2p=pass1_f2p))
        out.update(status=verdict.status, reason=verdict.reason)
        out.update(verdict.fields)
        return out

    fail = _apply(container, workdir, code_patch, "code")
    if fail:
        out.update(status=fail.status, reason=fail.reason)
        return out

    try:
        after, _after_records, after_collect, _ = _pytest(
            container, workdir, targets, logs / f"{AFTER}.log", AFTER)
    except ValueError as exc:
        out.update(status="apparatus", reason=f"after report: {exc}"[:300])
        return out
    out["after_collect_errors"] = [r.nodeid for r in after_collect]

    # Collection errors were recorded and then ignored, which let them decide
    # verdicts silently. Under `--continue-on-collection-errors` a file that
    # imports on the before side and not on the after side does not FAIL -- its
    # tests simply cease to exist. Every previously-passing node in it then
    # vanishes, misses outcomes.diff's exact-swap rename rule, lands in
    # `broken`, and books `rejected:regression_broken` claiming those tests
    # "fail after the code patch", which is false: they were never run. The two
    # sides were not measured comparably, so NO comparison between them is
    # honest -- apparatus, ours, not a verdict about the commit.
    #
    # Only errors NEW to the after side count. A collection error present on
    # both sides is a constant of the environment: it removes the same nodes
    # from both maps and the diff stays symmetric.
    #
    # This arm now lives in adjudicate (its `new_collect` check), reached by
    # the single Measurements built below. _measure records the evidence
    # (`after_collect_errors`) above and decides nothing here.

    verdict = adjudicate.adjudicate(adjudicate.Measurements(
        pass2=pass2,
        targets=selection,
        before=before,
        after=after,
        before_records=before_records,
        before_collect=[r.nodeid for r in before_collect],
        after_collect=[r.nodeid for r in after_collect],
        pass1_f2p=pass1_f2p))
    out.update(status=verdict.status, reason=verdict.reason)
    out.update(verdict.fields)
    return out


def validate_quarter(quarter, limit, keep_images, force):
    reason = quarters.preflight()
    if reason:
        raise SystemExit(f"preflight refused: {reason}")

    if not record.CANDIDATES.exists():
        raise SystemExit(f"no candidate file at {record.CANDIDATES}; "
                         f"run `mine enumerate` first")
    all_c = [json.loads(l) for l in open(record.CANDIDATES, encoding="utf-8")
             if l.strip()]
    done = record.read_all(record.VALIDATED)
    queue = [c for c in all_c if c["quarter"] == quarter
             and (force or c["sha"] not in done or not record.is_done(done[c["sha"]]))]
    queue = queue[:limit]
    if not queue:
        print(f"nothing to do for {quarter}")
        return {}

    # build_quarter_image returns a QuarterImage, and `skip` is the difference
    # between "this quarter has nothing to mine" (a verdict) and "the build
    # broke" (apparatus). Collapsing the two is exactly the confusion the
    # namedtuple exists to prevent.
    img = quarters.build_quarter_image(record.REPO, quarter, record.LOGS)
    if img.tag is None:
        if img.skip:
            print(f"{quarter}: {img.reason}; nothing to mine here")
            return {}
        raise SystemExit(
            f"image build failed for {quarter}: {img.reason}; "
            f"see {record.LOGS / f'build-{quarter}.log'}")
    if not img.anchored:
        print(f"WARNING: {quarter} is NOT anchored -- the frozen export did "
              f"not run, so this image holds modern dependencies wearing the "
              f"quarter's name. Every record below carries anchored=false.")

    cid = quarters.start_container(img.tag, f"miner-{quarter.lower()}")
    if not cid:
        raise SystemExit(f"container would not start for {quarter}")

    err = quarters.install_reporter(cid)
    if err:
        quarters.stop_container(cid)
        raise SystemExit(f"{quarter}: {err}")

    counts = {}
    try:
        def write(rec):
            # The single point at which a record reaches disk, so that the
            # anchoring flag cannot be lost down some branch that built its
            # record by hand. See the module docstring.
            rec["anchored"] = img.anchored
            rec["anchor"] = img.anchor
            record.append(record.VALIDATED, rec)
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
            print(f"  {rec['sha'][:8]} {rec['status']} {rec.get('reason') or ''}")

        def attempt(cand, pass2, pass1_f2p=None):
            """Run one candidate; convert an unexpected raise into `error`.

            A miner bug is not a verdict about the commit either -- `error` is
            non-terminal in record.is_done, so the candidate is retried once
            the bug is fixed.
            """
            try:
                return validate_one(cid, cand, record.REPO, img.anchored,
                                    pass2=pass2, pass1_f2p=pass1_f2p)
            except ContainerLost:
                raise
            except Exception:
                return dict(cand, status="error", before_failed=None,
                            reason=traceback.format_exc()[-1500:])

        survivors = []
        try:
            for cand in queue:
                rec = attempt(cand, pass2=False)
                if rec["status"] == "pass1_ok":
                    survivors.append((cand, rec["f2p"]))
                else:
                    write(rec)
            for cand, pass1_f2p in survivors:
                write(attempt(cand, pass2=True, pass1_f2p=pass1_f2p))
        except ContainerLost as exc:
            # `error`, not `apparatus`. Both are our fault, but apparatus is
            # TERMINAL in record.is_done, so a container timeout would retire
            # a candidate that may be perfectly valid and never look at it
            # again. `error` was made non-terminal in Task 1 for exactly this:
            # infrastructure loss is retried once the infrastructure is fixed.
            write(dict(cand, status="error", before_failed=None,
                       reason=f"container lost: {exc}"))
            print(f"  stopping {quarter}: {exc}")
    finally:
        quarters.stop_container(cid)
        if not keep_images:
            quarters.remove_image(img.tag)
    return counts
