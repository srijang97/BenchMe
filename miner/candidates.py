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

# Paths that satisfy metrics.is_test_file but are not pytest tests, so
# pointing pytest at them collects nothing and the candidate books as
# apparatus. Deliberately explicit per-repo config rather than a heuristic:
# a heuristic that guessed wrong would silently drop real tests, and the
# whole point of this redesign is that our defects must not become verdicts.
#
# pydantic/tests/typechecking: static type-checker fixtures, asserted by mypy
# and pyright, never executed by pytest. Eight of ten apparatus cases in the
# first 2025Q3 batch.
NON_PYTEST_TEST_DIRS = {
    # tests/mypy: found by the 2025Q3 re-run, not by inspection. Its
    # modules/ and outputs/ trees are mypy plugin fixtures -- pointing pytest
    # at them collects 0 items and reports errors, which the old code booked
    # as apparatus and (after the empty-targets fix) would book as apparatus
    # again. Adding it here keeps those candidates out of the funnel entirely
    # rather than spending a container slot to discover the same thing.
    "pydantic": ("tests/typechecking/", "tests/mypy/"),
}


def is_non_pytest_test(repo_name, path):
    # The trailing slash is normalised here rather than trusted in the table
    # above. An entry written "tests/typechecking" would otherwise also match
    # "tests/typechecking_extra/", silently dropping real pytest tests from a
    # candidate's targets -- our defect turning into a verdict about the
    # commit, which is the one thing this filter must not do.
    return any(path.startswith(prefix if prefix.endswith("/") else prefix + "/")
               for prefix in NON_PYTEST_TEST_DIRS.get(repo_name, ()))


# Explicit per-repo, never inferred. A heuristic that guessed wrong would
# silently drop real candidates, which is the failure class this whole phase
# exists to remove.
EXPECTED_PROJECT = {"pydantic": "pydantic"}

_NAME = re.compile(r"""^\s*name\s*=\s*['"]([^'"]+)['"]""", re.M)
_PIN = re.compile(r"""['"]([A-Za-z0-9._-]+)==([0-9][^'"]*)['"]""")


def project_name(pyproject_text):
    """The [project] name, or None when there is no pyproject.toml at all.

    None is NOT foreignness: pydantic v1 predates pyproject.toml entirely.
    """
    m = _NAME.search(pyproject_text or "")
    return m.group(1) if m else None


def exact_pins(pyproject_text):
    """{name: version} for `name==version` pins only.

    Ranges are excluded deliberately. A `>=` bound that moves does not force a
    different environment; an exact pin does.
    """
    return {n: v for n, v in _PIN.findall(pyproject_text or "")}


