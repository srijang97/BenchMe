"""Repo-quarter environment profiles and container lifecycle.

The image carries the DEPENDENCY CLOSURE ONLY -- never pydantic itself. If
pydantic sits in site-packages, a candidate checked out at another commit is
not what gets imported, and every result is silently about the wrong code.
That is exactly the bind-mount shadowing that produced zero collected tests
twice during screening. Each candidate instead runs with its own checkout on
PYTHONPATH.

There is a SECOND invariant the import probe cannot see. The export must be
`--frozen`, so the closure is the one the lockfile pinned at the quarter's
end. A non-frozen export resolves fresh from PyPI and yields a MODERN
environment wearing a quarter's name: pydantic is still absent, pytest still
runs, the probe still passes, and every candidate is nonetheless measured
against dependencies that did not exist at its commit. That defeats the whole
point of anchoring while looking healthy. The build therefore records which
export ran, and `QuarterImage.anchored` carries the answer out to the caller,
which MUST stamp it onto every candidate record produced in that image.
"""
import re
import shutil
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import tierb  # noqa: E402

MEM = "4g"
CPUS = "4"
PIDS = "512"
MIN_DISK_GB = 20
MIN_RAM_GB = 6

QUARTER_RE = re.compile(r"^\d{4}Q[1-4]$")

# `--frozen` is the anchoring guarantee; `--no-emit-project` is the
# pydantic-absence guarantee. The fallback drops ONLY `--frozen`, because
# `--frozen` is what fails on a quarter whose lockfile uv cannot read (the
# pre-53bf2f2 pdm quarters). Dropping `--no-emit-project` too would emit the
# root project and install pydantic -- silently inverting the first invariant
# while the build still exits green.
EXPORT_FROZEN = tierb._EXPORT
EXPORT_UNFROZEN = tierb._EXPORT.replace("--frozen ", "")

# Written inside the image by the export step; read back after the build.
EXPORT_MODE_PATH = "/opt/miner/export-mode"
MODE_FROZEN = "frozen"
MODE_UNFROZEN = "unfrozen"

# No `2>/dev/null` on the primary export: hiding its stderr means a build log
# can never explain why the fallback fired.
DOCKERFILE = """FROM {base}
RUN apt-get update && apt-get install -y --no-install-recommends \\
    git curl build-essential less && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /src
COPY . /src
RUN mkdir -p /opt/miner \\
 && ( {export} > /tmp/reqs.txt \\
      && echo {mode_frozen} > {mode_path} ) \\
 || ( {fallback} > /tmp/reqs.txt \\
      && echo {mode_unfrozen} > {mode_path} )
RUN uv pip install --system -r /tmp/reqs.txt
RUN uv pip install --system pytest
WORKDIR /
RUN rm -rf /src
# Docker creates a missing `-w` directory as root, which a non-root container
# cannot write to. Each candidate's checkout lands here, so it must be owned
# by the user the container actually runs as.
RUN mkdir -p /work && chown {user} /work
WORKDIR /work
RUN python -m pytest --version
"""

# A build result that distinguishes a verdict from an apparatus failure.
#   tag      image tag, or None
#   reason   machine-readable outcome, one of REASON_*
#   anchor   the anchor sha, when one was found
#   anchored True only if the frozen export ran; see the module docstring
#   skip     True when this is a real verdict about the quarter (nothing to
#            mine), False when it is our apparatus that broke
QuarterImage = namedtuple("QuarterImage",
                          "tag reason anchor anchored skip")

REASON_OK = "ok"
REASON_NO_COMMITS = "no-commits-in-quarter"
REASON_BAD_QUARTER = "malformed-quarter"
REASON_GIT_FAILED = "git-log-failed"
REASON_WORKTREE_FAILED = "worktree-add-failed"
REASON_BUILD_FAILED = "docker-build-failed"
REASON_BUILD_TIMEOUT = "docker-build-timeout"
REASON_DOCKER_MISSING = "docker-not-available"


