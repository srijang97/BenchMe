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
    each failing node's message and the collapsed map does not carry it.

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
    return outcomes.collapse(rep.tests), rep.tests, rep.collect, out


# Why _runnable_targets came back with nothing to run. THREE of these four are
# facts about US and one is a fact about the commit, and collapsing them was a
# live defect: `dac3c437` and `568509c0` in miner/out/validated.jsonl are
# terminally `rejected:unchanged` because their only test path lived under
# `tests/typechecking/`, i.e. because of OUR filter. candidates.py's own
# comment on NON_PYTEST_TEST_DIRS says that filter must never turn our defect
# into a verdict about the commit; this constant set is how that is enforced.
EMPTY_FILTERED = "filtered"          # ours: dropped by NON_PYTEST_TEST_DIRS
EMPTY_NOT_RUNNABLE = "not_runnable"  # ours: fixtures/conftest only, nothing to run
EMPTY_ABSENT = "absent"              # ours: not present, and not because it was deleted
EMPTY_DELETED = "deleted"            # the COMMIT deleted its test files

# Only EMPTY_DELETED is a verdict about the commit. Everything else -- and
# anything unrecognised, which is the point of testing membership rather than
# inequality -- is ours and books apparatus.
EMPTY_IS_A_VERDICT = frozenset({EMPTY_DELETED})


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


# The four things pass 2's measurement can say about pass 1's oracle. They map
# onto three DIFFERENT kinds of record, and keeping them apart is the whole
# point of the check:
#
#   PASS2_ERROR       our bug -- the check could not be made at all.
#   PASS2_APPARATUS   our tooling -- the oracle nodes were never measured.
#   PASS2_UNSTABLE    a verdict about the commit -- measured, did not flip.
#   PASS2_REPRODUCED  the oracle survives; `reproduced` is the intersection.
PASS2_ERROR = "error"
PASS2_APPARATUS = "apparatus"
PASS2_UNSTABLE = "unstable"
PASS2_REPRODUCED = "reproduced"

Pass2Check = namedtuple("Pass2Check", "kind never_measured reproduced")


