"""Tier B: reuse each repo's own shipped environment definition, then measure.

Never synthesises an environment. Descends a ladder and records which rung
worked; the rung is itself the qualification signal.
"""
import io
import os
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

BASE_IMAGE = "python:3.12-slim"

# Marks a container run that never produced a verdict of its own.
TIMEOUT_RETURNCODE = -9

# Non-root by default. See run_in for why root is not a neutral choice.
DEFAULT_CONTAINER_USER = "1000:1000"

RUNGS = {
    1: "devcontainer.json",
    2: "Dockerfile in repo",
    3: "CI workflow setup steps",
    4: "pyproject + lockfile via uv",
}


def detect_rung(repo, tracked):
    names = {PurePosixPath(t).name: t for t in tracked}
    if "devcontainer.json" in names:
        return 1, names["devcontainer.json"]
    if "Dockerfile" in names:
        return 2, names["Dockerfile"]
    if any(t.startswith(".github/workflows") for t in tracked):
        return 3, next(t for t in tracked if t.startswith(".github/workflows"))
    if "pyproject.toml" in names:
        return 4, names["pyproject.toml"]
    return 0, ""


LOCKED = "uv-export-locked"
LOCKED_ALL = "uv-locked-all-groups+extras"
LOCKED_EXTRAS = "uv-locked-default-groups+extras"
LOCKED_DEFAULT = "uv-locked-default-groups"
RESOLVED = "uv-resolved"
REPO_DOCKERFILE = "repo-dockerfile"

# The lock is honoured by EXPORTING it and installing into the system
# interpreter, not by `uv sync`. `uv sync` materialises `/repo/.venv`, and
# `run_in` bind-mounts the host repo over `/repo` at measurement time, which
# replaces the whole directory and takes that venv with it. The suite would
# then run against a bare interpreter. Exporting to the system site-packages
# puts the environment outside the mount point, where it survives.
_EXPORT = "uv export --frozen --no-hashes --no-emit-project"

# Three genuine strategies, tried in order, each recorded distinctly.
#
# `--all-extras` is not optional polish: extras are the PACKAGE's own declared
# functionality and its tests exercise them. pydantic keeps `email-validator`
# in `[project.optional-dependencies]`, which `--all-groups` does NOT cover,
# and four of its tests failed on `No module named 'email_validator'` purely
# because of that gap. pydantic's own Makefile installs
# `--all-groups --all-packages --all-extras`, so this matches what the project
# tells its developers to run.
#
# The fallbacks exist because `--all-groups` FAILS outright on a project that
# declares conflicting groups -- measured on urllib3: `Groups 'dev' and
# 'dev-min-pyopenssl' are incompatible`. Without them such a repo books a
# `gated:B1` build failure, which would be a false elimination.
_LOCKED_INSTALL = f"""RUN mkdir -p /opt/screener \
 && ( {_EXPORT} --all-groups --all-extras -o /tmp/requirements.txt \
      && echo all-groups+extras > /opt/screener/export-mode ) \
 || ( {_EXPORT} --all-extras -o /tmp/requirements.txt \
      && echo default-groups+extras > /opt/screener/export-mode ) \
 || ( {_EXPORT} -o /tmp/requirements.txt \
      && echo default-groups > /opt/screener/export-mode )
RUN uv pip install --system -r /tmp/requirements.txt \
 && uv pip install --system --no-deps -e .
"""

# Two real strategies, not a swallow: editable install, else a plain install.
# There is deliberately no trailing `|| true` -- see _dockerfile_for_rung4.
_RESOLVED_INSTALL = """RUN uv pip install --system -e . \\
 || uv pip install --system .
"""


def _install_strategy(repo):
    """Which install path the generated image will use, for the record.

    G7 admits a candidate on the strength of a lockfile, justified by
    determinism. If the build then resolved fresh from PyPI the gate and the
    build would disagree, so the two must be reported together.
    """
    return LOCKED if (Path(repo) / "uv.lock").is_file() else RESOLVED


