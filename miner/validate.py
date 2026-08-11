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
