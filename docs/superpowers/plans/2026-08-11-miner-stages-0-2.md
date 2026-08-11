# Miner Stages 0–2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn pydantic's git history into validated fail-to-pass candidates with evidence, and measure the two numbers several council rulings are conditional on — the real conversion rate and the curation cost per candidate.

**Architecture:** Stage 0 enumerates commits from the local clone using rules already written and tested in `screener/metrics.py`. Stage 1 scores and stratifies but never filters. Stage 2 splits each commit into a test patch and a code patch, applies them to the parent inside one long-lived container per repo-quarter, and diffs per-test outcomes to establish fail-to-pass.

**Tech Stack:** Python 3.14.4 (stdlib only), Git 2.53, Docker 29.3.1 (WSL2), pytest for the three tests.

**Spec:** `docs/superpowers/specs/2026-08-11-miner-stages-0-2-design.md`

**Branch:** create `feat/miner-stages-0-2` off `main` before Task 1.

## Global Constraints

- **Python 3.14.4**, invoked as `python`. Use the Bash tool (Git Bash), not PowerShell.
- **Standard library only** in `miner/`. No new third-party dependencies.
- **Import, never copy, from `screener/`.** `metrics.py` is the harvest target and must have one definition, not two that drift. Use a `sys.path` insert.
- **Exactly three unit tests**, all in `miner/tests/test_validate.py`: patch splitting, outcome diffing, failure classification. These cover the only logic that fails *silently*. Everything else is verified by running against real pydantic commits. Do not add a fourth.
- **Stage 1 kills nothing on score.** It orders and stratifies only. Pass-1 volume is a per-batch sampling budget that gets recorded, never a consequence of scoring.
- **Quarter images carry the dependency closure only, never pydantic itself.** If pydantic is in `site-packages`, a candidate checked out at another commit is not what gets imported and every result is silently wrong.
- **One container alive at a time.** Quarters run strictly sequentially.
- **Container caps**: `--memory=4g --memory-swap=4g --cpus=4 --pids-limit=512`, running as non-root (`tierb.DEFAULT_CONTAINER_USER`).
- **`rejected` and `apparatus` are different statuses.** A repo verdict is never recorded as our fault, and our fault is never recorded as a repo verdict.
- **Corpus repo** is `pydantic`, already cloned at `screener/work/pydantic`.

---

## File Structure

| File | Responsibility |
|---|---|
| `miner/record.py` | Record schema, JSONL append/read, resumability |
| `miner/candidates.py` | Stages 0–1: enumerate, score, stratify |
| `miner/validate.py` | Stage 2 pure logic: patch split, outcome diff, failure classification |
| `miner/quarters.py` | Repo-quarter profiles, image build, container lifecycle |
| `miner/runner.py` | Stage 2 orchestration: two passes over a quarter's candidates |
| `miner/report.py` | Funnel report |
| `miner/mine.py` | CLI: `enumerate`, `validate`, `report` |
| `miner/tests/test_validate.py` | The three tests |

`validate.py` holds pure functions and no I/O, which is why it is the only file with unit tests. `runner.py` holds the orchestration that touches containers.

---

## Task 1: Scaffold and record store

**Files:**
- Create: `miner/record.py`, `miner/mine.py`, `miner/.gitignore`, `miner/tests/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `ROOT`, `OUT`, `CANDIDATES`, `VALIDATED`, `LOGS` (all `pathlib.Path`)
  - `append(path, record: dict) -> None`
  - `read_all(path) -> dict[str, dict]` keyed by `sha`
  - `is_done(record: dict) -> bool`
  - `REPO = Path("screener/work/pydantic")` resolved absolute

- [ ] **Step 1: Create directories and branch**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git checkout main && git checkout -b feat/miner-stages-0-2
mkdir -p miner/tests miner/out/logs
```

- [ ] **Step 2: Write `miner/.gitignore`**

```
out/
work/
__pycache__/
```

- [ ] **Step 3: Write `miner/record.py`**

```python
"""Candidate records and the append-only JSONL store.

A record is keyed by the candidate commit sha. Statuses:
  validated          fail-to-pass established, assertion-class, regressions clean
  rejected:<reason>  a real verdict about the commit
  apparatus          our fault (OOM, build failure, patch would not apply)
  error              miner bug; traceback recorded, sweep continues

rejected and apparatus are kept rigidly separate. The screener's central
lesson was that six of seven eliminations were the apparatus rather than the
subject, and that was only visible because the two were recorded differently.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BENCH = ROOT.parent
REPO = BENCH / "screener" / "work" / "pydantic"
OUT = ROOT / "out"
CANDIDATES = OUT / "candidates.jsonl"
VALIDATED = OUT / "validated.jsonl"
LOGS = OUT / "logs"


def append(path, record):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def read_all(path):
    """Return {sha: record}; last write wins."""
    records = {}
    p = Path(path)
    if not p.exists():
        return records
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                records[rec["sha"]] = rec
    return records


def is_done(record):
    """error is NOT terminal -- a miner bug should be retried after a fix."""
    status = record.get("status", "")
    return status == "validated" or status == "apparatus" \
        or status.startswith("rejected:")
```

