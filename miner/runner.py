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
  apparatus           a verdict about US -- the patch would not apply, the
                      container died, nothing parsed, validate.py raised.

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


def _checkout(container, sha, workdir):
    r = _guard(quarters.exec_in(container, ["git", "clone", "--quiet",
                                            "--no-checkout", "/repo", workdir]),
               "git clone")
    if r.returncode != 0:
        return f"clone failed: {(r.stdout + r.stderr)[:200]}"
    r = _guard(quarters.exec_in(
        container, ["git", "-C", workdir, "checkout", "--quiet", sha]),
        "git checkout")
    if r.returncode != 0:
        return f"checkout failed: {(r.stdout + r.stderr)[:200]}"
    return None


def _apply(container, workdir, patch_text, label):
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
        return f"could not write {label} patch"
    r = _guard(quarters.exec_in(
        container, ["git", "-C", workdir, "apply", "--3way", path]),
        f"git apply ({label})")
    if r.returncode != 0:
        return f"{label} patch would not apply: {(r.stdout + r.stderr)[:200]}"
    return None


def _pytest(container, workdir, targets, log_path, phase, timeout=1800):
    """Run pytest on `targets`; return
    (status_map, records, collect_errors, output).

    `status_map` is node id -> one of outcomes.FAILURE/ERROR/PASSED/SKIPPED.
    `records` is the raw list of outcomes.Record, kept because labelling needs
    each failing node's message and the collapsed map does not carry it.
    Raises ValueError (from outcomes.parse_report) when the report is
    malformed OR truncated -- the latter meaning the plugin never wrote its
    sessionfinish terminator, so the session did not run to the end. The
    caller books either as apparatus.

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
    tests, collect = outcomes.parse_report(rr.stdout)
    return outcomes.collapse(tests), tests, collect, out


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

    Returns (targets, err). `err` is not None when the PROBE ITSELF failed:
    an unchecked probe returns an empty set on failure, which is
    indistinguishable from "the commit touches no runnable test" and lands as
    `rejected:unchanged` -- the same shape as the `_numstat` defect fixed in
    Task 2. The loop is written with `if ... then` rather than `[ -e p ] && ...`
    precisely so the shell's exit status reports the probe, not whether the
    last path happened to exist.
    """
    wanted = [t for t in tests
              if metrics.is_test_file(t)
              and PurePosixPath(t).name != "conftest.py"
              and not candidates.is_non_pytest_test(record.REPO.name, t)]
    if not wanted:
        return [], None
    script = ("cd {wd} || exit 3; "
              "for p in {ps}; do if [ -e \"$p\" ]; then echo \"$p\"; fi; done").format(
        wd=shlex.quote(workdir), ps=" ".join(shlex.quote(p) for p in wanted))
    r = _guard(quarters.exec_in(container, ["sh", "-c", script]), "target probe")
    if r.returncode != 0:
        return None, ("target probe failed (rc={}): {}".format(
            r.returncode, (r.stdout + r.stderr)[:200]))
    present = set(r.stdout.split())
    return [t for t in wanted if t in present], None


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

    `pass1_f2p` is pass 1's oracle, `before` is pass 2's before-run status map
    (only membership is read), `f2p_now` is pass 2's own fail->pass list.

    The order of the three tests is the contract:

      1. no `pass1_f2p` at all -> PASS2_ERROR. A programming error, reported as
         itself rather than smuggled into apparatus.
      2. an oracle node absent from `before` -> PASS2_APPARATUS. It was never
         measured, so nothing can be concluded about it -- "measured and did
         not flip" is a fact about the commit, "never measured" is a fact about
         us. Checked before reproduction so a never-measured node cannot fall
         through into it.
      3. every node measured, none flipped -> PASS2_UNSTABLE; otherwise
         PASS2_REPRODUCED with the intersection.
    """
    if not pass1_f2p:
        return Pass2Check(PASS2_ERROR, [], [])
    never_measured = sorted(t for t in pass1_f2p if t not in before)
    if never_measured:
        return Pass2Check(PASS2_APPARATUS, never_measured, [])
    now = set(f2p_now)
    reproduced = sorted(t for t in pass1_f2p if t in now)
    if not reproduced:
        return Pass2Check(PASS2_UNSTABLE, [], [])
    return Pass2Check(PASS2_REPRODUCED, [], reproduced)


def _measure(container, cand, repo, out, workdir, pass2, pass1_f2p=None):
    """The body of validate_one, minus the workdir lifetime."""
    sha, parent = cand["sha"], cand["parent"]
    logs = record.LOGS / sha[:12]

    tests, code = validate.split_paths(cand["files"])
    if not tests:
        out.update(status="rejected:unchanged", reason="no test paths")
        return out

    err = _checkout(container, parent, workdir)
    if err:
        out.update(status="apparatus", reason=err)
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

    err = _apply(container, workdir, test_patch, "test")
    if err:
        out.update(status="apparatus", reason=err)
        return out

    if pass2:
        targets = ["tests"]
    else:
        targets, probe_err = _runnable_targets(container, workdir, tests)
        if probe_err:
            out.update(status="apparatus", reason=probe_err)
            return out
        if not targets:
            out.update(status="rejected:unchanged",
                       reason="no runnable test file among the touched test "
                              "paths after the test patch")
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

    # Checked HERE, before the code patch and the second pytest invocation. A
    # candidate with no before-side outcomes is already dead; running the full
    # after pass to reach the same conclusion just buys a second full pytest
    # run per dead candidate. The `if not after` guard below has to stay where
    # it is -- it cannot be known any earlier.
    if not before:
        out.update(status="apparatus",
                   reason="no test outcomes on the before side")
        return out

    err = _apply(container, workdir, code_patch, "code")
    if err:
        out.update(status="apparatus", reason=err)
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
    # Both pass-2 checks are made BEFORE the `if not d["f2p"]` return below.
    # `--continue-on-collection-errors` means a collection error anywhere in
    # the full suite can drop pass-1's oracle nodes from pass 2's results, and
    # when it drops ALL of them d["f2p"] is empty and that return would book
    # `rejected:unchanged`: our tooling's failure wearing a verdict about the
    # commit, which is the precise failure class this redesign exists to
    # eliminate. Round 1 closed the partial case; this closes the total one.
    #
    # Pass 1 carries no pass1_f2p and never enters this block, so it still
    # books `rejected:unchanged` when nothing goes fail->pass -- for pass 1
    # that is a genuine verdict about the commit and is correct.
    #
    # The check is computed ONCE, here, and the unstable arm is branched on
    # again further down, after labelling.
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

        # "Measured and did not flip" is not "never measured", and only the
        # first is a fact about the commit. Absence from pass 2's before-run
        # status map means the node was never measured, so nothing can be
        # concluded about it: apparatus, which is ours and terminal.
        if check.kind == PASS2_APPARATUS:
            n_before = len(out.get("before_collect_errors") or [])
            n_after = len(out.get("after_collect_errors") or [])
            missing = check.never_measured
            out.update(
                status="apparatus",
                reason=f"{len(missing)} of {len(pass1_f2p)} pass-1 fail->pass "
                       f"test(s) were never measured in pass 2, so the "
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

    # LABEL, never gate. Round 1 required an assertion-class base negative;
    # round 2 retired that rule because fail-to-pass against the genuine
    # upstream fix already establishes the failure was caused by the missing
    # fix. A node id with no reporter message still gets a label
    # ("unlabelled") rather than being rejected or defaulted to a qualifying
    # class -- see outcomes.label.
    f2p_set = set(d["f2p"])
    messages = {r.nodeid: r.message for r in before_records
                if r.nodeid in f2p_set}
    out["failure_labels"] = {t: outcomes.label(messages.get(t))
                             for t in d["f2p"]}

    if pass2:
        # Decision 7: the transition must reproduce. Pass 2 is an independent
        # measurement -- fresh clone, fresh patch, full-suite selection rather
        # than the touched files -- so an f2p that appears in pass 1 and not
        # here is either flaky or selection-dependent. Kimi's point in round
        # 2: flakiness, not taxonomy, is the plausible mechanism by which a
        # test "passes for unrelated reasons".
        #
        # `check` was computed above the `rejected:unchanged` return, and the
        # error and apparatus arms already returned there. Only the two
        # verdicts about the COMMIT are left to make here, after labelling.
        if check.kind == PASS2_UNSTABLE:
            out.update(
                status="rejected:unstable",
                reason=f"all {len(pass1_f2p)} pass-1 fail->pass test(s) were "
                       f"measured in the full-suite pass-2 run and none "
                       f"reproduced the fail->pass transition")
            # Pass 2's own raw f2p set is not an oracle here -- nothing in it
            # reproduced -- and leaving it in place lets a downstream reader
            # mistake it for one while `f2p_reproduced` is empty. It stays
            # recoverable from `failure_labels`, whose keys are that set.
            out["f2p"] = []
            return out
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
        out.update(status="rejected:regression_broken",
                   reason=f"{len(d['broken'])} previously-passing tests fail "
                          f"after the code patch")
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
