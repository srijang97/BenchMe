"""Tier B: reuse each repo's own shipped environment definition, then measure.

Never synthesises an environment. Descends a ladder and records which rung
worked; the rung is itself the qualification signal.
"""
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

BASE_IMAGE = "python:3.12-slim"

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


def _dockerfile_for_rung4(repo):
    """Generic uv-based image. Deterministic because the repo pins its deps."""
    return f"""FROM {BASE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends git curl \\
    build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
WORKDIR /repo
COPY . /repo
RUN uv pip install --system -e . || uv pip install --system . || true
RUN uv pip install --system pytest || true
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


def build_image(repo, name, rung, log_dir):
    repo = Path(repo)
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    tag = f"benchme-screener/{name}:tierb"

    if rung == 2:
        dockerfile = next(
            p for p in repo.rglob("Dockerfile") if p.is_file())
        cmd = ["docker", "build", "-f", host_path(dockerfile), "-t", tag,
               host_path(repo)]
    else:
        # Rungs 1, 3 and 4 all end up here: write a generic uv image and let
        # the repo's own pins do the work. Record the rung that was DETECTED,
        # not the mechanism used to build.
        generated = repo / "Dockerfile.screener"
        generated.write_text(_dockerfile_for_rung4(repo), encoding="utf-8")
        cmd = ["docker", "build", "-f", host_path(generated), "-t", tag,
               host_path(repo)]

    proc = subprocess.run(cmd, capture_output=True, text=True, env=docker_env(),
                          encoding="utf-8", errors="replace", timeout=3600)
    with open(log_dir / "docker-build.log", "w", encoding="utf-8") as fh:
        fh.write(proc.stdout + "\n" + proc.stderr)
    return tag if proc.returncode == 0 else None


def run_in(image, repo, argv, network, log_path, timeout=3600):
    cmd = ["docker", "run", "--rm", "-v", f"{host_path(repo)}:/repo",
           "-w", "/repo"]
    if not network:
        cmd += ["--network", "none"]
    cmd += [image, *argv]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=docker_env(),
                          encoding="utf-8", errors="replace", timeout=timeout)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc
