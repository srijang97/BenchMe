# Repo Screener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the two-tier screener that selects, by measurement, the public Python repository BenchMe develops its first evaluation corpus against.

**Architecture:** Tier A clones each candidate with `--filter=blob:none` and computes git-metadata metrics without executing any repository code; hard gates eliminate and a single key ranks. Tier B takes the top N survivors, reuses each repo's own shipped environment definition to build a container, and measures suite runtime, flakiness, targeted-test latency and network dependence. Output is a Markdown report listing every candidate including eliminated ones.

**Tech Stack:** Python 3.14.4 (stdlib + PyYAML only), pytest for the three rule tests, Git 2.53, Docker 29.3.1 (WSL2 backend).

**Spec:** `docs/superpowers/specs/2026-08-10-repo-screener-design.md`

**Branch:** continue on `spec/repo-screener` — the spec is unmerged and this is one unit of work.

## Global Constraints

- **Python 3.14.4**, invoked as `python` on this Windows host. Use the Bash tool (Git Bash), not PowerShell, for all commands in this plan.
- **Dependencies: PyYAML only.** Plus `pytest` as a dev dependency. No other third-party packages.
- **Testing is deliberately narrow.** Spec §7 restricts the test suite to exactly three counting-rule fixtures, all in `screener/tests/test_metrics.py`. Tasks 1, 2, 6, 7, 8 and 9 therefore use a **manual verification step** in place of a unit test. Do not invent additional tests — a wrong counting rule is the only bug in this tool that is expensive, and the spec says so explicitly.
- **Tier A must never execute repository code.** Git plumbing and file reads only.
- **Tier A must never use `git log --numstat`.** Line counts force blob fetches and defeat the blobless clone. Count files, never lines.
- **No composite score anywhere.** Gates eliminate; `projected_capsules` ranks; everything else is a report column.
- **Paths inside records are POSIX-style** (forward slashes), regardless of host.
- **Freshness cutoff** defaults to `2026-05-01`, configurable via `--cutoff`.
- **Finalist count** N defaults to `4`, configurable via `--top`.
- **Conversion constant** for projected yield is `0.022`, defined once as `CONVERSION_RATE` in `metrics.py`.
- **Tasks 7–9 have a human in the loop by design.** Spec §4.1 makes `operator_minutes` a typed-in number because it is the leading indicator on the services-trap gate; a fabricated value corrupts it. These tasks need Docker Desktop running and an interactive terminal, so they are **not suitable for autonomous subagent execution**. Tasks 1–6 are fully non-interactive.
- **Docker is invoked with forward-slashed host paths** via `tierb.host_path()`, and with `MSYS_NO_PATHCONV=1` set. Backslashed sources collide with the `-v SRC:DEST` separator on Windows.

---

## File Structure

| File | Responsibility |
|---|---|
| `screener/candidates.yaml` | The 18 candidate repos: clone URL, diversity tag, note |
| `screener/screen.py` | CLI (`tier-a`, `tier-b`, `report`), orchestration, resumable JSONL store |
| `screener/gitmeta.py` | Blobless clone with retry; `git log` parsing into `Commit` records; tracked-file listing |
| `screener/metrics.py` | **The durable artifact.** Candidate-pair rule, authorship exclusion, all Tier A metrics |
| `screener/gates.py` | G1–G7 and B1–B4 evaluation, terminal status, ranking |
| `screener/tierb.py` | Environment ladder, container build, suite measurements, derived budgets |
| `screener/report.py` | `REPORT.md` rendering, all five sections |
| `screener/tests/conftest.py` | Synthetic git repository builder |
| `screener/tests/test_metrics.py` | The three counting-rule tests |

`metrics.py` is separated from everything else on purpose: it is what gets harvested into the miner when this code is thrown away.

---

## Task 1: Scaffold, candidate list, and resumable record store

**Files:**
- Create: `screener/candidates.yaml`
- Create: `screener/screen.py`
- Create: `screener/requirements.txt`
- Create: `screener/.gitignore`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `load_candidates(path: str) -> list[dict]` — each dict has keys `name`, `url`, `tag`, `note`
  - `read_records(path: str) -> dict[str, dict]` — maps `name` to its last record
  - `append_record(path: str, record: dict) -> None`
  - `operator_minutes_for(name: str, args) -> int` — non-interactive when supplied, fails closed otherwise
  - `OUT = Path("screener/out")`, `TIER_A = OUT/"tier_a.jsonl"`, `TIER_B = OUT/"tier_b.jsonl"`, `LOGS = OUT/"logs"`

- [ ] **Step 1: Create the directory layout**

```bash
cd /c/Users/Srijan/Documents/BenchMe
mkdir -p screener/tests screener/out/logs
```

- [ ] **Step 2: Write `screener/requirements.txt`**

```
PyYAML==6.0.2
pytest==8.3.4
```

- [ ] **Step 3: Write `screener/.gitignore`**

```
out/
work/
__pycache__/
```

- [ ] **Step 4: Write `screener/candidates.yaml`**

```yaml
# Candidate repos for the BenchMe corpus screener.
# tag is one of: logic, io, framework, coupling, cli, app
# Every entry is a prior to be falsified, not a pre-screened fact.
candidates:
  - name: pydantic
    url: https://github.com/pydantic/pydantic.git
    tag: logic
    note: Default pick. Rust core arrives as a pinned wheel so G5 should hold.
  - name: attrs
    url: https://github.com/python-attrs/attrs.git
    tag: logic
    note: Clean and hermetic; doubt it clears G2.
  - name: marshmallow
    url: https://github.com/marshmallow-code/marshmallow.git
    tag: logic
    note: Same shape as attrs, same volume doubt.
  - name: packaging
    url: https://github.com/pypa/packaging.git
    tag: logic
    note: Very clean, probably too quiet for G2.
  - name: jsonschema
    url: https://github.com/python-jsonschema/jsonschema.git
    tag: logic
    note: Spec-driven tests; test_map_ratio uncertain.
  - name: httpx
    url: https://github.com/encode/httpx.git
    tag: io
    note: Mock transports should keep it hermetic; B4 is the question.
  - name: starlette
    url: https://github.com/encode/starlette.git
    tag: io
    note: TestClient-based, likely hermetic.
  - name: werkzeug
    url: https://github.com/pallets/werkzeug.git
    tag: io
    note: Socket-level tests; B4 risk.
  - name: urllib3
    url: https://github.com/urllib3/urllib3.git
    tag: io
    note: Spins a local test server; expect B4 trouble.
  - name: fastapi
    url: https://github.com/fastapi/fastapi.git
    tag: framework
    note: High velocity, hermetic, large test count.
  - name: sqlalchemy
    url: https://github.com/sqlalchemy/sqlalchemy.git
    tag: coupling
    note: Best coupling in the list; expect G4 and suite runtime to bite.
  - name: jinja
    url: https://github.com/pallets/jinja.git
    tag: framework
    note: Moderate volume.
  - name: flask
    url: https://github.com/pallets/flask.git
    tag: framework
    note: SWE-bench overlap label; small, likely fails G2.
  - name: click
    url: https://github.com/pallets/click.git
    tag: cli
    note: Very hermetic, clean layout.
  - name: black
    url: https://github.com/psf/black.git
    tag: cli
    note: Excellent test discipline; velocity may have flattened.
  - name: rich
    url: https://github.com/Textualize/rich.git
    tag: cli
    note: Snapshot oracles are a different class; worth seeing.
  - name: pre-commit
    url: https://github.com/pre-commit/pre-commit.git
    tag: app
    note: Application-shaped probe, git-heavy.
  - name: mkdocs
    url: https://github.com/mkdocs/mkdocs.git
    tag: app
    note: Application-shaped probe, hermetic.
```