- [ ] **Step 4: Write `miner/mine.py`**

```python
"""BenchMe capsule miner, stages 0-2.

See docs/superpowers/specs/2026-08-11-miner-stages-0-2-design.md
"""
import argparse
import sys

import record


def cmd_enumerate(args):
    print("enumerate not implemented yet", file=sys.stderr)
    return 1


def cmd_validate(args):
    print("validate not implemented yet", file=sys.stderr)
    return 1


def cmd_report(args):
    print("report not implemented yet", file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mine")
    sub = parser.add_subparsers(dest="command", required=True)

    e = sub.add_parser("enumerate", help="stages 0-1 over the whole history")
    e.set_defaults(func=cmd_enumerate)

    v = sub.add_parser("validate", help="stage 2 for one repo-quarter")
    v.add_argument("--quarter", required=True, help="e.g. 2025Q3")
    v.add_argument("--limit", type=int, default=10,
                   help="sampling budget for this batch; recorded in the report")
    v.add_argument("--keep-images", action="store_true")
    v.add_argument("--force", action="store_true")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("report", help="render the funnel")
    r.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    for d in (record.OUT, record.LOGS):
        d.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Verify the CLI runs and the repo is where we expect**

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
python mine.py enumerate
python -c "import record; print('repo exists:', record.REPO.exists()); print(record.REPO)"
```

Expected: `enumerate not implemented yet` on stderr with exit 1, then `repo exists: True`.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add miner/record.py miner/mine.py miner/.gitignore miner/tests/__init__.py
git commit -m "feat(miner): scaffold, record store, CLI skeleton"
```

---

## Task 2: Stages 0 and 1 — enumerate, score, stratify

**Files:**
- Create: `miner/candidates.py`
- Modify: `miner/mine.py` (replace `cmd_enumerate`)

**Interfaces:**
- Consumes: `record.REPO`, `record.CANDIDATES`, `record.append`; `screener/metrics.py` and `screener/gitmeta.py` via `sys.path`
- Produces:
  - `quarter_of(iso_date: str) -> str` — `"2025-07-14T..."` → `"2025Q3"`
  - `subsystem_of(files: list[str]) -> str`
  - `enumerate_candidates(repo) -> list[dict]` — stage-0 survivors with stage-1 scores
  - `stratified_order(records: list[dict]) -> list[dict]` — round-robin across `(subsystem, size_bucket)`

- [ ] **Step 1: Write `miner/candidates.py`**

```python
"""Stages 0 and 1: enumerate candidates, score them, stratify the queue.

Stage 1 KILLS NOTHING. The handoff names the hazard directly: "Ranking biases
the corpus, and the bias is the falsification risk." Scoring for "small diff,
test-rich, clean flip" builds a suite of small easy tasks -- exactly the
representativeness failure in the project's own kill criteria. So the queue is
a stratified sample, and how much of it we run is a recorded budget decision.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import gitmeta  # noqa: E402
import metrics  # noqa: E402

import record  # noqa: E402

REVERT_SUBJECT = re.compile(r'^Revert "(?P<orig>.+)"')
SIZE_BUCKETS = ((2, "xs"), (4, "s"), (7, "m"))  # else "l"


def quarter_of(iso_date):
    year = int(iso_date[0:4])
    month = int(iso_date[5:7])
    return f"{year}Q{(month - 1) // 3 + 1}"


def size_bucket(n_files):
    for limit, name in SIZE_BUCKETS:
        if n_files <= limit:
            return name
    return "l"


def subsystem_of(files):
    """Top-level area under pydantic/. pydantic/v1 is its own stratum: it is a
    vendored compatibility tree duplicating most module names, and mixed in
    undifferentiated a batch could come back mostly from a shim nobody
    actively develops. It is also what broke the screener's test_map_ratio."""
    for f in files:
        if not metrics.is_source_file(f):
            continue
        parts = f.split("/")
        if parts[0] == "pydantic":
            if len(parts) > 2 and parts[1] == "v1":
                return "pydantic/v1"
            if len(parts) > 2:
                return f"pydantic/{parts[1]}"
            return "pydantic"
        return parts[0]
    return "unknown"


def _numstat(repo, parent, sha, paths):
    """Added/deleted line totals for the given paths. Needs blobs, which the
    local clone has after its lazy fetch -- this is the miner on a local
    clone, not the screener's blobless sweep."""
    if not paths:
        return 0, 0
    cmd = ["git", "diff", "--numstat", parent, sha, "--", *paths]
    proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    added = deleted = 0
    for line in proc.stdout.splitlines():
        cols = line.split("\t")
        if len(cols) >= 2 and cols[0].isdigit() and cols[1].isdigit():
            added += int(cols[0])
            deleted += int(cols[1])
    return added, deleted


