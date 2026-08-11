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