def _dockerfile_for_rung4(repo):
    """Generic uv image that honours the repo's lockfile when it ships one.

    Two invariants:

    1. A `uv.lock` is USED, not merely counted by G7. Otherwise the gate
       admits a repo for determinism the build then throws away.
    2. Nothing is swallowed. A build that cannot install the package or
       pytest must FAIL, so the caller records `gated:B1` -- an honest
       "cannot containerise". A green build into an empty environment would
       resurface later as "suite not green" and be misread as a property of
       the repository rather than of the screener.

    The closing `python -m pytest --version` is the assertion that makes
    "the build went green" mean "the environment is usable".
    """
    install = (_LOCKED_INSTALL if _install_strategy(repo) == LOCKED
               else _RESOLVED_INSTALL)
    # `less` is not decoration. python:3.12-slim omits it, but it is present
    # in every ordinary Linux dev image -- including the
    # mcr.microsoft.com/devcontainers/python:3 that click's own devcontainer
    # names. Without it, suites that shell out to a pager fail for a reason
    # that belongs to this template, not to the repository, and B2 would read
    # that as "suite not green at HEAD".
    return f"""FROM {BASE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends git curl \\
    less build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /repo
COPY . /repo
{install}# Only touched when the lock did not already supply pytest, so a locked
# environment stays exactly as locked.
RUN python -c "import pytest" || uv pip install --system pytest
RUN python -m pytest --version
"""


def _as_text(value):
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def host_path(p):
    """Docker Desktop wants forward slashes: C:/Users/... not C:\\Users\\...

    A backslashed source in `-v SRC:/repo` is fragile because the drive-letter
    colon collides with the separator. Forward slashes are the reliable form.
    """
    return str(Path(p).resolve()).replace("\\", "/")


def docker_env():
    """Defensive: stop MSYS/Git Bash rewriting container-side paths like /repo."""
    return dict(os.environ, MSYS_NO_PATHCONV="1", MSYS2_ARG_CONV_EXCL="*")


def build_image(repo, name, rung, log_dir, record=None):
    """Build the measurement image. Returns the tag, or None on any failure.

    A failed build is a RESULT (`gated:B1`), never an exception: nothing here
    raises, including a timeout or a missing docker binary. The full build log
    is written either way.

    `record`, when given, receives `install_strategy` so the caller can report
    whether this repo's environment was locked or resolved.
    """
    repo = Path(repo)
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    tag = f"benchme-screener/{name}:tierb"

    if rung == 2:
        dockerfile = next(
            (p for p in repo.rglob("Dockerfile") if p.is_file()), None)
        if dockerfile is None:
            _write_build_log(log_dir, "", "no Dockerfile found on disk")
            return None
        strategy = REPO_DOCKERFILE
        cmd = ["docker", "build", "-f", host_path(dockerfile), "-t", tag,
               host_path(repo)]
    else:
        # Rungs 1, 3 and 4 all end up here: write a generic uv image and let
        # the repo's own pins do the work. Record the rung that was DETECTED,
        # not the mechanism used to build.
        #
        # The generated Dockerfile lives in log_dir, NOT in the repo. Writing
        # it into the clone would leave an untracked file inside the artefact
        # under measurement; `docker build -f` accepts a Dockerfile outside
        # the build context, so there is no reason to pollute it.
        generated = log_dir / "Dockerfile.screener"
        generated.write_text(_dockerfile_for_rung4(repo), encoding="utf-8")
        strategy = _install_strategy(repo)
        cmd = ["docker", "build", "-f", host_path(generated), "-t", tag,
               host_path(repo)]

    if record is not None:
        record["install_strategy"] = strategy

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              env=docker_env(), encoding="utf-8",
                              errors="replace", timeout=3600)
    except subprocess.TimeoutExpired as exc:
        _write_build_log(log_dir, exc.stdout, "TIMEOUT after 3600s")
        return None
    except OSError as exc:
        _write_build_log(log_dir, "", f"BUILD NOT STARTED: {exc}")
        return None
    _write_build_log(log_dir, proc.stdout, proc.stderr)
    if proc.returncode != 0:
        return None
    if record is not None and strategy == LOCKED:
        record["install_strategy"] = _export_mode(tag)
    return tag