- [ ] **Step 5: Write `screener/screen.py`**

```python
"""BenchMe repo screener.

Two tiers. Tier A reads git metadata only and never executes repository code.
Tier B builds a container and runs the suite for the top N survivors.

See docs/superpowers/specs/2026-08-10-repo-screener-design.md
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
WORK = ROOT / "work"
LOGS = OUT / "logs"
TIER_A = OUT / "tier_a.jsonl"
TIER_B = OUT / "tier_b.jsonl"

TERMINAL = ("passed", "unavailable")


def load_candidates(path):
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["candidates"]


def read_records(path):
    """Return {name: record} keyed by name, last write wins."""
    records = {}
    p = Path(path)
    if not p.exists():
        return records
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records[rec["name"]] = rec
    return records


def append_record(path, record):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def is_done(record):
    """A record is done if it reached a terminal state. gated:* counts as done."""
    status = record.get("status", "")
    return status in TERMINAL or status.startswith("gated:")


def operator_minutes_for(name, args):
    """Minutes the operator spent getting this repo's suite green.

    Spec section 4.1 makes this a human-supplied number on purpose: it is the
    leading indicator on the services-trap gate. It therefore FAILS CLOSED
    rather than defaulting to 0 -- a silently fabricated 0 would corrupt the
    one metric that says whether this is a product or a consultancy.
    """
    mapping = {}
    for pair in getattr(args, "operator_minutes", []) or []:
        key, _, value = pair.partition("=")
        mapping[key.strip()] = value.strip()
    if name in mapping:
        return int(mapping[name])
    if sys.stdin.isatty():
        return int(input(f"  operator minutes spent on {name}: ").strip() or 0)
    raise SystemExit(
        f"operator_minutes for '{name}' was not supplied and stdin is not a "
        f"terminal. Re-run with --operator-minutes {name}=<minutes>."
    )


def cmd_tier_a(args):
    print("tier-a not implemented yet", file=sys.stderr)
    return 1


def cmd_tier_b(args):
    print("tier-b not implemented yet", file=sys.stderr)
    return 1


def cmd_report(args):
    print("report not implemented yet", file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="screen")
    parser.add_argument("--candidates", default=str(ROOT / "candidates.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("tier-a", help="static git-metadata screen, all candidates")
    a.add_argument("--cutoff", default="2026-05-01")
    a.add_argument("--force", action="store_true")
    a.set_defaults(func=cmd_tier_a)

    b = sub.add_parser("tier-b", help="container build and suite measurement, finalists only")
    b.add_argument("--top", type=int, default=4)
    b.add_argument("--force", action="store_true")
    b.add_argument("--operator-minutes", action="append", default=[],
                   metavar="NAME=MINUTES",
                   help="minutes you spent per repo, e.g. --operator-minutes click=35. "
                        "Required when stdin is not a terminal.")
    b.set_defaults(func=cmd_tier_b)

    r = sub.add_parser("report", help="render REPORT.md")
    r.add_argument("--cutoff", default="2026-05-01")
    r.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    for d in (OUT, WORK, LOGS):
        d.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Install dependencies and verify the CLI runs**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pip install -r screener/requirements.txt
python screener/screen.py tier-a
```

Expected: prints `tier-a not implemented yet` to stderr, exit code 1, and `screener/out/` plus `screener/work/` now exist.

- [ ] **Step 7: Verify the candidate list parses and has 18 entries**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -c "import sys; sys.path.insert(0,'screener'); import screen; c=screen.load_candidates('screener/candidates.yaml'); print(len(c)); print(sorted({x['tag'] for x in c}))"
```

Expected: `18` then `['app', 'cli', 'coupling', 'framework', 'io', 'logic']`.

- [ ] **Step 8: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/candidates.yaml screener/screen.py screener/requirements.txt screener/.gitignore
git commit -m "feat(screener): scaffold, candidate list, resumable record store"
```

---

## Task 2: Git metadata layer

**Files:**
- Create: `screener/gitmeta.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `Commit` dataclass with fields: `sha: str`, `author: str`, `committer: str`, `date: str` (ISO-8601), `subject: str`, `body: str`, `files: list[str]`
  - `clone(url: str, dest: Path, log_dir: Path, retries: int = 1) -> bool` — True on success; False means `unavailable`
  - `log_commits(repo: Path) -> list[Commit]` — non-merge commits only, newest first
  - `tracked_files(repo: Path) -> list[str]` — POSIX paths at HEAD
  - `head_sha(repo: Path) -> str`

- [ ] **Step 1: Write `screener/gitmeta.py`**

```python
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
```

- [ ] **Step 2: Verify against this repository itself**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -c "
import sys; sys.path.insert(0,'screener')
import gitmeta
cs = gitmeta.log_commits('.')
print('commits:', len(cs))
print('newest sha:', cs[0].sha[:8])
print('newest subject:', cs[0].subject)
print('files in newest:', cs[0].files)
print('tracked:', len(gitmeta.tracked_files('.')))
"
```

Expected: at least 3 commits, a real 8-character SHA, the subject `Add repo screener design spec`, a `files` list containing `docs/superpowers/specs/2026-08-10-repo-screener-design.md`, and a tracked-file count in the dozens.

- [ ] **Step 3: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/gitmeta.py
git commit -m "feat(screener): blobless clone and git log parsing"
```

> **Amended during execution (2026-08-10).** The code above shipped with two
> exception-safety defects that review caught. `clone()` is required to be
> *total* — it signals failure by returning `False` so the candidate is recorded
> `unavailable` and the sweep continues. As written it could raise on two paths:
> `subprocess.TimeoutExpired` from `_run`, and a leftover partial `.git`
> short-circuiting to `True` and then failing downstream. The shipped module adds
> `_usable_clone()` (verifies `git rev-parse --verify HEAD`) and `_discard()`
> (removes an unusable clone, with a chmod fallback for git's read-only objects),
> and catches `TimeoutExpired` in `clone()` only.
>
> Note the boundary: `_run` logs the timeout and **re-raises**. Only `clone()`
> catches it. `log_commits`, `tracked_files` and `head_sha` must be allowed to
> raise, because they run inside the orchestrator's `try/except` where an
> exception is the intended `error` signal — swallowing a timeout there would
> turn a hung `git log` into an empty commit list and a fabricated metric.
>
> See `screener/gitmeta.py` for the authoritative implementation.

---

## Task 3: The candidate-pair rule

This is the durable artifact. It gets two of the three tests in the whole project.

**Files:**
- Create: `screener/metrics.py`
- Create: `screener/tests/conftest.py`
- Create: `screener/tests/test_metrics.py`

**Interfaces:**
- Consumes: `gitmeta.Commit`
- Produces:
  - `CONVERSION_RATE = 0.022`
  - `is_test_file(path: str) -> bool`
  - `is_source_file(path: str) -> bool`
  - `is_human(commit) -> bool`
  - `is_candidate_pair(commit, max_files: int = 10) -> bool`

- [ ] **Step 1: Write the synthetic repo builder `screener/tests/conftest.py`**

```python
"""Builds tiny git repositories with known-answer histories."""
import subprocess
from pathlib import Path