def enumerate_candidates(repo):
    commits = gitmeta.log_commits(repo)
    by_sha = {c.sha: c for c in commits}

    reverted_subjects = set()
    for c in commits:
        m = REVERT_SUBJECT.match(c.subject)
        if m:
            reverted_subjects.add(m.group("orig").strip())

    # later commits touching the same file within 48h -> hotfix signal
    out = []
    for c in commits:
        if not metrics.is_candidate_pair(c):
            continue
        if not c.parents:
            continue
        parent = c.parents[0]
        if parent not in by_sha and len(c.parents) != 1:
            continue

        tests = [f for f in c.files if metrics.is_test_file(f)]
        sources = [f for f in c.files if metrics.is_source_file(f)]

        t_add, t_del = _numstat(repo, parent, c.sha, tests)
        if t_add == 0:
            continue  # deletion-only test change: no fail-to-pass to offer
        if REVERT_SUBJECT.match(c.subject):
            continue  # a revert of another candidate; same behaviour twice

        s_add, s_del = _numstat(repo, parent, c.sha, sources)

        out.append({
            "sha": c.sha,
            "parent": parent,
            "date": c.date,
            "quarter": quarter_of(c.date),
            "subject": c.subject[:200],
            "files": c.files,
            "test_files": tests,
            "source_files": sources,
            "n_files": len(c.files),
            "size_bucket": size_bucket(len(c.files)),
            "subsystem": subsystem_of(c.files),
            "test_lines_added": t_add,
            "source_lines_added": s_add,
            "test_source_ratio": round(t_add / s_add, 3) if s_add else None,
            "reverted_later": c.subject.strip() in reverted_subjects,
            "status": "enumerated",
        })
    return out


def stratified_order(records):
    """Round-robin across (subsystem, size_bucket) so a small batch is not
    drawn from one easy corner of the distribution."""
    strata = {}
    for r in records:
        strata.setdefault((r["subsystem"], r["size_bucket"]), []).append(r)
    for group in strata.values():
        group.sort(key=lambda r: r["date"], reverse=True)
    ordered, keys = [], sorted(strata)
    while any(strata[k] for k in keys):
        for k in keys:
            if strata[k]:
                ordered.append(strata[k].pop(0))
    return ordered
```

- [ ] **Step 2: Wire `cmd_enumerate` in `miner/mine.py`**

Replace the `cmd_enumerate` stub with:

```python
def cmd_enumerate(args):
    import candidates

    rows = candidates.enumerate_candidates(record.REPO)
    ordered = candidates.stratified_order(rows)
    record.CANDIDATES.unlink(missing_ok=True)
    for r in ordered:
        record.append(record.CANDIDATES, r)

    by_q = {}
    for r in ordered:
        by_q[r["quarter"]] = by_q.get(r["quarter"], 0) + 1
    print(f"enumerated {len(ordered)} candidates")
    for q in sorted(by_q, reverse=True)[:12]:
        print(f"  {q}: {by_q[q]}")
    return 0
```

- [ ] **Step 3: Run it against real pydantic and read the output**

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
time python mine.py enumerate
```

Expected: a candidate count and a per-quarter breakdown. The screener counted 1,597 candidate pairs across all history; this number will be **lower**, because deletion-only test changes and reverts are now excluded. Report the actual figure and the difference — that gap is the first real measurement of this build.

- [ ] **Step 4: Sanity-check the stratification**

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
python -c "
import json, collections
rows=[json.loads(l) for l in open('out/candidates.jsonl',encoding='utf-8')]
print('total', len(rows))
print('subsystems:', collections.Counter(r['subsystem'] for r in rows).most_common(8))
print('sizes:', collections.Counter(r['size_bucket'] for r in rows))
print('first 10 strata:', [(r['subsystem'], r['size_bucket']) for r in rows[:10]])
"
```

Expected: the first ten candidates come from **different** `(subsystem, size_bucket)` pairs, not ten of the same. If they are all the same stratum, `stratified_order` is wrong — fix it before continuing, because every later batch inherits this ordering.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add miner/candidates.py miner/mine.py
git commit -m "feat(miner): stages 0-1 enumerate, score, stratify"
```

---

## Task 3: Patch splitting and outcome diffing

**Files:**
- Create: `miner/validate.py`
- Create: `miner/tests/test_validate.py`

**Interfaces:**
- Consumes: `metrics.is_test_file`
- Produces:
  - `split_paths(files: list[str]) -> tuple[list[str], list[str]]` — `(test_paths, code_paths)`
  - `make_patch(repo, parent, sha, paths) -> str` — unified diff text, `""` if no paths
  - `diff_outcomes(before: dict, after: dict) -> dict` with keys `f2p`, `p2p`, `broken` (each a sorted list of node ids)

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate  # noqa: E402