def _export_mode(tag):
    """Which uv export the build actually used, read back out of the image.

    Decided inside the container -- `--all-groups` installs everything the
    repo declares, which is the faithful reconstruction, but it FAILS on a
    project declaring conflicting groups (measured on urllib3: `Groups `dev`
    and `dev-min-pyopenssl` are incompatible`). Falling back to the default
    groups keeps such a repo measurable instead of booking it `gated:B1`.
    Read from a marker file rather than the build log, which goes silent on
    a cached layer.
    """
    try:
        probe = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", tag,
             "cat", "/opt/screener/export-mode"],
            capture_output=True, text=True, env=docker_env(), encoding="utf-8",
            errors="replace", timeout=300)
    except (subprocess.TimeoutExpired, OSError):
        return LOCKED
    mode = probe.stdout.strip()
    return {"all-groups+extras": LOCKED_ALL,
            "default-groups+extras": LOCKED_EXTRAS,
            "default-groups": LOCKED_DEFAULT}.get(mode, LOCKED)


def _write_build_log(log_dir, stdout, stderr):
    def _text(v):
        if v is None:
            return ""
        return v.decode("utf-8", "replace") if isinstance(v, bytes) else v

    with open(Path(log_dir) / "docker-build.log", "w", encoding="utf-8") as fh:
        fh.write(_text(stdout) + "\n" + _text(stderr))


# Caches, not build products. Restoring these would import one run's state
# into the next and corrupt the flake measurement.
_CACHE_MARKERS = ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")