import pytest


def _git(repo, *args, env=None):
    full = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
            "PATH": __import__("os").environ["PATH"]}
    if env:
        full.update(env)
    subprocess.run(["git", *args], cwd=str(repo), check=True,
                   capture_output=True, text=True, env=full)


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Test Human")
    _git(repo, "config", "user.email", "human@example.com")
    return repo


def commit(repo, files, message, author="Test Human <human@example.com>",
           committer=None):
    """files: {relative_path: contents}"""
    for rel, contents in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contents, encoding="utf-8")
    _git(repo, "add", "-A")
    name, email = author.rstrip(">").split(" <")
    cname, cemail = (name, email)
    if committer:
        cname, cemail = committer.rstrip(">").split(" <")
    env = {
        "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": cname, "GIT_COMMITTER_EMAIL": cemail,
    }
    _git(repo, "commit", "-q", "-m", message, env=env)


@pytest.fixture
def repo_factory(tmp_path):
    return lambda: make_repo(tmp_path)
```

- [ ] **Step 2: Write the failing tests `screener/tests/test_metrics.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gitmeta  # noqa: E402
import metrics  # noqa: E402
from conftest import commit, make_repo  # noqa: E402


def test_authorship_exclusion(tmp_path):
    """Spec section 7 fixture 1: bots and AI co-authors are excluded."""
    repo = make_repo(tmp_path)
    commit(repo, {"src/a.py": "x=1", "tests/test_a.py": "assert 1"},
           "human change one")
    commit(repo, {"src/b.py": "x=2", "tests/test_b.py": "assert 2"},
           "bump deps", author="dependabot[bot] <bot@github.com>")
    commit(repo, {"src/c.py": "x=3", "tests/test_c.py": "assert 3"},
           "agent change\n\nCo-authored-by: Claude <noreply@anthropic.com>")
    commit(repo, {"src/d.py": "x=4", "tests/test_d.py": "assert 4"},
           "human change two")

    commits = gitmeta.log_commits(repo)
    pairs = [c for c in commits if metrics.is_candidate_pair(c)]
    excluded = [c for c in commits if not metrics.is_human(c)]

    assert len(pairs) == 2
    assert len(excluded) == 2
    assert {c.subject for c in pairs} == {"human change one", "human change two"}


def test_candidate_pair_definition(tmp_path):
    """Spec section 7 fixture 2: exactly one commit qualifies."""
    repo = make_repo(tmp_path)
    commit(repo, {"src/base.py": "x=0"}, "seed")
    commit(repo, {"src/only.py": "x=1"}, "source only")
    commit(repo, {"tests/test_only.py": "assert 1"}, "test only")
    commit(repo, {"src/good.py": "x=2", "tests/test_good.py": "assert 2"},
           "valid pair")
    wide = {f"src/w{i}.py": f"x={i}" for i in range(10)}
    wide["tests/test_wide.py"] = "assert 1"
    commit(repo, wide, "eleven files")

    commits = gitmeta.log_commits(repo)
    pairs = [c for c in commits if metrics.is_candidate_pair(c)]

    assert len(pairs) == 1
    assert pairs[0].subject == "valid pair"
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest screener/tests/test_metrics.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'metrics'`.

- [ ] **Step 4: Write `screener/metrics.py`**

```python
"""Tier A metric definitions.

This module is the durable artifact. When the rest of the screener is thrown
away, these rules are harvested into the miner's stage 0. Change them
deliberately, and update screener/tests/test_metrics.py when you do.
"""
import re
from pathlib import PurePosixPath

# SWE-Next honest conversion from raw candidate pairs to valid capsules.
# A conservative floor, not a prediction. See spec section 9 item 2.
CONVERSION_RATE = 0.022

BOT_IDENTITY = re.compile(r"\[bot\]|dependabot|renovate|pre-commit-ci", re.I)
AI_TRAILER = re.compile(
    r"co-authored-by:[^\n]*(copilot|devin|claude|codex)", re.I)
AI_MARKER = re.compile(
    r"generated with[^\n]*(claude code|codex|copilot)", re.I)


def is_test_file(path):
    p = PurePosixPath(path)
    if p.suffix != ".py":
        return False
    if "tests" in p.parts or "test" in p.parts:
        return True
    return p.name.startswith("test_") or p.stem.endswith("_test")


def is_source_file(path):
    p = PurePosixPath(path)
    return p.suffix == ".py" and not is_test_file(path)


def is_human(commit):
    """False for bot identities, AI co-author trailers, and generation markers."""
    identity = f"{commit.author} {commit.committer}"
    if BOT_IDENTITY.search(identity):
        return False
    message = f"{commit.subject}\n{commit.body}"
    if AI_TRAILER.search(message) or AI_MARKER.search(message):
        return False
    return True


def is_candidate_pair(commit, max_files=10):
    """A commit that could in principle become a capsule.

    Merge commits are already excluded by `git log --no-merges`.
    """
    if not is_human(commit):
        return False
    if len(commit.files) > max_files:
        return False
    has_source = any(is_source_file(f) for f in commit.files)
    has_test = any(is_test_file(f) for f in commit.files)
    return has_source and has_test
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest screener/tests/test_metrics.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/metrics.py screener/tests/conftest.py screener/tests/test_metrics.py
git commit -m "feat(screener): candidate-pair rule with authorship exclusion"
```

---

## Task 4: Remaining Tier A metrics

**Files:**
- Modify: `screener/metrics.py`
- Modify: `screener/tests/test_metrics.py`

**Interfaces:**
- Consumes: `is_test_file`, `is_source_file`, `is_candidate_pair`, `CONVERSION_RATE` from Task 3
- Produces:
  - `test_map_ratio(tracked: list[str]) -> float`
  - `detect_environment(repo: Path, tracked: list[str]) -> dict` — keys `lockfile`, `has_pyproject`, `has_ci`, `has_container`, `compiled_markers`, `service_markers`, `uses_pytest`
  - `compute_tier_a(commits: list, tracked: list[str], repo: Path, cutoff: str) -> dict` — the full metric record

- [ ] **Step 1: Write the failing test for `test_map_ratio`**

Append to `screener/tests/test_metrics.py`:

```python
def test_test_map_ratio(tmp_path):
    """Spec section 7 fixture 3: three of four test files resolve to a source."""
    tracked = [
        "src/pkg/alpha.py",
        "src/pkg/beta.py",
        "src/pkg/gamma.py",
        "tests/test_alpha.py",     # resolves to alpha.py
        "tests/test_beta.py",      # resolves to beta.py
        "tests/gamma_test.py",     # resolves to gamma.py
        "tests/test_nothing.py",   # resolves to nothing
    ]
    assert metrics.test_map_ratio(tracked) == 0.75
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest screener/tests/test_metrics.py::test_test_map_ratio -v
```

Expected: FAIL — `AttributeError: module 'metrics' has no attribute 'test_map_ratio'`.

- [ ] **Step 3: Append the remaining metrics to `screener/metrics.py`**

```python
COMPILED_NAMES = ("Cargo.toml", "CMakeLists.txt", "setup.py")
COMPILED_SUFFIXES = (".pyx", ".pxd")
SERVICE_WORDS = re.compile(
    r"postgres|mysql|mariadb|redis|rabbitmq|kafka|mongodb|docker-compose", re.I)
