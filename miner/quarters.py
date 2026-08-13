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
import json
import re
import shutil
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import record  # noqa: E402
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
#
# The TEST closure, not a nicety. uv's export takes only the default `dev`
# group, which for pydantic omits `testing-extra` -- so devtools, sqlalchemy
# and cloudpickle are absent, 709 of the 711 outcomes in tests/test_docs.py
# come back SKIPPED, and several suites do not collect at all. Measured on
# 2025Q3: three of the first four candidates recorded `apparatus: no test
# outcomes parsed`, and the fourth was a verdict reached over a suite that had
# almost entirely skipped.
#
# NOT `--all-groups`, which is what the screener's tierb build uses. Measured
# on 2025Q3: pydantic's `docs` and `typechecking` groups pull pydantic-settings
# and pydantic-extra-types, and BOTH DEPEND ON PYDANTIC. Here that resolved to
# an unsatisfiable set and the build failed loudly, but the failure mode to
# fear is the other one: on a quarter where it does resolve, pydantic lands in
# site-packages and the first invariant in this module's docstring is inverted
# silently. The named groups below are the test groups, and nothing in them
# depends on pydantic. The `RUN python -c "import pydantic"` guard in the
# Dockerfile is the backstop if that ever stops being true.
#
# `--all-extras` stays: with `--no-emit-project` it contributes the extras'
# dependencies (email-validator, tzdata -- both needed by the suite) without
# the root project.
TEST_GROUPS = ["testing-extra"]
_GROUPS = " --all-extras" + "".join(f" --group {g}" for g in TEST_GROUPS)

# `--no-editable` is the pydantic-core guarantee, and it is load-bearing from
# 2025-11-10 onward. pydantic commit 41f6776e6 ("Make `uv` automatically
# install `pydantic-core` on `uv run`", #12496) moved pydantic-core from a
# PyPI pin to a uv WORKSPACE member:
#
#     [tool.uv.sources]
#     pydantic-core = { workspace = true }
#
# From that commit on, the export emits `-e ./pydantic-core` -- an EDITABLE
# install, which is only a pointer back into /src. The Dockerfile then runs
# `rm -rf /src` (it must; see the first invariant), and the pointer dangles:
# every candidate in the quarter dies at
# `pydantic/version.py: from pydantic_core import __version__`, and the miner
# books the lot as `apparatus`. Measured before this flag: 2025Q3 (anchor
# predates the migration) ran 0/21 apparatus, while 2025Q4/2026Q1/2026Q2/2026Q3
# ran 30/40 = 75%, every one of them that same import.
#
# `--no-editable` exports workspace members as non-editable, so pydantic-core
# is BUILT INTO site-packages and survives the deletion. Verified in a clean
# container against the real 2026Q3 tree: `-e ./pydantic-core` becomes
# `./pydantic-core`, and after `rm -rf /src`, `import pydantic_core` succeeds
# at 2.48.0 while `import pydantic` still fails -- so this does not trade the
# first invariant away to buy the second.
#
# It is applied to the UNFROZEN fallback too. Dropping it there would let an
# unanchored quarter reintroduce the same failure while the record cheerfully
# reported `anchored=false` rather than the real cause.
EXPORT_FROZEN = tierb._EXPORT + " --no-editable" + _GROUPS
EXPORT_FROZEN_MIN = tierb._EXPORT + " --no-editable"
EXPORT_UNFROZEN = EXPORT_FROZEN.replace("--frozen ", "")
EXPORT_UNFROZEN_MIN = EXPORT_FROZEN_MIN.replace("--frozen ", "")

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
 && ( ( {export} > /tmp/reqs.txt || {export_min} > /tmp/reqs.txt ) \\
      && echo {mode_frozen} > {mode_path} ) \\
 || ( ( {fallback} > /tmp/reqs.txt || {fallback_min} > /tmp/reqs.txt ) \\
      && echo {mode_unfrozen} > {mode_path} )
RUN uv pip install --system -r /tmp/reqs.txt
RUN uv pip install --system pytest hypothesis
RUN mkdir -p /opt/miner/wheels
{wheels_download}
WORKDIR /
RUN rm -rf /src
# The first invariant, enforced rather than assumed. If any exported group
# ever pulls pydantic in transitively (pydantic-settings and
# pydantic-extra-types both do), the closure would no longer be the quarter's
# and a stale pydantic would satisfy imports the candidate's own checkout was
# meant to answer. Fail the build instead.
#
# Placed AFTER `rm -rf /src`: run any earlier and the probe imports /src's own
# pydantic package directory via cwd, which fails the build on every repo.
RUN if python -c "import pydantic" 2>/dev/null; then \\
      echo "FATAL: pydantic is in site-packages; the export leaked the project"; \\
      exit 1; \\
    fi