def preflight():
    """Human-readable reason to refuse, or None. Refuses BEFORE a long run
    rather than dying halfway through one."""
    total, used, free = shutil.disk_usage(Path.home())
    if free / (1024 ** 3) < MIN_DISK_GB:
        return f"only {free / (1024**3):.1f} GB disk free, need {MIN_DISK_GB}"
    try:
        proc = subprocess.run(["docker", "info", "--format", "{{.MemTotal}}"],
                              capture_output=True, text=True,
                              env=tierb.docker_env(), timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "docker daemon not responding"
    if proc.returncode != 0:
        return "docker daemon not responding"
    # MemTotal is what Docker can actually hand a container, which is the
    # number that matters -- on Windows that is the VM's allocation, not the
    # host's. An unparseable value is not evidence of a problem, so it is
    # ignored rather than turned into a false refusal.
    raw = proc.stdout.strip()
    try:
        mem_gb = int(raw) / (1024 ** 3)
    except ValueError:
        return None
    if mem_gb < MIN_RAM_GB:
        return (f"docker has only {mem_gb:.1f} GB RAM available, "
                f"need {MIN_RAM_GB}")
    return None


def anchor_commit(repo, quarter):
    """Last commit inside the quarter -- its lockfile defines the environment
    for every candidate in the window.

    Raises ValueError on a malformed quarter. This is not pedantry: `2025Q9`
    used to compute `start_month=25` and pass `--after=2025-25-01`, which git
    IGNORES silently with exit 0, returning the same sha as 2025Q4. A
    plausible wrong anchor is worse than a crash, because every candidate in
    that window would then be built against an environment from a different
    quarter with nothing to show it.

    Raises RuntimeError if git itself failed, so that "git is broken" cannot
    be mistaken for "this quarter has no commits".
    """
    if not isinstance(quarter, str) or not QUARTER_RE.match(quarter):
        raise ValueError(
            f"malformed quarter {quarter!r}; expected YYYYQn with n in 1-4")
    year, q = int(quarter[:4]), int(quarter[-1])
    start_month = (q - 1) * 3 + 1
    end_year, end_month = (year, start_month + 3) if q < 4 else (year + 1, 1)
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%H",
         f"--before={end_year}-{end_month:02d}-01",
         f"--after={year}-{start_month:02d}-01"],
        cwd=str(repo), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"git log failed for {quarter} in {repo}: {proc.stderr.strip()}")
    return proc.stdout.strip() or None


def image_export_mode(tag):
    """Read back which export ran inside a built image. None if unreadable."""
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", tag,
         "cat", EXPORT_MODE_PATH],
        capture_output=True, text=True, env=tierb.docker_env(), timeout=120)
    return proc.stdout.strip() if proc.returncode == 0 else None