def sync_generated(image, repo, log_dir, timeout=600):
    """Restore install-time generated source files into the host clone.

    `run_in` bind-mounts the host repo over `/repo`, which REPLACES whatever
    the build wrote there. Any project that generates a source file during
    install therefore has that file deleted out from under it at measurement
    time. Measured on urllib3: hatch-vcs writes `src/urllib3/_version.py`
    (gitignored) during `pip install -e .`; `import urllib3` succeeds inside
    the image and fails the moment the mount is applied, so pytest aborted
    before collecting a single test and the repo booked `gated:B2`.

    Only files that are gitignored, absent from the host clone, and not
    caches are copied. Gitignored means `git status` in the clone stays
    clean, so the artefact under measurement is still not polluted.

    Returns the list of restored paths.
    """
    repo = Path(repo)
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        listing = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", image, "sh", "-c",
             "git config --global --add safe.directory /repo >/dev/null 2>&1; "
             "cd /repo && git ls-files --others --ignored --exclude-standard"],
            capture_output=True, text=True, env=docker_env(),
            encoding="utf-8", errors="replace", timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        with open(log_dir / "sync-generated.log", "w", encoding="utf-8") as fh:
            fh.write(f"listing failed, nothing restored: {exc}")
        return []
    wanted = [ln.strip() for ln in listing.stdout.splitlines()
              if ln.strip()
              and not any(m in ln for m in _CACHE_MARKERS)
              and not ln.strip().endswith(".pyc")
              and not (repo / ln.strip()).exists()]
    if not wanted:
        return []
    # The file list goes over stdin (`tar -T -`), never on the command line.
    # pydantic generates enough artefacts to blow the Windows command-length
    # limit outright: `FileNotFoundError: [WinError 206] The filename or
    # extension is too long`.
    try:
        tar = subprocess.run(
            ["docker", "run", "--rm", "-i", "--network", "none", image,
             "tar", "-cf", "-", "-C", "/repo", "-T", "-"],
            input="\n".join(wanted).encode("utf-8"),
            capture_output=True, env=docker_env(), timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        with open(log_dir / "sync-generated.log", "w", encoding="utf-8") as fh:
            fh.write(f"tar failed, nothing restored: {exc}")
        return []
    if tar.returncode != 0:
        with open(log_dir / "sync-generated.log", "w", encoding="utf-8") as fh:
            fh.write(tar.stderr.decode("utf-8", "replace"))
        return []
    with tarfile.open(fileobj=io.BytesIO(tar.stdout)) as tf:
        tf.extractall(repo, filter="data")
    with open(log_dir / "sync-generated.log", "w", encoding="utf-8") as fh:
        fh.write("restored from image into host clone:\n" + "\n".join(wanted))
    return wanted


def run_in(image, repo, argv, network, log_path, timeout=3600,
           user=DEFAULT_CONTAINER_USER):
    """Run argv in the image with the repo bind-mounted at /repo.

    Runs as a NON-ROOT uid by default. Root is not a neutral choice: it
    bypasses Unix permission bits, so it manufactures false failures on tests
    that assert a permission is denied -- measured on starlette, where
    test_staticfiles_with_invalid_dir_permissions_returns_401 got 200 instead
    of 401 -- and would equally mask genuine permission bugs elsewhere. It is
    wrong in both directions, and CI does not normally run as root.

    HOME is redirected because a bare uid has no home directory in the image:
    `docker run --user 1000:1000` leaves HOME=/ , which is not writable, and
    anything wanting a cache (uv, pip, pytest) fails there. /tmp is writable
    by any uid. The bind-mounted repo itself IS writable to a non-root uid on
    Docker Desktop, so __pycache__ and .pytest_cache still land normally --
    verified before this was adopted.
    """
    cmd = ["docker", "run", "--rm", "-v", f"{host_path(repo)}:/repo",
           "-w", "/repo"]
    if user:
        cmd += ["--user", user,
                "-e", "HOME=/tmp",
                "-e", "XDG_CACHE_HOME=/tmp/.cache",
                # Fallout of running non-root: the bind-mounted repo is not
                # owned by this uid, so git refuses it with `fatal: detected
                # dubious ownership in repository at '/repo'` and every test
                # that shells out to git fails. Measured on pydantic, whose
                # test_version_info runs `git rev-parse --short HEAD` and
                # died with exit 128. Declared via GIT_CONFIG_* env vars
                # rather than a config file because a bare uid has no
                # writable HOME to hold one.
                "-e", "GIT_CONFIG_COUNT=1",
                "-e", "GIT_CONFIG_KEY_0=safe.directory",
                "-e", "GIT_CONFIG_VALUE_0=*"]
    if not network:
        cmd += ["--network", "none"]
    cmd += [image, *argv]
    # A hung or unstartable container is a RESULT, not a crash. urllib3's
    # suite finishes in ~63s and then leaves a non-daemon thread alive, so
    # PID 1 never returns and `docker run` blocks until the timeout; letting
    # TimeoutExpired escape would abort the whole sweep and leave the repo
    # unrecorded, so the resume path would retry and re-abort. Callers get a
    # CompletedProcess with a non-zero returncode and the reason on stderr.
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              env=docker_env(), encoding="utf-8",
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(
            cmd, TIMEOUT_RETURNCODE, _as_text(exc.stdout),
            f"SCREENER: container timed out after {timeout}s")
    except OSError as exc:
        proc = subprocess.CompletedProcess(
            cmd, TIMEOUT_RETURNCODE, "", f"SCREENER: docker run failed: {exc}")
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc


# The brief specified `\S+::\S+`, which cannot match a parametrized nodeid
# containing a space -- `test_echo_via_pager[test0- less]` and its 372 kin.
# Against click that regex saw 1604 of 1977 outcomes and only 8 of 24
# failures, silently shrinking both the flake denominator and the failure
# set. `\S+::.*?` anchored on the outcome word recovers exactly the 1977
# pytest itself reports.
OUTCOME = re.compile(
    r"^(?P<nodeid>\S+::.*?)\s+(?P<outcome>PASSED|FAILED|ERROR|SKIPPED)\b",
    re.M)

# `-v` and `-q` are ADDITIVE in pytest: together they cancel to verbosity 0,
# which prints progress dots instead of per-test outcome lines. The brief
# passed both, so parse_outcomes returned {} -- test_count 0, head_green
# vacuously True, flake_rate 1.0 and a `gated:B3` false elimination on a
# suite that had in fact run. `-q` is dropped deliberately; do not restore it.
PYTEST_ARGV = ["python", "-m", "pytest", "-v", "-p", "no:randomly", "--tb=no"]


def parse_outcomes(stdout):
    return {m.group("nodeid"): m.group("outcome")
            for m in OUTCOME.finditer(stdout)}


def _collection_error(output, limit=400):
    """The line that explains a zero-test run, for the gate ledger.

    Without it the ledger says "suite not green at HEAD" and gives the reader
    nothing to act on, when the real cause is usually a single ImportError.
    """
    interesting = [ln.strip() for ln in output.splitlines()
                   if ln.startswith(("E   ", "ImportError", "ERROR"))]
    return " | ".join(interesting)[:limit] if interesting else output[-limit:].strip()


def measure(image, repo, log_dir, runs=5, user=DEFAULT_CONTAINER_USER,
            skips=()):
    """Five sealed suite runs, one networked run, and targeted-test latency."""
    import time

    log_dir = Path(log_dir)
    per_run = []
    durations = []
    returncodes = []
    first_output = ""
    for i in range(runs):
        started = time.monotonic()
        proc = run_in(image, repo, PYTEST_ARGV, network=False,
                      log_path=log_dir / f"suite-{i}.log", user=user)
        durations.append(time.monotonic() - started)
        per_run.append(parse_outcomes(proc.stdout))
        # Recorded for diagnosis: run_in returns TIMEOUT_RETURNCODE rather than
        # raising when a container hangs, so a dead run is visible here.
        returncodes.append(proc.returncode)
        if i == 0:
            first_output = f"{proc.stdout}\n{proc.stderr}"

    # A run that produced no outcomes, or wildly fewer than its siblings, did
    # not measure anything -- a dead container, a docker hiccup, or a timeout.
    # Treated as APPARATUS error, never as flakiness. Left unchecked it is a
    # false `gated:B3`: the empty run contributes no failures so the
    # deterministic intersection stays empty and B2 passes, then every id
    # differs across runs and flake_rate goes to ~1.0. That is the same shape
    # as the `-v -q` defect that once reported a clean suite as 100% flaky.
    counts = [len(r) for r in per_run]
    median = sorted(counts)[len(counts) // 2] if counts else 0
    bad_runs = [i for i, c in enumerate(counts)
                if c == 0 or (median and c < median * 0.5)]
    apparatus_error = ""
    if bad_runs and median:
        apparatus_error = (
            f"sealed runs {bad_runs} produced {[counts[i] for i in bad_runs]} "
            f"outcomes against a median of {median} "
            f"(returncodes {[returncodes[i] for i in bad_runs]}); "
            f"the container did not measure the suite")
    elif counts and not median:
        apparatus_error = ("no sealed run produced any outcome; "
                           "the suite never ran")

    all_ids = set().union(*per_run) if per_run else set()
    flaky = [nid for nid in all_ids
             if len({run.get(nid) for run in per_run}) > 1]
    baseline = per_run[0] if per_run else {}

    # B2 is DETERMINISTIC failure only: a test counts as a head failure when
    # it fails in EVERY sealed run. The suite is run five times precisely to
    # characterise flakiness, so deciding green/not-green from per_run[0]
    # threw four fifths of the evidence away and made the verdict depend on
    # which run happened to be first. Measured on urllib3: its HTTP/2 probe
    # test fails in runs 0-3 and passes in run 4, which produced `gated:B2`
    # on a coin flip while B3 -- the gate that exists for exactly this --
    # passed it at 0.153%.
    #
    # Intermittent failures are reported separately rather than folded in.
    # They are flakiness, they are already priced by `flake_rate` against
    # B3's 0.5% threshold, and B2 must not double-count them.
    failing = [{nid for nid, o in run.items() if o in ("FAILED", "ERROR")}
               for run in per_run]
    deterministic = set.intersection(*failing) if failing else set()
    intermittent = (set.union(*failing) - deterministic) if failing else set()

    # Recorded skip list, per spec gate B2 ("modulo a recorded skip list").
    # A skip removes a test from the B2 failure set and nothing else: it does
    # not touch flake_rate, and it is surfaced in the record and the report so
    # a skipped test is never silently invisible. A configured skip matching
    # no test that actually ran is reported as STALE rather than ignored --
    # a stale skip is how a real failure gets hidden later.
    skip_ids = {s["test"] for s in skips}
    skips_matched = skip_ids & all_ids
    stale_skips = sorted(skip_ids - all_ids)
    sealed_failures = deterministic - skip_ids

    net_proc = run_in(image, repo, PYTEST_ARGV, network=True,
                      log_path=log_dir / "suite-networked.log", user=user)
    net_outcomes = parse_outcomes(net_proc.stdout)
    net_failures = {nid for nid, o in net_outcomes.items()
                    if o in ("FAILED", "ERROR")}
    # Failing sealed but passing networked: these are network-dependent, not
    # agent mistakes. The runner denies egress by design, so without this diff
    # they would be misattributed later.
    #
    # Uses the DETERMINISTIC failure set, which also fixes a contamination
    # this diff had while it was based on run 0: a flaky test that happened
    # to fail sealed and pass networked was indistinguishable from a genuine
    # network dependency. Measured on urllib3, whose entire reported
    # `net_dependent_tests` set was a subset of `flaky_tests`. B4 acts on
    # this set, so the confusion was a live false-signal path.
    # CRITICAL: these are subtracted from the B2 failure set below.
    # Previously `head_green` required `sealed_failures` to be empty while
    # `net_dependent` was derived FROM `sealed_failures`, so B4 was only ever
    # reached when its own input was provably empty -- it could neither
    # eliminate nor rescue anything, and a repo whose only failures were
    # network-dependent (B4's exact design case) was booked
    # `gated:B2 "suite not green at HEAD"`. A network-dependent failure must
    # produce a network-dependent reason.
    net_dependent = sorted(sealed_failures - net_failures)

    target = next((nid for nid, o in baseline.items() if o == "PASSED"), None)
    cold = warm = None
    if target:
        started = time.monotonic()
        run_in(image, repo, ["python", "-m", "pytest", target, "-q"],
               network=False, log_path=log_dir / "targeted-cold.log", user=user)
        cold = round(time.monotonic() - started, 2)
        started = time.monotonic()
        run_in(image, repo, ["python", "-m", "pytest", target, "-q"],
               network=False, log_path=log_dir / "targeted-warm.log", user=user)
        warm = round(time.monotonic() - started, 2)

    # B2 judges what is genuinely broken; B4 judges what merely needs egress.
    broken = sealed_failures - set(net_dependent)

    total = len(all_ids)
    prefixes = {nid.split("::")[0] for nid in net_dependent}

    # A suite that collected NOTHING is not green -- `len(sealed_failures)==0`
    # is vacuously true there, and reporting it as green pushes the record on
    # to B3, which then eliminates on `flake_rate 1.0`. That reason is false:
    # nothing ran, so nothing was measured as flaky. Zero collected tests is a
    # B2 result ("suite not green at HEAD") and the ledger has to say so,
    # because a wrong elimination reason is worse than a wrong verdict -- it
    # sends the next reader to debug the wrong thing.
    collected = total > 0
    return {
        "test_count": total,
        "container_user": user or "root",
        "collected": collected,
        "collection_error": "" if collected else _collection_error(first_output),
        "head_green": collected and not apparatus_error and len(broken) == 0,
        "head_failures": sorted(broken)[:20],
        "head_failure_count": len(broken),
        "apparatus_error": apparatus_error,
        "bad_runs": bad_runs,
        "suite_returncodes": returncodes,
        "intermittent_failures": sorted(intermittent)[:20],
        "intermittent_count": len(intermittent),
        "skipped_tests": [dict(s) for s in skips
                          if s["test"] in skips_matched],
        "skipped_count": len(skips_matched),
        "stale_skips": stale_skips,
        "stale_skip_count": len(stale_skips),
        "flake_rate": round(len(flaky) / total, 5) if total else 1.0,
        "flaky_tests": flaky[:20],
        "suite_runtime_p50": round(sorted(durations)[len(durations) // 2], 2),
        "targeted_latency_cold": cold,
        "targeted_latency_warm": warm,
        "net_dependent_tests": net_dependent[:50],
        "net_dependent_count": len(net_dependent),
        "net_marker_excludable": len(prefixes) <= 3 and len(net_dependent) > 0,
        "target_nodeid": target,
    }


def budgets(record, mutants=60, tasks=30, k=5, configs=4):
    """Derived wall-clock estimates. Inputs are seconds; report hours.

    Hardening uses the WARM targeted latency on purpose: it runs thousands of
    invocations inside one already-started container, so cold-start overhead
    would inflate the estimate.

    A budget is None, never 0.0, when its input was never measured. A repo
    whose suite collected nothing would otherwise report `hardening_hours
    0.0` beside a healthy candidate's 0.45 and read as the CHEAPER option, in
    the one table the corpus decision is made from.
    """
    warm = record.get("targeted_latency_warm")
    suite = record.get("suite_runtime_p50")
    collected = record.get("collected", True)
    return {
        "hardening_hours": (round(mutants * tasks * warm / 3600, 2)
                            if collected and warm else None),
        "verification_hours": (round(suite * tasks * k * configs / 3600, 2)
                               if collected and suite else None),
    }