# The mirror invariant, and the reason this one is a BUILD guard rather than a
# runtime surprise. pydantic-core must be importable WITHOUT /src, because the
# candidate's own checkout supplies pydantic and nothing else supplies the
# compiled core. When the export emitted it editable (see `--no-editable`
# above), this held at build time and failed on every candidate afterwards --
# 30 apparatus records across four quarters before anyone looked at a log.
# Fail the build instead, where one message names the cause once.
RUN python -c "import pydantic_core" >/dev/null 2>&1 || ( \\
      echo "FATAL: pydantic_core is not importable after /src was removed;" \\
      echo "the export probably emitted it editable -- see --no-editable"; \\
      exit 1 )
# Docker creates a missing `-w` directory as root, which a non-root container
# cannot write to. Each candidate's checkout lands here, so it must be owned
# by the user the container actually runs as.
RUN mkdir -p /work && chown {user} /work
WORKDIR /work
RUN python -m pytest --version
# Stage 2 clones the host's pydantic checkout from a read-only bind mount at
# /repo, which a non-root uid does not own, so git refuses it with `fatal:
# detected dubious ownership`. This is declared SYSTEM-wide rather than via
# the GIT_CONFIG_* env vars the screener uses, because `git clone` runs
# upload-pack against the other repository and git strips GIT_CONFIG_COUNT
# and friends from that child's environment (they are local_repo_env) --
# measured: rev-parse on /repo succeeded with the env vars set while clone
# from the same shell still failed.
RUN git config --system --add safe.directory '*'
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
        ["git", "log", "--format=%H",
         f"--before={end_year}-{end_month:02d}-01",
         f"--after={year}-{start_month:02d}-01"],
        cwd=str(repo), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"git log failed for {quarter} in {repo}: {proc.stderr.strip()}")
    shas = [s for s in proc.stdout.strip().splitlines() if s]
    if not shas:
        return None
    # Skip foreign project commits (e.g. pydantic-core commits grafted into repo log)
    expected_name = candidates.EXPECTED_PROJECT.get(Path(repo).name, "pydantic")
    tomls = candidates._read_pyprojects(repo, [(s, s) for s in shas])
    for s in shas:
        pname = candidates.project_name(tomls.get(f"{s}:pyproject.toml", ""))
        if pname == expected_name or pname is None:
            return s
    return None


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
                              export_min=EXPORT_FROZEN_MIN,
                              fallback=EXPORT_UNFROZEN,
                              fallback_min=EXPORT_UNFROZEN_MIN,
                              mode_frozen=MODE_FROZEN,
                              mode_unfrozen=MODE_UNFROZEN,
                              mode_path=EXPORT_MODE_PATH,
                              user=tierb.DEFAULT_CONTAINER_USER,
                              wheels_download=_wheels_download_cmd(quarter)),
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


REPORTER_DIR = "/work/.benchme"
# The plugin's module name and the variable it reads its output path from.
# These live here rather than in outcomes.py because they are facts about
# INSTALLING the plugin; outcomes.py only parses what it writes and stays free
# of any container knowledge.
PLUGIN_MODULE = "benchme_reporter"
REPORT_ENV = "BENCHME_REPORT"