CI_DIRS = (".github/workflows", ".gitlab-ci.yml", ".circleci", "azure-pipelines.yml")
LOCKFILES = ("uv.lock", "poetry.lock", "Pipfile.lock", "pdm.lock")
REVERT = re.compile(r'^Revert "')
HOTFIX = re.compile(r"\b(hotfix|regression|fixup)\b", re.I)


def test_map_ratio(tracked):
    """Fraction of test files resolvable to a source file by naming convention.

    Conventions: tests/test_X.py -> **/X.py, and tests/X_test.py -> **/X.py.
    """
    tests = [t for t in tracked if is_test_file(t)]
    if not tests:
        return 0.0
    stems = {PurePosixPath(s).stem for s in tracked if is_source_file(s)}
    matched = 0
    for t in tests:
        stem = PurePosixPath(t).stem
        if stem.startswith("test_") and stem[len("test_"):] in stems:
            matched += 1
        elif stem.endswith("_test") and stem[: -len("_test")] in stems:
            matched += 1
    return matched / len(tests)


def detect_environment(repo, tracked):
    names = {PurePosixPath(t).name for t in tracked}
    lockfile = next((lf for lf in LOCKFILES if lf in names), None)
    if lockfile is None and any(
        PurePosixPath(t).name.startswith("requirements") for t in tracked
    ):
        lockfile = "requirements"

    compiled = [
        t for t in tracked
        if PurePosixPath(t).suffix in COMPILED_SUFFIXES
        or PurePosixPath(t).name in ("Cargo.toml", "CMakeLists.txt")
    ]
    # setup.py only counts when it actually declares extensions.
    if "setup.py" in names:
        for t in tracked:
            if PurePosixPath(t).name == "setup.py":
                try:
                    body = (repo / t).read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if "ext_modules" in body:
                    compiled.append(t)

    service = []
    for t in tracked:
        name = PurePosixPath(t).name
        parent = str(PurePosixPath(t).parent)
        if parent.startswith(".github/workflows") or name in (
            "tox.ini", "pyproject.toml", "docker-compose.yml", "docker-compose.yaml"
        ):
            try:
                body = (repo / t).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if SERVICE_WORDS.search(body):
                service.append(t)

    uses_pytest = False
    for t in tracked:
        if PurePosixPath(t).name in ("pyproject.toml", "tox.ini", "setup.cfg",
                                     "pytest.ini"):
            try:
                body = (repo / t).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "pytest" in body:
                uses_pytest = True
                break

    return {
        "lockfile": lockfile,
        "has_pyproject": "pyproject.toml" in names,
        "has_ci": any(any(t.startswith(d) or t == d for d in CI_DIRS)
                      for t in tracked),
        "has_container": ("Dockerfile" in names
                          or "devcontainer.json" in names),
        "compiled_markers": sorted(set(compiled)),
        "service_markers": sorted(set(service)),
        "uses_pytest": uses_pytest,
    }


def _percentile(values, pct):
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(int(round((pct / 100) * (len(ordered) - 1))), len(ordered) - 1)
    return ordered[idx]


def compute_tier_a(commits, tracked, repo, cutoff):
    """Full Tier A metric record. `cutoff` is an ISO date string, e.g. 2026-05-01."""
    pairs = [c for c in commits if is_candidate_pair(c)]
    excluded = [c for c in commits if not is_human(c)]
    fresh_pairs = [c for c in pairs if c.date[:10] >= cutoff]
    since_cutoff = [c for c in commits if c.date[:10] >= cutoff]

    file_counts = [len(c.files) for c in pairs]
    source_counts = [sum(1 for f in c.files if is_source_file(f)) for c in pairs]

    py_files = [t for t in tracked if PurePosixPath(t).suffix == ".py"]
    loc = 0
    for t in py_files:
        try:
            loc += sum(1 for _ in open(repo / t, encoding="utf-8", errors="replace"))
        except OSError:
            pass

    record = {
        "commits_total": len(commits),
        "commits_since_cutoff": len(since_cutoff),
        "candidate_pairs": len(pairs),
        "candidate_pairs_fresh": len(fresh_pairs),
        "excluded_nonhuman": len(excluded),
        "projected_capsules": round(len(pairs) * CONVERSION_RATE, 2),
        "projected_fresh": round(len(fresh_pairs) * CONVERSION_RATE, 2),
        "fresh_share": round(len(fresh_pairs) / len(pairs), 4) if pairs else 0.0,
        "files_p50": _percentile(file_counts, 50),
        "files_p90": _percentile(file_counts, 90),
        "frac_multifile": (
            round(sum(1 for n in source_counts if n >= 3) / len(pairs), 4)
            if pairs else 0.0
        ),
        "revert_pairs": sum(1 for c in commits if REVERT.match(c.subject)),
        "hotfix_commits": sum(1 for c in commits if HOTFIX.search(c.subject)),
        "test_map_ratio": round(test_map_ratio(tracked), 4),
        "tracked_files": len(tracked),
        "python_loc": loc,
    }
    record.update(detect_environment(repo, tracked))
    return record
```

Note: `commits_180d` from the spec's metric table is intentionally dropped — `commits_since_cutoff` covers the same "is this repo alive" question and is the value G3 actually gates on. Carrying two overlapping liveness counters would invite them to disagree in the report.

- [ ] **Step 4: Run the tests to verify all three pass**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest screener/tests/ -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/metrics.py screener/tests/test_metrics.py
git commit -m "feat(screener): tier A environment, yield and discrimination metrics"
```

---

## Task 5: Gates and ranking

**Files:**
- Create: `screener/gates.py`

**Interfaces:**
- Consumes: the record dict from `metrics.compute_tier_a`
- Produces:
  - `TIER_A_GATES: list[tuple[str, str, callable]]` — `(id, description, predicate)`
  - `evaluate_tier_a(record: dict) -> tuple[str, str|None]` — returns `("passed", None)` or `("gated:G4", "test_map_ratio 0.31 < 0.5")`
  - `evaluate_tier_b(record: dict) -> tuple[str, str|None]`
  - `rank(records: list[dict]) -> list[dict]` — survivors only, sorted by `projected_capsules` descending

- [ ] **Step 1: Write `screener/gates.py`**