def test_split_paths_separates_tests_from_code():
    files = [
        "pydantic/main.py",
        "tests/test_main.py",
        "pydantic/_internal/_fields.py",
        "tests/benchmarks/test_north_star.py",
        "docs/index.md",
    ]
    tests, code = validate.split_paths(files)
    assert tests == ["tests/benchmarks/test_north_star.py", "tests/test_main.py"]
    assert code == ["docs/index.md", "pydantic/_internal/_fields.py",
                    "pydantic/main.py"]
    assert not set(tests) & set(code)


def test_diff_outcomes_classifies_each_test():
    before = {
        "tests/test_a.py::test_new": "FAILED",
        "tests/test_a.py::test_old": "PASSED",
        "tests/test_a.py::test_breaks": "PASSED",
        "tests/test_a.py::test_skipped": "SKIPPED",
    }
    after = {
        "tests/test_a.py::test_new": "PASSED",
        "tests/test_a.py::test_old": "PASSED",
        "tests/test_a.py::test_breaks": "FAILED",
        "tests/test_a.py::test_skipped": "SKIPPED",
    }
    result = validate.diff_outcomes(before, after)
    assert result["f2p"] == ["tests/test_a.py::test_new"]
    assert result["p2p"] == ["tests/test_a.py::test_old"]
    assert result["broken"] == ["tests/test_a.py::test_breaks"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest miner/tests/test_validate.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'validate'`.

- [ ] **Step 3: Write `miner/validate.py`**

```python
"""Stage 2 pure logic. No I/O, no containers -- which is why this is the only
file in the miner with unit tests. Each function here fails SILENTLY if wrong:
a bad patch split hands the agent the answer or strips the fix; a bad outcome
diff records the wrong tests as the oracle.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import metrics  # noqa: E402


def split_paths(files):
    """(test_paths, code_paths), both sorted. Uses the same is_test_file rule
    the screener and stage 0 use, so a file cannot be a test here and source
    there."""
    tests = sorted(f for f in files if metrics.is_test_file(f))
    code = sorted(f for f in files if not metrics.is_test_file(f))
    return tests, code


def make_patch(repo, parent, sha, paths):
    """Unified diff for `paths` between parent and sha. Empty string when
    there are no paths, so callers can skip `git apply` entirely."""
    if not paths:
        return ""
    proc = subprocess.run(
        ["git", "diff", "--binary", parent, sha, "--", *paths],
        cwd=str(repo), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed for {sha[:8]}: {proc.stderr[:300]}")
    return proc.stdout


def diff_outcomes(before, after):
    """f2p  -- failed before, passed after (the oracle)
    p2p    -- passed on both sides (the regression set)
    broken -- passed before, failed after (the code patch broke something)

    Only PASSED and FAILED participate. SKIPPED and ERROR are deliberately
    excluded from all three: a skipped test proves nothing, and an errored
    test is an apparatus signal handled by the caller.
    """
    f2p, p2p, broken = [], [], []
    for nodeid, before_outcome in before.items():
        after_outcome = after.get(nodeid)
        if before_outcome == "FAILED" and after_outcome == "PASSED":
            f2p.append(nodeid)
        elif before_outcome == "PASSED" and after_outcome == "PASSED":
            p2p.append(nodeid)
        elif before_outcome == "PASSED" and after_outcome == "FAILED":
            broken.append(nodeid)
    return {"f2p": sorted(f2p), "p2p": sorted(p2p), "broken": sorted(broken)}
```

- [ ] **Step 4: Run to verify they pass**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest miner/tests/test_validate.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add miner/validate.py miner/tests/test_validate.py
git commit -m "feat(miner): patch splitting and outcome diffing"
```

---

## Task 4: Failure classification

The third and final test. This one is written against **real captured pytest output**, not against a guess at its format — get the sample first, then write the test.

**Files:**
- Modify: `miner/validate.py`
- Modify: `miner/tests/test_validate.py`

**Interfaces:**
- Consumes: nothing new
- Produces:
  - `FAILURE_CLASSES = {"assertion", "missing_api", "structural"}`
  - `parse_failures(stdout: str) -> dict[str, str]` — node id → exception type name
  - `classify(exc_name: str) -> str` — `"assertion"` | `"missing_api"` | `"structural"` | `"other:<Exc>"`

- [ ] **Step 1: Capture real pytest short-summary output**

Create a throwaway file and run pytest on it so the test is written against the true format rather than an assumed one:

```bash
cd /c/Users/Srijan/Documents/BenchMe
mkdir -p /tmp/fmt && cat > /tmp/fmt/test_sample.py <<'PY'
def test_assertion():
    assert 1 == 2

def test_missing_attr():
    import json
    json.this_does_not_exist()

def test_missing_import():
    import a_module_that_does_not_exist  # noqa: F401
PY
python -m pytest /tmp/fmt/test_sample.py -v -p no:randomly --tb=no -rf 2>&1 | tail -12
```

Record the exact `FAILED ...` summary lines. They are the input the test will use.

- [ ] **Step 2: Append the failing test using the captured lines**

Add to `miner/tests/test_validate.py`, substituting the exact lines captured in Step 1 for `SAMPLE` if they differ from what is written here:

```python
SAMPLE = """
=========================== short test summary info ============================
FAILED test_sample.py::test_assertion - assert 1 == 2
FAILED test_sample.py::test_missing_attr - AttributeError: module 'json' has no attribute 'this_does_not_exist'
FAILED test_sample.py::test_missing_import - ModuleNotFoundError: No module named 'a_module_that_does_not_exist'
"""


def test_parse_and_classify_failures():
    parsed = validate.parse_failures(SAMPLE)
    assert validate.classify(parsed["test_sample.py::test_missing_attr"]) \
        == "missing_api"
    assert validate.classify(parsed["test_sample.py::test_missing_import"]) \
        == "missing_api"
    assert validate.classify(parsed["test_sample.py::test_assertion"]) \
        == "assertion"
    assert validate.classify("SyntaxError") == "structural"
    assert validate.classify("ValueError") == "other:ValueError"
```

A bare `assert` failure prints no exception name — pytest writes `- assert 1 == 2`. `parse_failures` must map that to `AssertionError` so it classifies as `assertion`.

- [ ] **Step 3: Run to verify it fails**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest miner/tests/test_validate.py::test_parse_and_classify_failures -v
```

Expected: FAIL — `AttributeError: module 'validate' has no attribute 'parse_failures'`.

- [ ] **Step 4: Append to `miner/validate.py`**

```python
import re

# pytest's short summary line, e.g.
#   FAILED tests/test_x.py::test_y - AttributeError: no attribute 'z'
#   FAILED tests/test_x.py::test_y - assert 1 == 2
# Node ids can contain spaces inside parametrised brackets, so the node id is
# matched non-greedily up to the " - " separator rather than as \S+. The
# screener learned this the hard way: a \S+ node-id pattern silently dropped
# 1,604 of 1,977 tests.
FAILED_LINE = re.compile(r"^FAILED (?P<nodeid>.+?) - (?P<detail>.*)$", re.M)
EXC_NAME = re.compile(r"^(?P<exc>[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Exit))\b")

MISSING_API = {"AttributeError", "ImportError", "ModuleNotFoundError",
               "NameError"}
STRUCTURAL = {"SyntaxError", "IndentationError", "TabError",
              "CollectionError", "Collection"}
FAILURE_CLASSES = {"assertion", "missing_api", "structural"}


def parse_failures(stdout):
    """node id -> exception type name, from pytest's short summary.

    A bare `assert` prints no exception name at all, so it is mapped to
    AssertionError explicitly rather than falling through to `other:`.
    """
    out = {}
    for m in FAILED_LINE.finditer(stdout):
        detail = m.group("detail").strip()
        exc = EXC_NAME.match(detail)
        out[m.group("nodeid").strip()] = exc.group("exc") if exc else "AssertionError"
    return out


def classify(exc_name):
    """Per the council contract: only assertion failures qualify as a valid
    base negative. missing_api and structural are rejected -- but counted by
    class, because the assertion-only rule filters out feature work (a new
    feature's test fails at the parent with AttributeError) and we need to
    know what that costs in yield before assuming the rule was right.
    """
    if exc_name == "AssertionError":
        return "assertion"
    if exc_name in MISSING_API:
        return "missing_api"
    if exc_name in STRUCTURAL:
        return "structural"
    return f"other:{exc_name}"
```

- [ ] **Step 5: Run the full suite**

```bash
cd /c/Users/Srijan/Documents/BenchMe
python -m pytest miner/tests/test_validate.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
rm -rf /tmp/fmt
git add miner/validate.py miner/tests/test_validate.py
git commit -m "feat(miner): failure classification with assertion-only rule"
```

---

## Task 5: Repo-quarter profiles and container lifecycle

**Files:**
- Create: `miner/quarters.py`

**Interfaces:**
- Consumes: `screener/tierb.py` — `host_path`, `docker_env`, `BASE_IMAGE`, `DEFAULT_CONTAINER_USER`, `_EXPORT`
- Produces:
  - `anchor_commit(repo, quarter) -> str` — last commit sha within that quarter
  - `build_quarter_image(repo, quarter, log_dir) -> str | None` — image tag, or None on failure
  - `start_container(image, name) -> str | None` — container id
  - `exec_in(container, argv, timeout=1800) -> subprocess.CompletedProcess`
  - `stop_container(container) -> None`
  - `remove_image(tag) -> None`
  - `preflight() -> str | None` — human-readable reason to refuse, or None

- [ ] **Step 1: Write `miner/quarters.py`**

```python
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
```

- [ ] **Step 2: Build one real quarter image and confirm pydantic is absent**

Use `2025Q3` — comfortably after pydantic replaced pdm with uv at commit `53bf2f2`, so `uv.lock` exists and no pdm fallback is needed.

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
python -c "
import quarters, record
print('preflight:', quarters.preflight() or 'ok')
print('anchor:', quarters.anchor_commit(record.REPO, '2025Q3'))
tag = quarters.build_quarter_image(record.REPO, '2025Q3', 'out/logs')
print('image:', tag)
"
```

Expected: an anchor sha and an image tag. On failure read `miner/out/logs/build-2025Q3.log`.

- [ ] **Step 3: Verify the image has the dependencies but NOT pydantic**

This is the check that matters most in the whole plan.

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
python -c "
import quarters
cid = quarters.start_container('benchme-miner/pydantic:2025q3', 'miner-check')
print('container:', cid[:12] if cid else None)
r = quarters.exec_in(cid, ['python','-c','import pydantic; print(pydantic.__file__)'])
print('pydantic import rc:', r.returncode, '| out:', (r.stdout+r.stderr).strip()[:120])
r2 = quarters.exec_in(cid, ['python','-c','import pydantic_core, typing_extensions; print(\"deps ok\")'])
print('deps:', (r2.stdout+r2.stderr).strip()[:120])
quarters.stop_container(cid)
"
```

Expected: importing `pydantic` **FAILS** with `ModuleNotFoundError`, and importing `pydantic_core` **SUCCEEDS**. If pydantic imports, the image is wrong — fix the Dockerfile before continuing, because every downstream result would be about the wrong code.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add miner/quarters.py
git commit -m "feat(miner): repo-quarter profiles and container lifecycle"
```

---

## Task 6: Stage 2 orchestration

**Files:**
- Create: `miner/runner.py`
- Modify: `miner/mine.py` (replace `cmd_validate`)

**Interfaces:**
- Consumes: `validate.split_paths/make_patch/diff_outcomes/parse_failures/classify`, `quarters.*`, `record.*`, `tierb.parse_outcomes`, `tierb.PYTEST_ARGV`
- Produces: `validate_quarter(quarter, limit, keep_images, force) -> dict` summary counts

- [ ] **Step 1: Write `miner/runner.py`**

```python
"""Stage 2 orchestration: two passes over one quarter's candidates.

Pass 1 runs only the test files the commit touched -- cheap, and it eliminates
most candidates. Pass 2 runs the full suite on survivors only, to establish the
pass-to-pass set and catch a code patch that breaks something elsewhere.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import tierb  # noqa: E402

import quarters  # noqa: E402
import record  # noqa: E402
import validate  # noqa: E402

BEFORE, AFTER = "before", "after"


def _checkout(container, sha, workdir):
    r = quarters.exec_in(container, ["git", "clone", "--quiet", "--no-checkout",
                                     "/repo", workdir])
    if r.returncode != 0:
        return f"clone failed: {(r.stdout + r.stderr)[:200]}"
    r = quarters.exec_in(container, ["git", "-C", workdir, "checkout", "--quiet", sha])
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
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "sh", "-c", f"cat > {path}"],
        input=patch_text, capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=tierb.docker_env())
    if proc.returncode != 0:
        return f"could not write {label} patch"
    r = quarters.exec_in(container, ["git", "-C", workdir, "apply", "--3way", path])
    if r.returncode != 0:
        return f"{label} patch would not apply: {(r.stdout + r.stderr)[:200]}"
    return None


