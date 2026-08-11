"""Repo-quarter environment profiles and container lifecycle.

The image carries the DEPENDENCY CLOSURE ONLY -- never pydantic itself. If
pydantic sits in site-packages, a candidate checked out at another commit is
not what gets imported, and every result is silently about the wrong code.
That is exactly the bind-mount shadowing that produced zero collected tests
twice during screening. Each candidate instead runs with its own checkout on
PYTHONPATH.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import tierb  # noqa: E402

MEM = "4g"
CPUS = "4"
PIDS = "512"
MIN_DISK_GB = 20
MIN_RAM_GB = 6

DOCKERFILE = """FROM {base}
RUN apt-get update && apt-get install -y --no-install-recommends \\
    git curl build-essential less && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /src
COPY . /src
RUN {export} > /tmp/reqs.txt 2>/dev/null || uv export --no-hashes > /tmp/reqs.txt
RUN uv pip install --system -r /tmp/reqs.txt
RUN uv pip install --system pytest
RUN rm -rf /src
RUN python -m pytest --version
"""


def preflight():
    total, used, free = shutil.disk_usage(Path.home())
    if free / (1024 ** 3) < MIN_DISK_GB:
        return f"only {free / (1024**3):.1f} GB disk free, need {MIN_DISK_GB}"
    proc = subprocess.run(["docker", "info", "--format", "{{.MemTotal}}"],
                          capture_output=True, text=True, env=tierb.docker_env())
    if proc.returncode != 0:
        return "docker daemon not responding"
    return None


def anchor_commit(repo, quarter):
    """Last commit inside the quarter -- its lockfile defines the environment
    for every candidate in the window."""
    year, q = int(quarter[:4]), int(quarter[-1])
    start_month = (q - 1) * 3 + 1
    end_year, end_month = (year, start_month + 3) if q < 4 else (year + 1, 1)
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%H",
         f"--before={end_year}-{end_month:02d}-01",
         f"--after={year}-{start_month:02d}-01"],
        cwd=str(repo), capture_output=True, text=True)
    return proc.stdout.strip() or None


def build_quarter_image(repo, quarter, log_dir):
    sha = anchor_commit(repo, quarter)
    if not sha:
        return None
    work = Path(repo).parent / f"_anchor_{quarter}"
    subprocess.run(["git", "worktree", "remove", "--force", str(work)],
                   cwd=str(repo), capture_output=True, text=True)
    proc = subprocess.run(["git", "worktree", "add", "--detach", str(work), sha],
                          cwd=str(repo), capture_output=True, text=True)
    if proc.returncode != 0:
        return None

    dockerfile = work / "Dockerfile.miner"
    dockerfile.write_text(
        DOCKERFILE.format(base=tierb.BASE_IMAGE, export=tierb._EXPORT),
        encoding="utf-8")
    tag = f"benchme-miner/pydantic:{quarter.lower()}"
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    build = subprocess.run(
        ["docker", "build", "-f", tierb.host_path(dockerfile), "-t", tag,
         tierb.host_path(work)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=tierb.docker_env(), timeout=3600)
    (log_dir / f"build-{quarter}.log").write_text(
        build.stdout + "\n" + build.stderr, encoding="utf-8")
    subprocess.run(["git", "worktree", "remove", "--force", str(work)],
                   cwd=str(repo), capture_output=True, text=True)
    return tag if build.returncode == 0 else None


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
    return subprocess.run(
        ["docker", "exec", container, *argv],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=tierb.docker_env(), timeout=timeout)


def stop_container(container):
    subprocess.run(["docker", "rm", "-f", container], capture_output=True,
                   text=True, env=tierb.docker_env())


def remove_image(tag):
    subprocess.run(["docker", "rmi", "-f", tag], capture_output=True,
                   text=True, env=tierb.docker_env())