def not_minable_reason(repo_name, parent_toml, commit_toml, test_files=None):
    """Why this candidate is outside what the method can measure, or None."""
    expected = EXPECTED_PROJECT.get(repo_name)
    if expected:
        actual = project_name(commit_toml)
        if actual is not None and actual.replace("-", "_") != expected.replace("-", "_"):
            return "foreign_project"
    before, after = exact_pins(parent_toml), exact_pins(commit_toml)
    for name, version in after.items():
        if name in before and before[name] != version:
            return "straddles_dependency_bump"
    if test_files:
        test_py = [f for f in test_files if metrics.is_test_file(f)]
        if test_py and all(is_non_pytest_test(repo_name, f) for f in test_py):
            return "no_pytest_tests"
    return None


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
    clone, not the screener's blobless sweep.

    Raises RuntimeError on a non-zero git exit rather than returning (0, 0).
    The caller reads a zero `added` as "deletion-only test change" and drops
    the commit, so a silent zero would record an apparatus failure -- a
    missing blob, a bad pathspec, a locked index, a re-clone with
    --filter=blob:none against an unreachable promisor -- as a verdict about
    the commit. That confusion is the failure class this project has already
    hit seven times, and it is why gitmeta.log_commits raises here too.
    """
    if not paths:
        return 0, 0
    cmd = ["git", "diff", "--numstat", parent, sha, "--", *paths]
    proc = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(
            f"git diff --numstat failed ({proc.returncode}) for {sha} "
            f"against {parent} in {repo}: {proc.stderr.strip()[:500]}")
    added = deleted = 0
    for line in proc.stdout.splitlines():
        cols = line.split("\t")
        if len(cols) >= 2 and cols[0].isdigit() and cols[1].isdigit():
            added += int(cols[0])
            deleted += int(cols[1])
    return added, deleted


def _read_pyprojects(repo, pairs):
    """pyproject.toml text at each parent and commit, in ONE batched call.

    Returns {spec: text} where spec is "<rev>:pyproject.toml" and text is ""
    when that tree has no pyproject.toml. Absence is NOT foreignness (pydantic
    v1 predates pyproject.toml entirely) and NOT a pin change; the caller's
    negative tests depend on "" flowing through exactly like a real file.

    Raises RuntimeError on any shape the batch cannot vouch for. The clone is
    blobless (--filter=blob:none), so a blob that is not local is fetched
    lazily on demand; if the promisor is unreachable the batch dies partway,
    and returning the partial map would read the missing entries as "no
    pyproject.toml" -- silently dropping the very candidates this filter
    exists to count. The size-delimited parse also means a truncated batch is
    detected rather than mis-read.
    """
    specs = [f"{rev}:pyproject.toml" for parent, sha in pairs
             for rev in (parent, sha)]
    proc = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=str(repo),
        input=("\n".join(specs) + "\n").encode("utf-8"), capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"git cat-file --batch failed (rc={proc.returncode}) reading "
            f"{len(specs)} pyproject.toml paths: "
            f"{proc.stderr.decode('utf-8', 'replace').strip()[:500]}")
    blobs = {}
    stream = proc.stdout
    pos = 0
    for spec in specs:
        end = stream.find(b"\n", pos)
        if end == -1:
            raise RuntimeError("git cat-file --batch output truncated before "
                               f"a header for {spec!r}")
        header = stream[pos:end]
        pos = end + 1
        if header.endswith(b" missing"):
            blobs[spec] = ""
            continue
        parts = header.split(b" ")
        if len(parts) != 3 or parts[1] != b"blob":
            raise RuntimeError(
                f"unexpected git cat-file --batch header {header!r} for "
                f"{spec!r}")
        try:
            size = int(parts[2])
        except ValueError:
            raise RuntimeError(
                f"unparseable blob size in {header!r} for {spec!r}")
        body = stream[pos:pos + size]
        if len(body) != size:
            raise RuntimeError(
                f"git cat-file --batch returned {len(body)} of {size} bytes "
                f"for {spec!r}; the blobless clone's lazy fetch likely failed")
        blobs[spec] = body.decode("utf-8", errors="replace")
        pos += size
        if stream[pos:pos + 1] == b"\n":
            pos += 1
    return blobs


def enumerate_candidates(repo):
    commits = gitmeta.log_commits(repo)

    # Provenance stamped onto every record. Without it a moved corpus is
    # undetectable across runs: HEAD can advance, or a fetch can bring new
    # commits, and two candidate files would look comparable when they are
    # not. Cheap to record, impossible to reconstruct after the fact.
    repo_head = gitmeta.head_sha(repo)
    commits_total = len(commits)
    repo_name = Path(repo).name

    reverted_subjects = set()
    for c in commits:
        m = REVERT_SUBJECT.match(c.subject)
        if m:
            reverted_subjects.add(m.group("orig").strip())

    out = []
    for c in commits:
        if not metrics.is_candidate_pair(c):
            continue
        if not c.parents:
            continue
        parent = c.parents[0]
        # No parent-reachability guard. Checking `parent in by_sha` would be
        # wrong: by_sha comes from log_commits, which passes --no-merges, so
        # merge commits are absent from it by construction while remaining
        # perfectly valid git objects that `git diff` handles fine. Guarding
        # on it would silently drop every candidate whose parent is a merge.
        # A genuinely unreachable parent now surfaces as a raised error from
        # _numstat instead of a silent exclusion.

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
            "stratum": f"{subsystem_of(c.files)}:{size_bucket(len(c.files))}",
            "repo_head": repo_head,
            "repo_commits_total": commits_total,
            "test_lines_added": t_add,
            "source_lines_added": s_add,
            "test_source_ratio": round(t_add / s_add, 3) if s_add else None,
            "reverted_later": c.subject.strip() in reverted_subjects,
            "status": "enumerated",
        })

    # Foreign-project and dependency-boundary filters. One batched read for
    # the whole candidate list -- 1,568 individual git-show calls is minutes
    # of avoidable work -- then stamp each candidate that is outside what the
    # method can measure. The stamp is COUNTED, never a silent drop: the
    # validator skips a candidate carrying the not_minable field and writes a
    # record with status=f"not_minable:{reason}", so it stays in the funnel.
    tomls = _read_pyprojects(repo, [(r["parent"], r["sha"]) for r in out])
    for r in out:
        reason = not_minable_reason(
            repo_name,
            tomls[f"{r['parent']}:pyproject.toml"],
            tomls[f"{r['sha']}:pyproject.toml"],
            test_files=r["test_files"],
        )
        if reason:
            r["not_minable"] = reason
    return out


def stratified_order(records):
    """Round-robin across (subsystem, size_bucket) so a small batch is not
    drawn from one easy corner of the distribution.

    Stamps `cycle` (1-based: which round-robin pass emitted the record) so the
    sampling structure is legible from the data alone. Reading the first N rows
    of a round-robin is NOT reading the top N of a ranked queue: strata are
    equalised per cycle, not weighted by mass, so a prefix over-samples thin
    strata. Any rate computed from a truncated prefix must be reweighted per
    stratum before it can be called a corpus rate, and `cycle` is what makes
    that possible without re-deriving the ordering.
    """
    strata = {}
    for r in records:
        strata.setdefault((r["subsystem"], r["size_bucket"]), []).append(r)
    for group in strata.values():
        group.sort(key=lambda r: r["date"], reverse=True)
    ordered, keys = [], sorted(strata)
    cycle = 0
    while any(strata[k] for k in keys):
        cycle += 1
        for k in keys:
            if strata[k]:
                r = strata[k].pop(0)
                r["cycle"] = cycle
                ordered.append(r)
    return ordered