def _pytest(container, workdir, targets, log_path, timeout=1800):
    argv = ["sh", "-c",
            "cd {wd} && PYTHONPATH={wd} python -m pytest -v -p no:randomly "
            "--tb=no -rf {t} 2>&1".format(wd=workdir, t=" ".join(targets))]
    r = quarters.exec_in(container, argv, timeout=timeout)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(log_path).write_text(r.stdout + r.stderr, encoding="utf-8")
    return r.stdout + r.stderr


def validate_one(container, cand, repo, pass2=False):
    """Returns a record dict. Never raises for a candidate-level problem."""
    sha, parent = cand["sha"], cand["parent"]
    out = dict(cand)
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

    test_patch = validate.make_patch(repo, parent, sha, tests)
    code_patch = validate.make_patch(repo, parent, sha, code)

    err = _apply(container, workdir, test_patch, "test")
    if err:
        out.update(status="apparatus", reason=err)
        return out

    targets = tests if not pass2 else ["tests"]
    before_out = _pytest(container, workdir, targets, logs / "before.log")
    before = tierb.parse_outcomes(before_out)
    failures = validate.parse_failures(before_out)

    err = _apply(container, workdir, code_patch, "code")
    if err:
        out.update(status="apparatus", reason=err)
        return out

    after_out = _pytest(container, workdir, targets, logs / "after.log")
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

    all_c = [json.loads(l) for l in open(record.CANDIDATES, encoding="utf-8")
             if l.strip()]
    done = record.read_all(record.VALIDATED)
    queue = [c for c in all_c if c["quarter"] == quarter
             and (force or c["sha"] not in done or not record.is_done(done[c["sha"]]))]
    queue = queue[:limit]
    if not queue:
        print(f"nothing to do for {quarter}")
        return {}

    tag = quarters.build_quarter_image(record.REPO, quarter, record.LOGS)
    if not tag:
        raise SystemExit(f"image build failed for {quarter}; see out/logs/build-{quarter}.log")
    cid = quarters.start_container(tag, f"miner-{quarter.lower()}")
    if not cid:
        raise SystemExit(f"container would not start for {quarter}")

    counts = {}
    try:
        survivors = []
        for cand in queue:
            rec = validate_one(cid, cand, record.REPO, pass2=False)
            if rec["status"] == "pass1_ok":
                survivors.append(cand)
            else:
                record.append(record.VALIDATED, rec)
                counts[rec["status"]] = counts.get(rec["status"], 0) + 1
                print(f"  {cand['sha'][:8]} {rec['status']} {rec.get('reason') or ''}")
        for cand in survivors:
            rec = validate_one(cid, cand, record.REPO, pass2=True)
            record.append(record.VALIDATED, rec)
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
            print(f"  {cand['sha'][:8]} {rec['status']} {rec.get('reason') or ''}")
    finally:
        quarters.stop_container(cid)
        if not keep_images:
            quarters.remove_image(tag)
    return counts