def check_pass2_determinism(pass1_f2p, before, f2p_now):
    """Decide what pass 2's measurement says about pass 1's fail->pass set.

    Pure by construction -- dicts and lists in, a Pass2Check out, no container
    and no I/O -- because `_measure` cannot be tested without Docker and this
    decision is the part that must not regress. See miner/tests/test_runner.py.

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


def _labels_for(before_records, f2p):
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
        out.update(status="rejected:unchanged", reason="no test paths")
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
    else:
        found = _runnable_targets(container, workdir, tests)
        if found.err:
            out.update(status="apparatus", reason=found.err)
            return out
        targets = found.paths
        if not targets:
            # FOUR causes used to collapse into one `rejected:unchanged`, and
            # only one of them is a fact about the commit. Everything we did to
            # the path list -- the NON_PYTEST_TEST_DIRS filter, the
            # conftest/fixture drop, an unexplained absence -- is ours and
            # books apparatus. `dac3c437` and `568509c0` are already on disk as
            # terminal `rejected:unchanged` records for exactly this reason.
            # Membership, not inequality: an EMPTY_* value this code does not
            # recognise must fall to apparatus, never to a verdict.
            if found.why in EMPTY_IS_A_VERDICT:
                out.update(
                    status="rejected:unchanged",
                    reason=f"no runnable test file among the touched test "
                           f"paths after the test patch: {found.detail}")
            else:
                out.update(
                    status="apparatus",
                    reason=f"OUR path selection left pass 1 with no target "
                           f"({found.why}): {found.detail}"[:300])
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

    # PASS 1 ONLY. In pass 1 the pytest targets ARE this candidate's own
    # touched test files, so a before-side collection error means one of THOSE
    # files failed to import. Under `--continue-on-collection-errors` its tests
    # are not run and not reported -- they simply do not exist in `before`. The
    # oracle can therefore be absent through no fault of the commit, d["f2p"]
    # comes back empty and the candidate books `rejected:unchanged`: OUR
    # dependency or environment gap recorded as a terminal verdict about the
    # commit. Apparatus is the honest answer -- ours, and durable, since the
    # same image will fail the same import again.
    #
    # Placed after `before_collect_errors` is recorded, so the diagnostic
    # survives on the record, and before the code patch is applied, so a
    # candidate that is already dead does not pay for a second pytest run.
    #
    # NOT applied to pass 2, deliberately. Pass 2 runs the FULL suite, where
    # collection errors from dependency drift in an anchored image are endemic
    # and have nothing to do with the candidate (measured on 2025Q3); a blanket
    # rule there would terminally retire nearly every candidate. The correct
    # pass-2 predicate is narrower -- intersect the collection-error node ids
    # with the candidate's OWN target paths, so only an error in a file this
    # candidate depends on counts -- and it is deliberately left as follow-up
    # work rather than guessed at now. Pass 2 is not unguarded in the meantime:
    # `new_collect` below still catches errors NEW to the after side, and
    # check_pass2_determinism still books apparatus for any oracle node the
    # full-suite run did not measure, which is the shape a collection error
    # takes there.
    if not pass2 and before_collect:
        first = before_collect[0].nodeid
        out.update(
            status="apparatus",
            reason=f"{len(before_collect)} of this candidate's own touched "
                   f"test file(s) failed to collect on the before side, so "
                   f"their tests never ran and the oracle cannot be trusted "
                   f"to be absent for any reason but ours (first: "
                   f"{first})"[:300])
        return out

    # Checked HERE, before the code patch and the second pytest invocation. A
    # candidate with no before-side outcomes is already dead; running the full
    # after pass to reach the same conclusion just buys a second full pytest
    # run per dead candidate. The `if not after` guard below has to stay where
    # it is -- it cannot be known any earlier.
    if not before:
        out.update(status="apparatus",
                   reason="no test outcomes on the before side")
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

    # The after side needs the same guard. An empty after makes every f2p
    # comparison fail, so diff["f2p"] is empty and the next branch books
    # `rejected:unchanged`: apparatus wearing a verdict.
    if not after:
        out.update(status="apparatus",
                   reason="no test outcomes on the after side")
        return out

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
    new_collect = sorted({r.nodeid for r in after_collect}
                         - {r.nodeid for r in before_collect})
    if new_collect:
        out.update(
            status="apparatus",
            reason=f"{len(new_collect)} file(s) failed to collect after the "
                   f"code patch but not before it, so the two sides were not "
                   f"measured comparably and no regression verdict is honest "
                   f"(first: {new_collect[0]})"[:300])
        return out

    d = outcomes.diff(before, after)
    out["f2p"] = d["f2p"]
    out["p2p_count"] = len(d["p2p"])
    out["broken"] = d["broken"]
    out["renamed"] = d["renamed"]
    out["error_base"] = d["error_base"]
    out["skipped_after"] = d["skipped_after"]
    out["tests_seen"] = len(before)

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
    if pass2:
        check = check_pass2_determinism(pass1_f2p, before, d["f2p"])
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
            out.update(
                status="error",
                reason="miner bug: pass 2 ran with no pass-1 fail->pass set, "
                       "so the determinism check of decision 7 could not be "
                       "made; refusing to book a validated record without it")
            return out

        out["f2p_pass1"] = sorted(pass1_f2p)
        out["f2p_reproduced"] = check.reproduced

        # "Measured and did not flip" is not "not measured", and only the first
        # is a fact about the commit. A node missing from pass 2's before-run
        # status map, or present in it as SKIPPED, did not execute, so nothing
        # can be concluded about it: apparatus, which is ours and terminal.
        if check.kind == PASS2_APPARATUS:
            n_before = len(out.get("before_collect_errors") or [])
            n_after = len(out.get("after_collect_errors") or [])
            missing = check.never_measured
            out.update(
                status="apparatus",
                reason=f"{len(missing)} of {len(pass1_f2p)} pass-1 fail->pass "
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
            out["f2p"] = []
            return out

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
            out.update(
                status="rejected:unstable",
                reason=f"all {len(pass1_f2p)} pass-1 fail->pass test(s) were "
                       f"measured in the full-suite pass-2 run and none "
                       f"reproduced the fail->pass transition")
            # Pass 2's own raw f2p set is not an oracle here -- nothing in it
            # reproduced -- and leaving it in place lets a downstream reader
            # mistake it for one while `f2p_reproduced` is empty. It stays
            # recoverable from `failure_labels`, whose keys are that set, which
            # is why the labels are built here rather than left to the
            # qualifying path below.
            out["failure_labels"] = _labels_for(before_records, d["f2p"])
            out["f2p"] = []
            return out

        # Pass2Check.kind is CLOSED here. The three arms above have returned,
        # so only PASS2_REPRODUCED may continue -- and it must say so out loud.
        # Falling through implicitly would mean a fifth kind added later
        # reaches `validated` by default, i.e. an unrecognised value defaulting
        # to the qualifying outcome, which the project's global constraints
        # forbid. `error`, not apparatus: a kind this function does not
        # recognise is a miner bug, and `error` is non-terminal so the
        # candidate is retried once the bug is fixed.
        if check.kind != PASS2_REPRODUCED:
            out.update(
                status="error",
                reason=f"miner bug: unrecognised pass-2 determinism kind "
                       f"{check.kind!r}; refusing to book a validated record "
                       f"on a check outcome this code does not understand")
            return out

    if not d["f2p"]:
        # error_base is spelled out in the reason because it is the one
        # rejection the new contract still makes on failure kind, and it is
        # the number a future audit of decision 2 will need.
        detail = "no test went fail->pass"
        if d["error_base"]:
            detail += (f"; {len(d['error_base'])} test(s) went error->pass, "
                       f"which is not an admissible base negative")
        out.update(status="rejected:unchanged", reason=detail)
        return out

    out["failure_labels"] = _labels_for(before_records, d["f2p"])

    if pass2:
        # Every pass-1 oracle node was measured and at least one reproduced.
        # The oracle is the INTERSECTION. A test that only flips in one of the
        # two runs is not something we are willing to grade an agent on. No
        # `if reproduced:` guard: the branch above already returned on empty,
        # and a guard here would read as though an empty intersection could
        # still reach `validated`.
        # A copy, not the same list object as f2p_reproduced: two record fields
        # aliasing one list is a trap for any later code that edits either.
        out["f2p"] = list(check.reproduced)
        # failure_labels was built from the pass-2 f2p set a few lines up.
        # Narrowing the oracle without narrowing the labels would leave
        # report._composition counting labels for node ids that are not in
        # the capsule's oracle.
        out["failure_labels"] = {t: lbl
                                 for t, lbl in out["failure_labels"].items()
                                 if t in set(out["f2p"])}

    if pass2 and d["broken"]:
        # Reported as two numbers, not one. A node id that is ABSENT from the
        # after run did not fail -- it vanished, and "fail" is simply false
        # about it. The two have different causes (a genuine regression versus
        # a rename the exact-swap rule did not reconcile) and report._regressions
        # exists only because the recorded reason used to conflate them.
        vanished = [n for n in d["broken"] if n not in after]
        failed = [n for n in d["broken"] if n in after]
        out.update(
            status="rejected:regression_broken",
            reason=f"{len(failed)} previously-passing test(s) fail after the "
                   f"code patch and {len(vanished)} vanished from the after "
                   f"run (first: {d['broken'][0]})"[:300])
        return out

    out.update(status="validated" if pass2 else "pass1_ok", reason=None)
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