```python
"""Hard gates and ranking. Gates eliminate; one key ranks; no composite score."""

CUTOFF_MIN_PAIRS = 360        # G2: 360 * 0.022 = 7.92 ~ 8 capsules
CUTOFF_MIN_FRESH_COMMITS = 30  # G3
MIN_TEST_MAP_RATIO = 0.5       # G4
MAX_OPERATOR_MINUTES = 120     # B1
MAX_FLAKE_RATE = 0.005         # B3
MAX_NET_DEPENDENT_SHARE = 0.02  # B4


def _g1(r):
    if not r.get("uses_pytest"):
        return "no pytest configuration detected"
    return None


def _g2(r):
    n = r.get("candidate_pairs", 0)
    if n < CUTOFF_MIN_PAIRS:
        return f"candidate_pairs {n} < {CUTOFF_MIN_PAIRS}"
    return None


def _g3(r):
    n = r.get("commits_since_cutoff", 0)
    if n < CUTOFF_MIN_FRESH_COMMITS:
        return f"commits_since_cutoff {n} < {CUTOFF_MIN_FRESH_COMMITS}"
    return None


def _g4(r):
    v = r.get("test_map_ratio", 0.0)
    if v < MIN_TEST_MAP_RATIO:
        return f"test_map_ratio {v} < {MIN_TEST_MAP_RATIO}"
    return None


def _g5(r):
    m = r.get("compiled_markers") or []
    if m:
        return f"compiled extension built from source: {', '.join(m[:3])}"
    return None


def _g6(r):
    m = r.get("service_markers") or []
    if m:
        return f"service dependency referenced in: {', '.join(m[:3])}"
    return None


def _g7(r):
    if not r.get("lockfile"):
        return "no lockfile or pinned requirements"
    return None


TIER_A_GATES = [
    ("G1", "Python + pytest detected", _g1),
    ("G2", "candidate_pairs >= 360", _g2),
    ("G3", "commits_since_cutoff >= 30", _g3),
    ("G4", "test_map_ratio >= 0.5", _g4),
    ("G5", "no compiled extension built from source", _g5),
    ("G6", "no service dependency on default test path", _g6),
    ("G7", "lockfile or pinned dependencies present", _g7),
]


def _b1(r):
    if r.get("env_rung") in (None, 0):
        return "no usable environment definition"
    if r.get("operator_minutes", 0) > MAX_OPERATOR_MINUTES:
        return f"operator_minutes {r['operator_minutes']} > {MAX_OPERATOR_MINUTES}"
    return None


def _b2(r):
    if not r.get("head_green"):
        return "suite not green at HEAD"
    return None


def _b3(r):
    v = r.get("flake_rate", 1.0)
    if v > MAX_FLAKE_RATE:
        return f"flake_rate {v} > {MAX_FLAKE_RATE}"
    return None


def _b4(r):
    total = r.get("test_count", 0)
    net = len(r.get("net_dependent_tests") or [])
    if total and (net / total) > MAX_NET_DEPENDENT_SHARE:
        if r.get("net_marker_excludable"):
            return None
        return f"net_dependent_tests {net}/{total} and not marker-excludable"
    return None


TIER_B_GATES = [
    ("B1", "environment builds at rung <=4 within 120 operator minutes", _b1),
    ("B2", "suite green at HEAD", _b2),
    ("B3", "flake_rate <= 0.5%", _b3),
    ("B4", "network-dependent tests <=2% or marker-excludable", _b4),
]


def _evaluate(record, gates):
    for gate_id, _desc, predicate in gates:
        reason = predicate(record)
        if reason is not None:
            return f"gated:{gate_id}", reason
    return "passed", None


def evaluate_tier_a(record):
    return _evaluate(record, TIER_A_GATES)


def evaluate_tier_b(record):
    return _evaluate(record, TIER_B_GATES)


def rank(records):
    """Survivors only, ranked on the single key. No composite score."""
    survivors = [r for r in records if r.get("status") == "passed"]
    return sorted(survivors, key=lambda r: r.get("projected_capsules", 0),
                  reverse=True)
```

- [ ] **Step 2: Wire `cmd_tier_a` in `screener/screen.py`**

Replace the `cmd_tier_a` stub with:

```python
def cmd_tier_a(args):
    import gates
    import gitmeta
    import metrics

    candidates = load_candidates(args.candidates)
    done = read_records(TIER_A)
    for cand in candidates:
        name = cand["name"]
        if not args.force and name in done and is_done(done[name]):
            print(f"skip {name} ({done[name]['status']})")
            continue
        log_dir = LOGS / name
        dest = WORK / name
        print(f"tier-a {name} ...", flush=True)
        record = {"name": name, "url": cand["url"], "tag": cand["tag"],
                  "note": cand.get("note", ""), "cutoff": args.cutoff}
        try:
            # clone() is total by contract, but it stays INSIDE the guard so a
            # future regression there degrades one candidate instead of
            # aborting the sweep. Spec section 6: the sweep never aborts.
            if not gitmeta.clone(cand["url"], dest, log_dir):
                record.update(status="unavailable",
                              reason="clone failed after retry")
                append_record(TIER_A, record)
                continue
            commits = gitmeta.log_commits(dest)
            tracked = gitmeta.tracked_files(dest)
            record["head_sha"] = gitmeta.head_sha(dest)
            record.update(metrics.compute_tier_a(commits, tracked, dest,
                                                 args.cutoff))
        except Exception as exc:  # a screener bug, not a repo verdict
            record.update(status="error", reason=f"{type(exc).__name__}: {exc}")
            append_record(TIER_A, record)
            continue
        status, reason = gates.evaluate_tier_a(record)
        record.update(status=status, reason=reason)
        append_record(TIER_A, record)
        print(f"  {status} {reason or ''}")
    return 0
```

- [ ] **Step 3: Verify on a three-candidate subset**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python - <<'PY'
import yaml, pathlib
src = yaml.safe_load(open('screener/candidates.yaml', encoding='utf-8'))
keep = [c for c in src['candidates'] if c['name'] in ('click', 'flask', 'pydantic')]
pathlib.Path('screener/subset.yaml').write_text(
    yaml.safe_dump({'candidates': keep}, sort_keys=False), encoding='utf-8')
PY
python screener/screen.py --candidates screener/subset.yaml tier-a
```

Expected: three clone lines then a status line each. `flask` most likely reports `gated:G2` with a candidate-pair count; `pydantic` should either pass or gate on a *named* gate. Any `error` status is a screener bug to fix before continuing.

- [ ] **Step 4: Verify resumability**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python screener/screen.py --candidates screener/subset.yaml tier-a
```

Expected: three `skip <name> (<status>)` lines and no re-cloning.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/gates.py screener/screen.py
git commit -m "feat(screener): tier A gates, ranking, and sweep orchestration"
```

---

## Task 6: Tier A report

**Files:**
- Create: `screener/report.py`
- Modify: `screener/screen.py`

**Interfaces:**
- Consumes: `screen.read_records`, `gates.rank`, `gates.TIER_A_GATES`
- Produces: `render(tier_a: dict, tier_b: dict, cutoff: str, screener_sha: str) -> str`

- [ ] **Step 1: Write `screener/report.py`**

```python
"""REPORT.md rendering. Every candidate appears, including eliminated ones."""
import datetime as _dt

import gates

