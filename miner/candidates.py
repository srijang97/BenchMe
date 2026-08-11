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
    "pydantic": ("tests/typechecking/",),
}


def is_non_pytest_test(repo_name, path):
    # The trailing slash is normalised here rather than trusted in the table
    # above. An entry written "tests/typechecking" would otherwise also match
    # "tests/typechecking_extra/", silently dropping real pytest tests from a
    # candidate's targets -- our defect turning into a verdict about the
    # commit, which is the one thing this filter must not do.
    return any(path.startswith(prefix if prefix.endswith("/") else prefix + "/")
               for prefix in NON_PYTEST_TEST_DIRS.get(repo_name, ()))


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


def enumerate_candidates(repo):
    commits = gitmeta.log_commits(repo)

    # Provenance stamped onto every record. Without it a moved corpus is
    # undetectable across runs: HEAD can advance, or a fetch can bring new
    # commits, and two candidate files would look comparable when they are
    # not. Cheap to record, impossible to reconstruct after the fact.
    repo_head = gitmeta.head_sha(repo)
    commits_total = len(commits)

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
