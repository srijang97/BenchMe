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
LOCKED_ALL = "uv-locked-all-groups"
LOCKED_DEFAULT = "uv-locked-default-groups"
RESOLVED = "uv-resolved"
REPO_DOCKERFILE = "repo-dockerfile"

# The lock is honoured by EXPORTING it and installing into the system
# interpreter, not by `uv sync`. `uv sync` materialises `/repo/.venv`, and
# `run_in` bind-mounts the host repo over `/repo` at measurement time, which
# replaces the whole directory and takes that venv with it. The suite would
# then run against a bare interpreter. Exporting to the system site-packages
# puts the environment outside the mount point, where it survives.
_LOCKED_INSTALL = """RUN mkdir -p /opt/screener \
 && ( uv export --frozen --no-hashes --no-emit-project --all-groups \
        -o /tmp/requirements.txt \
      && echo all-groups > /opt/screener/export-mode ) \
 || ( uv export --frozen --no-hashes --no-emit-project \
        -o /tmp/requirements.txt \
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
    probe = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", tag,
         "cat", "/opt/screener/export-mode"],
        capture_output=True, text=True, env=docker_env(), encoding="utf-8",
        errors="replace", timeout=300)
    mode = probe.stdout.strip()
    if mode == "all-groups":
        return LOCKED_ALL
    if mode == "default-groups":
        return LOCKED_DEFAULT
    return LOCKED


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
    listing = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", image, "sh", "-c",
         "git config --global --add safe.directory /repo >/dev/null 2>&1; "
         "cd /repo && git ls-files --others --ignored --exclude-standard"],
        capture_output=True, text=True, env=docker_env(), encoding="utf-8",
        errors="replace", timeout=timeout)
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
    tar = subprocess.run(
        ["docker", "run", "--rm", "-i", "--network", "none", image,
         "tar", "-cf", "-", "-C", "/repo", "-T", "-"],
        input="\n".join(wanted).encode("utf-8"),
        capture_output=True, env=docker_env(), timeout=timeout)
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
    proc = subprocess.run(cmd, capture_output=True, text=True, env=docker_env(),
                          encoding="utf-8", errors="replace", timeout=timeout)
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


def measure(image, repo, log_dir, runs=5, user=DEFAULT_CONTAINER_USER):
    """Five sealed suite runs, one networked run, and targeted-test latency."""
    import time

    log_dir = Path(log_dir)
    per_run = []
    durations = []
    first_output = ""
    for i in range(runs):
        started = time.monotonic()
        proc = run_in(image, repo, PYTEST_ARGV, network=False,
                      log_path=log_dir / f"suite-{i}.log", user=user)
        durations.append(time.monotonic() - started)
        per_run.append(parse_outcomes(proc.stdout))
        if i == 0:
            first_output = f"{proc.stdout}\n{proc.stderr}"

    all_ids = set().union(*per_run) if per_run else set()
    flaky = [nid for nid in all_ids
             if len({run.get(nid) for run in per_run}) > 1]
    baseline = per_run[0] if per_run else {}
    sealed_failures = {nid for nid, o in baseline.items()
                       if o in ("FAILED", "ERROR")}

    net_proc = run_in(image, repo, PYTEST_ARGV, network=True,
                      log_path=log_dir / "suite-networked.log", user=user)
    net_outcomes = parse_outcomes(net_proc.stdout)
    net_failures = {nid for nid, o in net_outcomes.items()
                    if o in ("FAILED", "ERROR")}
    # Failing sealed but passing networked: these are network-dependent, not
    # agent mistakes. The runner denies egress by design, so without this diff
    # they would be misattributed later.
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
        "head_green": collected and len(sealed_failures) == 0,
        "head_failures": sorted(sealed_failures)[:20],
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