A_COLUMNS = [
    ("candidate_pairs", "pairs"),
    ("projected_capsules", "proj"),
    ("candidate_pairs_fresh", "fresh"),
    ("projected_fresh", "proj_f"),
    ("fresh_share", "fresh%"),
    ("excluded_nonhuman", "nonhuman"),
    ("frac_multifile", "multifile"),
    ("files_p50", "f_p50"),
    ("files_p90", "f_p90"),
    ("test_map_ratio", "testmap"),
    ("revert_pairs", "reverts"),
    ("hotfix_commits", "hotfix"),
    ("tracked_files", "files"),
    ("python_loc", "loc"),
    ("lockfile", "lock"),
    ("tag", "tag"),
]

B_COLUMNS = [
    ("env_rung", "rung"),
    ("operator_minutes", "op_min"),
    ("head_green", "green"),
    ("flake_rate", "flake"),
    ("suite_runtime_p50", "suite_s"),
    ("targeted_latency_warm", "warm_s"),
    ("net_dependent_count", "net"),
    ("hardening_hours", "harden_h"),
    ("verification_hours", "verify_h"),
]


def _table(records, columns):
    head = "| repo | " + " | ".join(label for _k, label in columns) + " |"
    rule = "|---" * (len(columns) + 1) + "|"
    rows = []
    for r in records:
        cells = [str(r.get(key, "")) for key, _label in columns]
        rows.append("| " + r["name"] + " | " + " | ".join(cells) + " |")
    return "\n".join([head, rule, *rows])


def render(tier_a, tier_b, cutoff, screener_sha):
    now = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    a_records = list(tier_a.values())
    survivors = gates.rank(a_records)
    b_records = list(tier_b.values())

    out = []
    out.append("# Repo screener report\n")
    out.append("## 1. Run metadata\n")
    out.append(f"- Generated: {now}")
    out.append(f"- Freshness cutoff: `{cutoff}`")
    out.append(f"- Screener commit: `{screener_sha}`")
    out.append(f"- Candidates screened: {len(a_records)}")
    out.append(f"- Tier A survivors: {len(survivors)}")
    out.append(f"- Tier B finalists: {len(b_records)}\n")

    out.append("## 2. Gate ledger\n")
    out.append("Every candidate, including eliminated ones. A screener that "
               "reports only survivors is indistinguishable from one with a "
               "bug in its gates.\n")
    out.append("| repo | status | reason | head_sha |")
    out.append("|---|---|---|---|")
    for r in sorted(a_records, key=lambda x: x["name"]):
        out.append("| {} | `{}` | {} | `{}` |".format(
            r["name"], r.get("status", "?"), r.get("reason") or "",
            (r.get("head_sha") or "")[:8]))
    out.append("")
    out.append("Gate definitions:\n")
    for gate_id, desc, _p in gates.TIER_A_GATES:
        out.append(f"- **{gate_id}** — {desc}")
    for gate_id, desc, _p in gates.TIER_B_GATES:
        out.append(f"- **{gate_id}** — {desc}")
    out.append("")

    out.append("## 3. Ranked survivors\n")
    if survivors:
        out.append("Ranked on `projected_capsules` alone. All other columns "
                   "are reported, not scored.\n")
        out.append(_table(survivors, A_COLUMNS))
    else:
        out.append("No candidate cleared all Tier A gates.")
    out.append("")

    out.append("## 4. Tier B finalists\n")
    if b_records:
        out.append(_table(b_records, B_COLUMNS))
        out.append("")
        out.append("`harden_h` and `verify_h` are soft thresholds, not gates.")
    else:
        out.append("Tier B has not been run.")
    out.append("")

    out.append("## 5. Recommendation\n")
    passed_b = [r for r in b_records if r.get("status") == "passed"]
    passed_b.sort(key=lambda r: r.get("hardening_hours", 1e9))
    if passed_b:
        top = passed_b[0]
        out.append(f"**Corpus repo: `{top['name']}`** — cleared Tier A and "
                   f"Tier B, environment rung {top.get('env_rung')}, "
                   f"{top.get('operator_minutes')} operator minutes, "
                   f"hardening budget {top.get('hardening_hours')} h.\n")
        out.append("Runners-up by diversity tag, for repos 2 and 3 without "
                   "re-running Tier A:\n")
        seen = {top.get("tag")}
        for r in survivors:
            if r.get("tag") not in seen:
                out.append(f"- `{r['name']}` ({r.get('tag')}) — "
                           f"{r.get('projected_capsules')} projected capsules")
                seen.add(r.get("tag"))
    else:
        out.append("No finalist cleared Tier B. Review the gate ledger.")
    out.append("")
    return "\n".join(out)
```

- [ ] **Step 2: Wire `cmd_report` in `screener/screen.py`**

Replace the `cmd_report` stub with:

```python
def cmd_report(args):
    import subprocess

    import report

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         cwd=str(ROOT.parent), capture_output=True,
                         text=True).stdout.strip() or "unknown"
    text = report.render(read_records(TIER_A), read_records(TIER_B),
                         args.cutoff, sha)
    path = OUT / "REPORT.md"
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")
    return 0
```

- [ ] **Step 3: Verify the report renders from the subset run**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python screener/screen.py report && cat screener/out/REPORT.md
```

Expected: five numbered sections; section 2 lists all three subset repos with statuses and reasons; section 4 says Tier B has not been run; section 5 says no finalist cleared Tier B.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/report.py screener/screen.py
git commit -m "feat(screener): report rendering with full gate ledger"
```

---

## Task 7: Tier B environment ladder

**Files:**
- Create: `screener/tierb.py`
- Modify: `screener/screen.py`

**Interfaces:**
- Consumes: `screen.WORK`, `screen.LOGS`, `gitmeta.head_sha`
- Produces:
  - `detect_rung(repo: Path, tracked: list[str]) -> tuple[int, str]` — `(rung, description)`; rung `0` means none found
  - `build_image(repo: Path, name: str, rung: int, log_dir: Path) -> str | None` — returns image tag or None
  - `run_in(image: str, repo: Path, argv: list[str], network: bool, log_path: Path, timeout: int) -> subprocess.CompletedProcess`

- [ ] **Step 1: Start Docker and confirm the daemon responds**

```bash
cd /c/Users/Srijan/Documents/BenchMe
docker info --format '{{.ServerVersion}}'
```

Expected: a version string. If it errors, launch Docker Desktop and retry before continuing.

- [ ] **Step 2: Write `screener/tierb.py`**

```python
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
```

- [ ] **Step 3: Verify rung detection and a build on one repo**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -c "
import sys; sys.path.insert(0,'screener')
import gitmeta, tierb
from pathlib import Path
repo = Path('screener/work/click')
tracked = gitmeta.tracked_files(repo)
print('rung:', tierb.detect_rung(repo, tracked))
tag = tierb.build_image(repo, 'click', tierb.detect_rung(repo, tracked)[0], Path('screener/out/logs/click'))
print('image:', tag)
"
```

Expected: a rung between 1 and 4 with the file that triggered it, then an image tag. On failure, read `screener/out/logs/click/docker-build.log` — a build failure is a **result** (`gated:B1`), not a crash, and Task 8 records it as such.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/tierb.py
git commit -m "feat(screener): tier B environment ladder and container build"
```

---

## Task 8: Tier B measurements and derived budgets

**Files:**
- Modify: `screener/tierb.py`
- Modify: `screener/screen.py`

**Interfaces:**
- Consumes: `run_in`, `detect_rung`, `build_image` from Task 7
- Produces:
  - `parse_outcomes(stdout: str) -> dict[str, str]` — maps `nodeid` to `PASSED`/`FAILED`/`ERROR`/`SKIPPED`
  - `measure(image: str, repo: Path, log_dir: Path, runs: int = 5) -> dict`
  - `budgets(record: dict, mutants: int = 60, tasks: int = 30, k: int = 5, configs: int = 4) -> dict`

- [ ] **Step 1: Append the measurement functions to `screener/tierb.py`**

```python
OUTCOME = re.compile(r"^(?P<nodeid>\S+::\S+)\s+(?P<outcome>PASSED|FAILED|ERROR|SKIPPED)",
                     re.M)


def parse_outcomes(stdout):
    return {m.group("nodeid"): m.group("outcome")
            for m in OUTCOME.finditer(stdout)}


