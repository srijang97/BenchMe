"""Git metadata extraction. Never executes repository code."""
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# Control characters as separators: they effectively never appear in commit text.
REC = "\x1e"
FLD = "\x1f"

# --name-only, never --numstat. Line counts force blob fetches and defeat the
# blobless clone. See spec section 2.
PRETTY = f"{REC}%H{FLD}%an <%ae>{FLD}%cn <%ce>{FLD}%aI{FLD}%s{FLD}%b{FLD}"


@dataclass
class Commit:
    sha: str
    author: str
    committer: str
    date: str
    subject: str
    body: str
    files: list[str] = field(default_factory=list)


def _run(cmd, cwd=None, log_path=None, timeout=1800):
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"$ {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}\n")
    return proc


def clone(url, dest, log_dir, retries=1):
    """Blobless clone: full commit graph, blobs fetched lazily.

    Checks out HEAD so the file tree is readable for layout metrics.
    """
    dest = Path(dest)
    if (dest / ".git").exists():
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--filter=blob:none", url, str(dest)]
    for attempt in range(retries + 1):
        proc = _run(cmd, log_path=Path(log_dir) / "clone.log")
        if proc.returncode == 0:
            return True
    return False


def log_commits(repo):
    """Non-merge commits, newest first, with the files each one touched."""
    proc = _run(
        ["git", "log", "--no-merges", "--name-only", f"--pretty=format:{PRETTY}"],
        cwd=str(repo),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git log failed in {repo}: {proc.stderr[:500]}")
    commits = []
    for chunk in proc.stdout.split(REC):
        if not chunk.strip():
            continue
        parts = chunk.split(FLD)
        if len(parts) < 7:
            continue
        sha, author, committer, date, subject, body = parts[:6]
        files = [ln.strip() for ln in parts[6].splitlines() if ln.strip()]
        commits.append(Commit(
            sha=sha.strip(), author=author, committer=committer,
            date=date, subject=subject, body=body, files=files,
        ))
    return commits


def tracked_files(repo):
    proc = _run(["git", "ls-files"], cwd=str(repo))
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-files failed in {repo}")
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def head_sha(repo):
    proc = _run(["git", "rev-parse", "HEAD"], cwd=str(repo))
    return proc.stdout.strip()