def install_reporter(container):
    """Write the pytest reporter plugin into a running container.

    Once per container, not per candidate.

    It lives at REPORTER_DIR -- `/work/.benchme` -- which is a SIBLING of the
    per-candidate workdirs (`/work/<sha12>`), not a child of one. That single
    choice buys every property this needs at once: it is outside the checkout,
    so pytest cannot collect it as a test and it cannot appear in `git status`
    inside the workdir; and being a sibling, it survives
    `rm -rf /work/<sha12>` between candidates.

    `/work` is the one directory the image hands to the container's own user:
    the Dockerfile template above does `RUN mkdir -p /work && chown {user}
    /work`, so uid 1000 owns it outright and this exec needs no privilege
    escalation. That matters -- the container deliberately runs unprivileged
    so that no permission bug in a candidate's test can be masked by root, and
    an earlier silent-failure incident in this codebase is the reason that
    invariant is worth defending rather than working around.

    Written as BYTES for the same reason runner._apply is: subprocess wraps a
    text-mode stdin in a TextIOWrapper with newline=None, which on Windows
    turns every "\\n" into "\\r\\n". A CRLF Python file still imports, but the
    same defect silently corrupted patch application twice before, so the
    habit is worth keeping.
    """
    source = (Path(__file__).resolve().parent / "reporter_plugin.py").read_bytes()
    target = f"{REPORTER_DIR}/{PLUGIN_MODULE}.py"
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "sh", "-c",
         f"mkdir -p {REPORTER_DIR} && cat > {target}"],
        input=source, capture_output=True, env=tierb.docker_env())
    if proc.returncode != 0:
        return f"could not install reporter: {proc.stderr.decode()[:200]}"
    return None


def start_container(image, name):
    subprocess.run(["docker", "rm", "-f", name], capture_output=True,
                   text=True, env=tierb.docker_env())
    proc = subprocess.run(
        ["docker", "run", "-d", "--name", name,
         "--memory", MEM, "--memory-swap", MEM, "--cpus", CPUS,
         "--pids-limit", PIDS, "--network", "none",
         "--user", tierb.DEFAULT_CONTAINER_USER,
         # A bare uid has no home directory in the image, so HOME=/ , which is
         # not writable; anything wanting a cache (pytest, pip) fails there.
         # Same redirection the screener's run_in uses, so the environment a
         # candidate runs in matches the one the repo was screened green in.
         "-e", "HOME=/tmp", "-e", "XDG_CACHE_HOME=/tmp/.cache",
         # Read-only: the checkout is the source `_checkout` clones FROM, and
         # nothing in stage 2 may write to the host's clone.
         "-v", f"{tierb.host_path(Path(__file__).resolve().parents[1] / 'screener' / 'work' / 'pydantic')}:/repo:ro",
         "-w", "/work", image, "sleep", "infinity"],
        capture_output=True, text=True, env=tierb.docker_env())
    return proc.stdout.strip() if proc.returncode == 0 else None


def exec_in(container, argv, timeout=300):
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


def _wheels_download_cmd(quarter):
    """The Dockerfile layer that pre-downloads every pydantic-core wheel a
    quarter's candidates may need, or "" when the quarter pins none.

    The pins come from the candidate records' `core_pin` field -- the exact
    `pydantic-core==X` pin each commit's root pyproject.toml declares -- so
    the cache is closed over what `runner._align_core_pin` will ask for.

    Two callers exist and both read this file, so the function is the single
    point of truth for what lands in the image:

      * build_quarter_image formats it into the Dockerfile. A failed download
        FAILS THE BUILD: `|| true` is deliberately absent. The whole point of
        the cache is that the container installs offline
        (--no-index --find-links /opt/miner/wheels), so a wheel that was not
        cached is not merely missing convenience -- every candidate needing
        it would run with the wrong pydantic-core and book apparatus, or be
        errored and retried. Failing here names the cause once, at build
        time, the same way the pydantic / pydantic_core guards in the
        Dockerfile do.
      * the container runs --network none, so `pip download` must reach
        PyPI from inside the BUILD (builds keep network; the runtime
        container does not). That is exactly the split this layer encodes.

    A malformed line in candidates.jsonl is skipped, never fatal: the file is
    append-only output, and one corrupted record must not take the quarter's
    build down with it. not_minable candidates never reach a container, so
    their pins must not bloat the image. A quarter whose candidates carry no
    core_pin gets NO wheel layer, so an anchor predating the pydantic-core
    pin does not add a no-op RUN to every old image.
    """
    pins = set()
    if record.CANDIDATES.exists():
        with open(record.CANDIDATES, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    c = json.loads(line)
                except ValueError:
                    # One bad line in an append-only file is a data blemish,
                    # not a reason to starve the quarter of its wheels.
                    continue
                if (c.get("quarter") == quarter
                        and not c.get("not_minable")
                        and c.get("core_pin")):
                    pins.add(c["core_pin"])
    if pins:
        pkgs = " ".join(f"pydantic-core=={p}" for p in sorted(pins))
        dl = " && ".join(
            f"pip download --dest /opt/miner/wheels pydantic-core=={p}"
            for p in sorted(pins))
        return f"RUN {dl}"
    return ""