def measure(image, repo, log_dir, runs=5):
    """Five sealed suite runs, one networked run, and targeted-test latency."""
    import time

    log_dir = Path(log_dir)
    per_run = []
    durations = []
    for i in range(runs):
        started = time.monotonic()
        proc = run_in(image, repo, ["python", "-m", "pytest", "-v", "-p",
                                    "no:randomly", "--tb=no", "-q"],
                      network=False, log_path=log_dir / f"suite-{i}.log")
        durations.append(time.monotonic() - started)
        per_run.append(parse_outcomes(proc.stdout))

    all_ids = set().union(*per_run) if per_run else set()
    flaky = [nid for nid in all_ids
             if len({run.get(nid) for run in per_run}) > 1]
    baseline = per_run[0] if per_run else {}
    sealed_failures = {nid for nid, o in baseline.items()
                       if o in ("FAILED", "ERROR")}

    net_proc = run_in(image, repo, ["python", "-m", "pytest", "-v", "-p",
                                   "no:randomly", "--tb=no", "-q"],
                      network=True, log_path=log_dir / "suite-networked.log")
    net_outcomes = parse_outcomes(net_proc.stdout)
    net_failures = {nid for nid, o in net_outcomes.items()
                    if o in ("FAILED", "ERROR")}
    net_dependent = sorted(sealed_failures - net_failures)

    target = next((nid for nid, o in baseline.items() if o == "PASSED"), None)
    cold = warm = None
    if target:
        started = time.monotonic()
        run_in(image, repo, ["python", "-m", "pytest", target, "-q"],
               network=False, log_path=log_dir / "targeted-cold.log")
        cold = round(time.monotonic() - started, 2)
        started = time.monotonic()
        run_in(image, repo, ["python", "-m", "pytest", target, "-q"],
               network=False, log_path=log_dir / "targeted-warm.log")
        warm = round(time.monotonic() - started, 2)

    total = len(all_ids)
    prefixes = {nid.split("::")[0] for nid in net_dependent}
    return {
        "test_count": total,
        "head_green": len(sealed_failures) == 0,
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
    """Derived wall-clock estimates. Inputs are seconds; report hours."""
    warm = record.get("targeted_latency_warm") or 0
    suite = record.get("suite_runtime_p50") or 0
    return {
        "hardening_hours": round(mutants * tasks * warm / 3600, 2),
        "verification_hours": round(suite * tasks * k * configs / 3600, 2),
    }
```

- [ ] **Step 2: Wire `cmd_tier_b` in `screener/screen.py`**

Replace the `cmd_tier_b` stub with:

```python
def cmd_tier_b(args):
    import gates
    import gitmeta
    import tierb

    tier_a = read_records(TIER_A)
    finalists = gates.rank(list(tier_a.values()))[: args.top]
    if not finalists:
        print("no Tier A survivors", file=sys.stderr)
        return 1
    done = read_records(TIER_B)
    for cand in finalists:
        name = cand["name"]
        if not args.force and name in done and is_done(done[name]):
            print(f"skip {name} ({done[name]['status']})")
            continue
        repo = WORK / name
        log_dir = LOGS / name
        record = {"name": name, "tag": cand.get("tag"),
                  "head_sha": gitmeta.head_sha(repo)}
        tracked = gitmeta.tracked_files(repo)
        rung, source = tierb.detect_rung(repo, tracked)
        record["env_rung"] = rung
        record["env_source"] = source
        print(f"tier-b {name}: rung {rung} ({source})", flush=True)
        if rung == 0:
            record.update(status="gated:B1",
                          reason="no usable environment definition",
                          operator_minutes=0)
            append_record(TIER_B, record)
            continue

        image = tierb.build_image(repo, name, rung, log_dir)
        if image is None:
            record.update(status="gated:B1",
                          reason="docker build failed; see docker-build.log",
                          operator_minutes=0)
            append_record(TIER_B, record)
            continue

        record["operator_minutes"] = operator_minutes_for(name, args)
        record.update(tierb.measure(image, repo, log_dir))
        record.update(tierb.budgets(record))
        status, reason = gates.evaluate_tier_b(record)
        record.update(status=status, reason=reason)
        append_record(TIER_B, record)
        print(f"  {status} {reason or ''}")
    return 0
```

- [ ] **Step 3: Verify Tier B end to end on the subset**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python screener/screen.py --candidates screener/subset.yaml tier-b --top 1
```

Expected: a rung line, a build, an `operator minutes` prompt, then a status line. `screener/out/tier_b.jsonl` gains one record containing `flake_rate`, `suite_runtime_p50`, `targeted_latency_warm`, `hardening_hours` and `verification_hours`.

Type the **real** number of minutes you spent — it is the services-trap indicator, not decoration. If stdin is not a terminal the command exits with instructions rather than guessing; supply the value explicitly instead:

```bash
python screener/screen.py --candidates screener/subset.yaml tier-b --top 1 --operator-minutes click=35
```

- [ ] **Step 4: Regenerate the report and confirm sections 4 and 5 populate**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python screener/screen.py report && sed -n '/## 4/,$p' screener/out/REPORT.md
```

Expected: section 4 shows the finalist row with both budget numbers; section 5 either names a corpus repo or explains that no finalist cleared Tier B.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add screener/tierb.py screener/screen.py
git commit -m "feat(screener): tier B suite measurement and derived budgets"
```

---

## Task 9: Full sweep and recorded verdict

**Files:**
- Create: `screener/out/REPORT.md` (generated)
- Modify: `docs/AGENTS_LOG.md`

**Interfaces:**
- Consumes: everything above
- Produces: the repo decision, and the log entry the project's standing rules require

- [ ] **Step 1: Remove the subset file and run the full Tier A sweep**

```bash
cd /c/Users/Srijan/Documents/BenchMe
rm -f screener/subset.yaml
python screener/screen.py tier-a
```

Expected: 18 status lines. Clones total a few GB in `screener/work/`, which is gitignored. Any `error` status is a bug — fix it and re-run that candidate with `--force`.

- [ ] **Step 2: Inspect the ranking before spending Tier B time**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python screener/screen.py report && sed -n '/## 2/,/## 4/p' screener/out/REPORT.md
```

Expected: a gate ledger for all 18 and a ranked survivor table. Sanity-check two priors from the spec: `flask` should gate on G2, and `sqlalchemy` should gate on G4 or rank poorly on `test_map_ratio`. **If neither holds, stop and re-read the metric definitions before running Tier B** — a rule that disagrees with both priors is more likely wrong than the priors are.

- [ ] **Step 3: Run Tier B on the top 4**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python screener/screen.py tier-b --top 4
```

Expected: four rung/build/measure cycles with an operator-minutes prompt each. Docker build time dominates; budget an hour or more. Run this from an interactive terminal, or pass `--operator-minutes NAME=N` once per finalist.

- [ ] **Step 4: Generate the final report**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python screener/screen.py report && cat screener/out/REPORT.md
```

Expected: all five sections populated, section 5 naming a corpus repo and runners-up by diversity tag.

- [ ] **Step 5: Force the report into git despite the ignored `out/` directory**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add -f screener/out/REPORT.md screener/out/tier_a.jsonl screener/out/tier_b.jsonl
git commit -m "chore(screener): record full sweep results"
```

- [ ] **Step 6: Append the session entry to `docs/AGENTS_LOG.md`**

Insert immediately after the `## Session register` heading, above the `cowork agent 1` entry. Fill the bracketed values from the actual report — do not invent them.

```markdown
### claude-code agent 2 — 2026-08-10
- **Model / surface**: `claude-opus-5` via Claude Code
- **Scope**: Select the public Python repo for BenchMe's first evaluation corpus by measurement rather than judgement.
- **Inputs read**: `docs/AGENTS_LOG.md`, `research/00`–`11`, `research/claude/` (teardown, methodology report, cost model), `research/claude/COWORK_AGENT_1_HANDOFF.md`, `docs/PROJECT_KNOWLEDGE_BASE.md`, `docs/DEMO_01_CODEX_ITS_DANGEROUS.md`, `demo/` layout
- **Artifacts produced**:
  - `docs/superpowers/specs/2026-08-10-repo-screener-design.md`
  - `docs/superpowers/plans/2026-08-10-repo-screener.md`
  - `screener/` — two-tier screener; `metrics.py` is the harvestable rule set
  - `screener/out/REPORT.md` — gate ledger and ranking for 18 candidates
- **Decisions made**:
  - First artifact varies the **model-tier** axis (segment 1), not harness or quantisation. At MDE ~12.5 pp, frontier-vs-frontier and prompt-level effects are not observable.
  - **Top-1 corpus now**, diversity deferred; the screener records a diversity tag so repos 2–3 need no re-run.
  - Gate-and-rank with a single ranking key; **no composite score**, consistent with `PROJECT_KNOWLEDGE_BASE.md` §12.
  - Freshness **ranks but does not gate** — a fresh-only gate eliminates the entire field, so the fresh/stale split is reported beside every downstream result instead.
  - Corpus repo selected: **[NAME]** ([reason from report §5]).
- **Conclusions overturned**: Demo 01's repo-selection criteria. "Small enough to understand in one evening" selected a rig, not a corpus, and produced zero discrimination (3/3 solved) on a repo too small to exhibit a harness effect at all.
- **New rule recorded**: repo size sets a floor on which effects are observable. Binds hard on the harness axis, weakly on model-tier.
- **Open questions left**:
  - Which harness is fixed for the model-tier experiment, and whether it needs the Inspect AI agent bridge for open-model endpoints.
  - The 2.2% conversion is a conservative floor; recalibrate `projected_capsules` after the miner's first real run.
  - The fixture repo is unselected — recommendation is ~20 SWE-bench Verified instances from `sympy`.
- **Cost / effort**: one session; no model spend beyond the session itself
```

- [ ] **Step 7: Add the Contested/Superseded row**

Append to the **Contested / superseded** table in `docs/AGENTS_LOG.md`:

```markdown
| Demo 01's repo-selection criteria ("small enough to understand in one evening") | `docs/DEMO_01_CODEX_ITS_DANGEROUS.md` §1 | **Superseded** — those are criteria for a development rig; used to pick a corpus they produced 3/3 solved and a repo too small to show a harness effect | claude-code agent 2: `docs/superpowers/specs/2026-08-10-repo-screener-design.md` §1 |
```

- [ ] **Step 8: Add the artifacts to the Artifact index**

Append to the **Artifact index** table in `docs/AGENTS_LOG.md`:

```markdown
| `docs/superpowers/specs/2026-08-10-repo-screener-design.md` | claude-code agent 2 | Corpus repo selection: gates, metrics, candidate set |
| `screener/` | claude-code agent 2 | Two-tier screener. `metrics.py` is the harvestable stage-0 rule set |
| `screener/out/REPORT.md` | claude-code agent 2 | Gate ledger and ranking for 18 candidates |
```

- [ ] **Step 9: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add docs/AGENTS_LOG.md
git commit -m "docs: log repo screener session and corpus decision"
```

---

## Self-Review

**Spec coverage.** §1 framing → Task 9 log entry and spec reference. §2 architecture, clone rule, resumability → Tasks 1, 2, 5. §3.1 candidate-pair rule → Task 3. §3.2 metrics → Tasks 3–4. §3.3 gates G1–G7 → Task 5. §3.4 ranking → Task 5. §4.1 environment ladder → Task 7. §4.2 measurements → Task 8. §4.3 budgets → Task 8. §4.4 gates B1–B4 → Task 5 (`gates.py` holds both tiers). §5 candidate set → Task 1. §6 failure semantics → Tasks 1 and 5. §7 testing → Tasks 3–4. §8 output → Task 6. §9 open questions → carried into the Task 9 log entry.

**One deliberate deviation, recorded here rather than silently:** spec §3.2 lists `commits_180d`; the plan drops it in favour of `commits_since_cutoff`, which answers the same liveness question and is what G3 gates on. Two overlapping liveness counters would invite disagreement in the report.

**Two defects found and patched before execution:**

1. `cmd_tier_b` originally called `input()` unconditionally, which raises `EOFError` under any non-interactive runner. Replaced with `operator_minutes_for()`: takes `--operator-minutes NAME=N` when supplied, prompts only on a real terminal, and **fails closed** otherwise. Defaulting to 0 was rejected — spec §4.1 makes this a human judgement precisely because it is the services-trap indicator, and a silent 0 would read as free onboarding.
2. Docker `-v` used `Path(repo).resolve()`, producing a backslashed Windows path whose drive-letter colon collides with the `SRC:DEST` separator. Replaced with `tierb.host_path()` (forward slashes) plus `MSYS_NO_PATHCONV=1` in the subprocess environment as defence against shell-level path rewriting.

**Type consistency.** `Commit` fields used in `metrics.py` (`author`, `committer`, `subject`, `body`, `files`, `date`) match the dataclass in Task 2. `targeted_latency_warm` is the field name in Task 8's `measure`, in `budgets`, and in `report.B_COLUMNS`. `net_dependent_count` is produced by `measure` and consumed by `B_COLUMNS`; `net_dependent_tests` (the list) is what gate `_b4` counts. `projected_capsules` is written by `compute_tier_a` and read by `gates.rank` and `report`. `status`/`reason` are set by both sweep commands and read by `report`.
