"""Stage 2 orchestration: two passes over one quarter's candidates.

Pass 1 runs only the test files the commit touched -- cheap, and it eliminates
most candidates. Pass 2 runs the full suite on survivors only, to establish the
pass-to-pass set and catch a code patch that breaks something elsewhere.

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
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import metrics  # noqa: E402
import tierb  # noqa: E402

import quarters  # noqa: E402
import record  # noqa: E402
import validate  # noqa: E402

BEFORE, AFTER = "before", "after"

# pytest trims its short-summary lines to the terminal width and, when the
# detail will not fit, omits it entirely -- producing `FAILED nodeid` lines
# that validate.parse_failures cannot tell apart from a genuinely detail-less
# line, and now raises on. CI=1 makes _pytest.config.running_on_ci() true,
# which disables the trimming outright; a wide COLUMNS covers the same ground
# for any pytest that predates that check. Both are set: without them
# classification degrades silently and the yield numbers become meaningless.
PYTEST_ENV = {"COLUMNS": "200", "CI": "1"}

# pytest-pretty is in pydantic's own dev group, so it is installed in every
# quarter image and active by default. It REPLACES the "short test summary
# info" block with a rich table:
#
#       Summary of Failures
#   ┏━━━━━━━━┳━━━━━━━━━━┳ ...
#   │ test_x │ test_a   │ ...
#
# There is no `FAILED nodeid - detail` line left for validate.parse_failures
# to read, so it returns {} and every f2p node id falls to its
# "AssertionError" default -- which classify() calls `assertion`, the one
# class that QUALIFIES. A missing_api or structural base negative would be
# admitted as valid, silently, with nothing anywhere in the record or the log
# to show it. Measured in the 2025Q3 image; the outcome lines survive, so
# parse_outcomes still works and nothing else looks wrong.
#
# `-rfE` rather than `-rf`: validate.parse_failures reads pytest's ERROR
# short-summary lines too (collection and fixture errors), and those only
# appear with E requested. They cannot become a false verdict -- only f2p node
# ids are ever looked up in that mapping -- but their absence from the log
# hides the commonest explanation for a zero-outcome run.
PYTEST_EXTRA = ["-p", "no:pretty", "-rfE"]


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


def _pytest(container, workdir, targets, log_path, timeout=1800):
    """Run pytest on `targets` inside `workdir`; always write the full log.

    The checkout goes on PYTHONPATH because the image deliberately does NOT
    contain the project itself -- see quarters' module docstring.
    """
    env = " ".join(f"{k}={v}" for k, v in PYTEST_ENV.items())
    wd = shlex.quote(workdir)
    cmd = "cd {wd} && {env} PYTHONPATH={wd} {argv} {t} 2>&1".format(
        wd=wd, env=env,
        argv=" ".join([*tierb.PYTEST_ARGV, *PYTEST_EXTRA]),
        t=" ".join(shlex.quote(t) for t in targets))
    r = _guard(quarters.exec_in(container, ["sh", "-c", cmd], timeout=timeout),
               "pytest")
    out = r.stdout + r.stderr
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(log_path).write_text(f"$ {cmd}\n{out}", encoding="utf-8")
    return out


def _runnable_targets(container, workdir, tests):
    """The touched test paths pytest can actually be pointed at, that exist.

    `validate.split_paths` uses the deliberately broader `_belongs_to_test_side`
    (fixture data under tests/, a root conftest.py), which is right for
    deciding which side of the patch a path belongs on and wrong for deciding
    what to hand pytest: a JSON fixture or a conftest as the only target
    collects nothing, pytest exits with no outcomes, and a perfectly good
    candidate is booked as apparatus. Same for a test file the commit DELETES
    -- it is gone once the test patch applies. Filtering here keeps both cases
    out of the apparatus column.
    """
    wanted = [t for t in tests
              if metrics.is_test_file(t)
              and PurePosixPath(t).name != "conftest.py"]
    if not wanted:
        return []
    script = "cd {wd} && for p in {ps}; do [ -e \"$p\" ] && echo \"$p\"; done".format(
        wd=shlex.quote(workdir), ps=" ".join(shlex.quote(p) for p in wanted))
    r = _guard(quarters.exec_in(container, ["sh", "-c", script]), "target probe")
    present = set(r.stdout.split())
    return [t for t in wanted if t in present]


def validate_one(container, cand, repo, anchored, pass2=False):
    """Returns a record dict. Never raises for a candidate-level problem.

    Raises ContainerLost when the container itself is gone; that is a run-level
    problem, not a candidate-level one.
    """
    sha, parent = cand["sha"], cand["parent"]
    out = dict(cand)
    out["anchored"] = anchored
    out["pass"] = 2 if pass2 else 1
    logs = record.LOGS / sha[:12]
    workdir = f"/work/{sha[:12]}"

    tests, code = validate.split_paths(cand["files"])
    if not tests:
        out.update(status="rejected:unchanged", reason="no test paths")
        return out

    err = _checkout(container, parent, workdir)
    if err:
        out.update(status="apparatus", reason=err)
        return out

    # validate.make_patch raises when a non-empty pathspec yields an empty
    # diff, and parse_failures raises on a truncated FAILED line. Both mean
    # OUR capture is wrong, so both are apparatus -- never a verdict about the
    # commit. Anything else escaping is a miner bug and is booked as `error`
    # by validate_quarter.
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
        targets = _runnable_targets(container, workdir, tests)
        if not targets:
            out.update(status="rejected:unchanged",
                       reason="no runnable test file among the touched test "
                              "paths after the test patch")
            return out

    before_out = _pytest(container, workdir, targets, logs / f"{BEFORE}.log")
    before = tierb.parse_outcomes(before_out)
    try:
        failures = validate.parse_failures(before_out)
    except RuntimeError as exc:
        out.update(status="apparatus", reason=f"parse_failures: {exc}"[:300])
        return out

    err = _apply(container, workdir, code_patch, "code")
    if err:
        out.update(status="apparatus", reason=err)
        return out

    after_out = _pytest(container, workdir, targets, logs / f"{AFTER}.log")
    after = tierb.parse_outcomes(after_out)

    quarters.exec_in(container, ["rm", "-rf", workdir])

    diff = validate.diff_outcomes(before, after)
    out["f2p"] = diff["f2p"]
    out["p2p_count"] = len(diff["p2p"])
    out["broken"] = diff["broken"]
    out["tests_seen"] = len(before)

    if not before:
        out.update(status="apparatus",
                   reason="no test outcomes parsed on the before side")
        return out
    if not diff["f2p"]:
        out.update(status="rejected:unchanged",
                   reason="no test went fail->pass")
        return out

    classes = {t: validate.classify(failures.get(t, "AssertionError"))
               for t in diff["f2p"]}
    out["failure_classes"] = classes
    if not any(c == "assertion" for c in classes.values()):
        dominant = sorted(classes.values())[0]
        out.update(status=f"rejected:{dominant.split(':')[0]}",
                   reason=f"no assertion-class base negative; saw {sorted(set(classes.values()))}")
        return out

    if pass2 and diff["broken"]:
        out.update(status="rejected:regression_broken",
                   reason=f"{len(diff['broken'])} previously-passing tests fail after the code patch")
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

        def attempt(cand, pass2):
            """Run one candidate; convert an unexpected raise into `error`.

            A miner bug is not a verdict about the commit either -- `error` is
            non-terminal in record.is_done, so the candidate is retried once
            the bug is fixed.
            """
            try:
                return validate_one(cid, cand, record.REPO, img.anchored,
                                    pass2=pass2)
            except ContainerLost:
                raise
            except Exception:
                return dict(cand, status="error",
                            reason=traceback.format_exc()[-1500:])

        survivors = []
        try:
            for cand in queue:
                rec = attempt(cand, pass2=False)
                if rec["status"] == "pass1_ok":
                    survivors.append(cand)
                else:
                    write(rec)
            for cand in survivors:
                write(attempt(cand, pass2=True))
        except ContainerLost as exc:
            write(dict(cand, status="apparatus", reason=str(exc)))
            print(f"  stopping {quarter}: {exc}")
    finally:
        quarters.stop_container(cid)
        if not keep_images:
            quarters.remove_image(img.tag)
    return counts