```

- [ ] **Step 2: Mount the repo into the container**

`_checkout` clones from `/repo`, so `start_container` must mount it. Edit `miner/quarters.py`'s `start_container` docker argv, adding the mount immediately before `"-w", "/work"`:

```python
         "-v", f"{tierb.host_path(Path(__file__).resolve().parents[1] / 'screener' / 'work' / 'pydantic')}:/repo:ro",
```

- [ ] **Step 3: Wire `cmd_validate` in `miner/mine.py`**

```python
def cmd_validate(args):
    import runner

    counts = runner.validate_quarter(args.quarter, args.limit,
                                     args.keep_images, args.force)
    print(f"\n{args.quarter} summary (budget {args.limit}):")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")
    return 0
```

- [ ] **Step 4: Run against ONE real candidate end to end**

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
python mine.py validate --quarter 2025Q3 --limit 1 --keep-images
```

Expected: one status line. Then read both logs verbatim — this is the acceptance check for the whole plan:

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
SHA=$(python -c "
import json
r=[json.loads(l) for l in open('out/validated.jsonl',encoding='utf-8')][-1]
print(r['sha'][:12], r['status'], r.get('reason'))" | cut -d' ' -f1)
echo '--- BEFORE (tail) ---'; tail -20 out/logs/$SHA/before.log
echo '--- AFTER (tail) ---';  tail -20 out/logs/$SHA/after.log
```

Expected: the before log shows failures, the after log shows them passing. If both sides are empty, `parse_outcomes` saw nothing — check the pytest invocation before assuming anything about the candidate.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add miner/runner.py miner/mine.py miner/quarters.py
git commit -m "feat(miner): stage 2 two-pass orchestration"
```

---

## Task 7: Funnel report and the first real batch

**Files:**
- Create: `miner/report.py`
- Modify: `miner/mine.py` (replace `cmd_report`)

**Interfaces:**
- Consumes: `record.CANDIDATES`, `record.VALIDATED`
- Produces: `render() -> str`

- [ ] **Step 1: Write `miner/report.py`**

```python
"""Funnel report. Every rejection appears with its class -- especially
missing_api, which is the number that tells us what the assertion-only rule
actually cost in yield.
"""
import json
from collections import Counter

import record


def render():
    cands = [json.loads(l) for l in open(record.CANDIDATES, encoding="utf-8")
             if l.strip()] if record.CANDIDATES.exists() else []
    done = list(record.read_all(record.VALIDATED).values())

    out = ["# Miner funnel — stages 0–2", ""]
    out.append(f"- Candidates enumerated: **{len(cands)}**")
    out.append(f"- Attempted in stage 2: **{len(done)}**")
    validated = [d for d in done if d["status"] == "validated"]
    out.append(f"- Validated: **{len(validated)}**")
    if done:
        rate = 100 * len(validated) / len(done)
        out.append(f"- Conversion on attempted: **{rate:.1f}%** "
                   f"(screener assumed 2.2% on raw pairs)")
    out.append("")

    out.append("## Verdicts")
    out.append("")
    out.append("| status | count |")
    out.append("|---|---|")
    for status, n in Counter(d["status"] for d in done).most_common():
        out.append(f"| `{status}` | {n} |")
    out.append("")

    apparatus = [d for d in done if d["status"] == "apparatus"]
    if apparatus:
        out.append("## Apparatus failures — our fault, not the repo's")
        out.append("")
        for d in apparatus[:15]:
            out.append(f"- `{d['sha'][:8]}` {d.get('reason')}")
        out.append("")

    out.append("## Candidates by quarter")
    out.append("")
    out.append("| quarter | candidates |")
    out.append("|---|---|")
    for q, n in sorted(Counter(c["quarter"] for c in cands).items(),
                       reverse=True)[:12]:
        out.append(f"| {q} | {n} |")
    out.append("")

    if validated:
        out.append("## Validated candidates")
        out.append("")
        out.append("| sha | subsystem | size | f2p tests | subject |")
        out.append("|---|---|---|---|---|")
        for d in validated:
            out.append(f"| `{d['sha'][:8]}` | {d['subsystem']} | "
                       f"{d['size_bucket']} | {len(d.get('f2p', []))} | "
                       f"{d['subject'][:60]} |")
    return "\n".join(out) + "\n"
```

- [ ] **Step 2: Wire `cmd_report` in `miner/mine.py`**

```python
def cmd_report(args):
    import report

    text = report.render()
    path = record.OUT / "REPORT.md"
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")
    return 0
```

- [ ] **Step 3: Run the first real batch of ten**

```bash
cd /c/Users/Srijan/Documents/BenchMe/miner
time python mine.py validate --quarter 2025Q3 --limit 10
python mine.py report && cat out/REPORT.md
```

Report the actual numbers. **Do not tune anything to improve them.** In particular: if `missing_api` is a large share, that is a finding about the assertion-only rule and belongs back at the council, not a reason to loosen the classifier.

- [ ] **Step 4: STOP and present raw output for review**

Do not proceed to further quarters. Present:

- the funnel report;
- rejection counts by class, with `missing_api` called out;
- verbatim before/after pytest tails for two or three candidates, including at least one rejected one, so the classifier's calls can be judged rather than trusted;
- wall-clock for the batch and the implied per-candidate cost.

- [ ] **Step 5: Commit**

```bash
cd /c/Users/Srijan/Documents/BenchMe
git add miner/report.py miner/mine.py
git add -f miner/out/REPORT.md miner/out/validated.jsonl
git commit -m "feat(miner): funnel report; first 2025Q3 batch results"
```

---

## Self-Review

**Spec coverage.** §1 scope and the two deliverable numbers → Tasks 3, 7. §2 architecture and reuse → Tasks 1, 2, 5, 6. §3 stage 0 additions (deletion-only, revert) → Task 2. §3 stage 1 scoring and stratification, `pydantic/v1` as its own stratum → Task 2. §4.1 dependency-closure-only images → Task 5, with Step 3 as an explicit verification. §4.2 patch splitting → Task 3. §4.3 outcome diffing → Task 3. §4.4 two passes → Task 6. §4.5 failure classification and counting by class → Tasks 4, 7. §4.6 container lifecycle → Tasks 5, 6. §5 resource caps and preflight → Task 5. §5 failure semantics → Task 1 (`record.py` docstring), Task 6. §6 the three tests → Tasks 3, 4. §7 stop-after-first-quarter review → Task 7 Step 4. §8 open questions carry into the review.

**Placeholder scan.** No TBDs, no "handle edge cases", no "similar to Task N". Every code step carries real code. Task 4 Step 1 deliberately captures real pytest output before the test is written rather than asserting a format I have not verified.

**Type consistency.** `record.append(path, record_dict)` and `record.read_all(path)` are used with those signatures in Tasks 2, 6, 7. `validate.split_paths` returns `(tests, code)` in that order, consumed that way in Task 6. `validate.diff_outcomes` returns keys `f2p`/`p2p`/`broken`, read with those names in `runner.validate_one`. `quarters.exec_in(container, argv, timeout)` is called with that signature throughout Task 6. `tierb.parse_outcomes(stdout)` and `tierb.PYTEST_ARGV` match the definitions verified in `screener/tierb.py`. Candidate dicts carry `sha`, `parent`, `files`, `quarter`, `subsystem`, `size_bucket`, `subject` from Task 2 and are read by those names in Tasks 6 and 7.

**One deviation from the spec, recorded here.** The spec's §4.4 describes pass 1 as running "touched test files". `runner._pytest` passes those paths directly to pytest, which means pass 2 runs `tests` (the whole directory) rather than a computed full-suite path. That is the intended behaviour and matches the spec's "full suite on survivors only", but the mechanism is a different argument rather than a different function.
