"""Git metadata extraction. Never executes repository code."""
import shutil
import stat
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


def _text(value):
    """Coerce subprocess output to str: it may be None or bytes on the error paths."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _write_log(log_path, cmd, stdout, stderr):
    if log_path is None:
        return
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(f"$ {' '.join(cmd)}\n{_text(stdout)}\n{_text(stderr)}\n")


def _run(cmd, cwd=None, log_path=None, timeout=1800):
    """Run a git command. Logs on the timeout path too, then re-raises.

    Callers that must not abort the sweep -- clone() -- catch TimeoutExpired
    themselves. log_commits/tracked_files/head_sha are called inside the
    orchestrator's try/except, so raising there is the intended signal.
    """
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        _write_log(log_path, cmd, exc.stdout, f"TIMEOUT after {timeout}s")
        raise
    _write_log(log_path, cmd, proc.stdout, proc.stderr)
    return proc


def _usable_clone(dest, log_path=None):
    """True only if dest holds a clone with a resolvable HEAD.

    A bare `.git` directory is not enough: an interrupted clone leaves one
    behind, and trusting it would report `error` later where the candidate
    should have been recorded `unavailable`.
    """
    if not (dest / ".git").exists():
        return False
    try:
        proc = _run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=str(dest), log_path=log_path, timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _discard(dest, log_path=None):
    """Remove an unusable clone so the retry starts from a clean directory.

    Git marks objects read-only, so rmtree needs a chmod fallback on Windows.
    """
    def _on_error(func, path, exc):
        try:
            Path(path).chmod(stat.S_IWRITE)
            func(path)
        except OSError:
            pass

    try:
        shutil.rmtree(dest, onexc=_on_error)
    except OSError as exc:
        _write_log(log_path, ["rm", "-rf", str(dest)], "", f"DISCARD FAILED: {exc}")
    if dest.exists():
        _write_log(log_path, ["rm", "-rf", str(dest)], "", "DISCARD INCOMPLETE")
        return False
    return True


def clone(url, dest, log_dir, retries=1):
    """Blobless clone: full commit graph, blobs fetched lazily.

    Checks out HEAD so the file tree is readable for layout metrics.

    Returns False -- never raises -- for every failure mode, including a
    timeout. False means `unavailable`, and the sweep continues.
    """
    dest = Path(dest)
    log_path = Path(log_dir) / "clone.log"
    if _usable_clone(dest, log_path):
        return True
    cmd = ["git", "clone", "--filter=blob:none", url, str(dest)]
    for attempt in range(retries + 1):
        try:
            if dest.exists() and not _discard(dest, log_path):
                return False
            dest.parent.mkdir(parents=True, exist_ok=True)
            proc = _run(cmd, log_path=log_path)
        except subprocess.TimeoutExpired:
            continue
        except OSError as exc:
            _write_log(log_path, cmd, "", f"CLONE FAILED: {exc}")
            return False
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