def build_quarter_image(repo, quarter, log_dir):
    """Build the quarter's image. Returns a QuarterImage, never raises.

    A log is ALWAYS written, including for the failures that never reach
    docker. Distinguishing "nothing to mine this quarter" from "our apparatus
    broke" is the project's signature requirement; collapsing both to None
    reproduces exactly the confusion the screener was built to avoid.
    """
    log_dir = Path(log_dir)
    log = []
    work = Path(repo).parent / f"_anchor_{quarter}"
    sha = None
    worktree_added = False

    def finish(tag, reason, anchored=False, skip=False):
        log.insert(0, f"quarter={quarter!r} anchor={sha} "
                      f"reason={reason} anchored={anchored} skip={skip}")
        # The quarter reaches this path unvalidated, so it cannot be trusted
        # as a filename: it may be None, empty, or carry separators that would
        # write the log outside log_dir entirely -- losing the very forensics
        # this function exists to guarantee.
        stem = re.sub(r"[^0-9A-Za-z._-]", "_", str(quarter))[:64] or "unknown"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"build-{stem}.log").write_text(
                "\n".join(log), encoding="utf-8")
        except OSError as exc:  # logging must never mask the real outcome
            print(f"warning: could not write build log: {exc}",
                  file=sys.stderr)
        return QuarterImage(tag, reason, sha, anchored, skip)

    try:
        try:
            sha = anchor_commit(repo, quarter)
        except ValueError as exc:
            # anchor_commit is right to raise -- validation belongs there. But
            # this wrapper promises a QuarterImage and a log on every path, and
            # a contract the code does not honour is worse than none, because
            # the caller stops defending against it.
            log.append(str(exc))
            return finish(None, REASON_BAD_QUARTER)
        except RuntimeError as exc:
            log.append(str(exc))
            return finish(None, REASON_GIT_FAILED)
        if not sha:
            log.append("git log found no commits in this quarter")
            # A real verdict about the quarter, not an apparatus failure.
            return finish(None, REASON_NO_COMMITS, skip=True)

        subprocess.run(["git", "worktree", "remove", "--force", str(work)],
                       cwd=str(repo), capture_output=True, text=True)
        proc = subprocess.run(
            ["git", "worktree", "add", "--detach", str(work), sha],
            cwd=str(repo), capture_output=True, text=True)
        if proc.returncode != 0:
            log.append("git worktree add failed:\n" + proc.stdout + proc.stderr)
            return finish(None, REASON_WORKTREE_FAILED)
        worktree_added = True

        dockerfile = work / "Dockerfile.miner"
        dockerfile.write_text(
            DOCKERFILE.format(base=tierb.BASE_IMAGE,
                              export=EXPORT_FROZEN,
                              fallback=EXPORT_UNFROZEN,
                              mode_frozen=MODE_FROZEN,
                              mode_unfrozen=MODE_UNFROZEN,
                              mode_path=EXPORT_MODE_PATH,
                              user=tierb.DEFAULT_CONTAINER_USER),
            encoding="utf-8")
        log.append("--- Dockerfile ---\n" + dockerfile.read_text(encoding="utf-8"))

        tag = f"benchme-miner/pydantic:{quarter.lower()}"
        try:
            build = subprocess.run(
                ["docker", "build", "-f", tierb.host_path(dockerfile), "-t",
                 tag, tierb.host_path(work)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=tierb.docker_env(), timeout=3600)
        except subprocess.TimeoutExpired as exc:
            log.append("docker build exceeded 3600s\n"
                       + tierb._as_text(exc.stdout) + tierb._as_text(exc.stderr))
            return finish(None, REASON_BUILD_TIMEOUT)
        except OSError as exc:
            log.append(f"docker could not be executed: {exc}")
            return finish(None, REASON_DOCKER_MISSING)

        log.append("--- docker build ---\n" + build.stdout + "\n" + build.stderr)
        if build.returncode != 0:
            return finish(None, REASON_BUILD_FAILED)

        mode = image_export_mode(tag)
        log.append(f"--- export mode --- {mode}")
        anchored = mode == MODE_FROZEN
        if not anchored:
            log.append(
                "WARNING: the frozen export did not run, so this image was "
                "resolved fresh rather than pinned to the quarter's lockfile. "
                "It is NOT anchored; results from it are about modern "
                "dependencies, not the quarter's.")
        return finish(tag, REASON_OK, anchored=anchored)
    finally:
        # Always remove the worktree. A timeout or a missing docker binary
        # would otherwise leave a stale worktree that blocks the next attempt.
        if worktree_added:
            subprocess.run(["git", "worktree", "remove", "--force", str(work)],
                           cwd=str(repo), capture_output=True, text=True)


def start_container(image, name):
    subprocess.run(["docker", "rm", "-f", name], capture_output=True,
                   text=True, env=tierb.docker_env())
    proc = subprocess.run(
        ["docker", "run", "-d", "--name", name,
         "--memory", MEM, "--memory-swap", MEM, "--cpus", CPUS,
         "--pids-limit", PIDS, "--network", "none",
         "--user", tierb.DEFAULT_CONTAINER_USER,
         "-w", "/work", image, "sleep", "infinity"],
        capture_output=True, text=True, env=tierb.docker_env())
    return proc.stdout.strip() if proc.returncode == 0 else None


def exec_in(container, argv, timeout=1800):
    """Run argv in the container. ALWAYS returns a CompletedProcess.

    On timeout the return code is `tierb.TIMEOUT_RETURNCODE` (-9), the
    established marker for "this run never produced a verdict of its own", so
    a hang cannot be booked as a test failure.

    CALLER CONTRACT: killing `docker exec` does NOT kill the process inside
    the container. It keeps running, keeps burning the container's capped CPU
    and memory, and holds the one-container-at-a-time slot. The caller MUST
    call `stop_container` after any timeout; the container is not reusable.
    """
    try:
        return subprocess.run(
            ["docker", "exec", container, *argv],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=tierb.docker_env(), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            args=["docker", "exec", container, *argv],
            returncode=tierb.TIMEOUT_RETURNCODE,
            stdout=tierb._as_text(exc.stdout),
            stderr=tierb._as_text(exc.stderr)
            + f"\nquarters.exec_in: timed out after {timeout}s; the process "
              f"inside the container is still running -- caller must call "
              f"stop_container({container!r}).\n")


def stop_container(container):
    subprocess.run(["docker", "rm", "-f", container], capture_output=True,
                   text=True, env=tierb.docker_env())


def remove_image(tag):
    subprocess.run(["docker", "rmi", "-f", tag], capture_output=True,
                   text=True, env=tierb.docker_env())
