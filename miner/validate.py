"""Stage 2 pure logic. No I/O, no containers -- which is why this is the only
file in the miner with unit tests. Each function here fails SILENTLY if wrong:
a bad patch split hands the agent the answer or strips the fix; a bad outcome
diff records the wrong tests as the oracle.
"""
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "screener"))
import metrics  # noqa: E402


def _belongs_to_test_side(path):
    """Broader than metrics.is_test_file. Catches two cases is_test_file
    misses because it requires a `.py` suffix: non-.py assets that live
    under a `tests/` directory (fixture data, JSON/YAML expectations) and a
    root `conftest.py` (neither a test file nor source under is_test_file,
    so it would otherwise fall into `code` by default).

    Deliberately NOT folded into metrics.is_test_file. That function answers
    "is this a test file for candidate-pair detection" and is shared with
    the screener; widening it would change what counts as a candidate pair
    -- a commit that only touches a fixture would start qualifying as a
    test/code pair. This predicate only decides which side of a patch split
    a path belongs to. Keep the two separate: a future reader will otherwise
    "simplify" them back together and reintroduce the candidate-detection
    change this split was written to avoid.
    """
    if metrics.is_test_file(path):
        return True
    p = PurePosixPath(path)
    return "tests" in p.parts or p.name == "conftest.py"


def split_paths(files):
    """(test_paths, code_paths), both sorted, using _belongs_to_test_side
    (see its docstring for why that predicate is broader than, and kept
    separate from, metrics.is_test_file). Without the broader predicate, a
    commit that adds a fixture under tests/ or a root conftest.py for its
    new test would put that file on the code side, the before state would
    error at collection instead of failing on the bug, and the candidate
    would silently disappear before it ever reached f2p."""
    tests = sorted(f for f in files if _belongs_to_test_side(f))
    code = sorted(f for f in files if not _belongs_to_test_side(f))
    return tests, code


def make_patch(repo, parent, sha, paths):
    """Unified diff for `paths` between parent and sha. Empty string when
    there are no paths, so callers can skip `git apply` entirely.

    `--no-color --no-ext-diff` and `-c diff.noprefix=false` pin the diff
    format against the user's git config (color.diff=always, a configured
    external diff tool, or diff.noprefix) so the patch this returns is
    always in the plain unified format `git apply` expects, rather than
    failing to apply much later and surfacing as an apparatus error on
    every candidate.

    `paths` come from `git log --name-only` for this exact commit, so if
    `paths` is non-empty the diff must produce output; empty stdout there
    means the pathspec matched nothing (e.g. a rename git diff resolved
    differently), not that nothing changed. Raise rather than let that
    become an empty patch and a before state indistinguishable from a
    clean tree.
    """
    if not paths:
        return ""
    proc = subprocess.run(
        ["git", "-c", "diff.noprefix=false", "diff", "--binary",
         "--no-color", "--no-ext-diff", parent, sha, "--", *paths],
        cwd=str(repo), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff failed for {sha[:8]}: {proc.stderr[:300]}")
    if not proc.stdout:
        raise RuntimeError(
            f"git diff produced no output for {sha[:8]} despite "
            f"{len(paths)} path(s); an empty diff here means the pathspec "
            f"matched nothing, not that nothing changed"
        )
    return proc.stdout


def diff_outcomes(before, after):
    """f2p  -- failed before, passed after (the oracle)
    p2p    -- passed on both sides (the regression set)
    broken -- passed before, and after is either FAILED or absent (the code
              patch broke something, including a collection crash that
              makes the test vanish rather than merely fail)

    SKIPPED and ERROR outcomes are deliberately excluded from all three
    sets: a skipped test proves nothing, and an errored test is an
    apparatus signal the caller handles separately. The one exception is
    absence: a node id that was PASSED before and is missing from `after`
    entirely (rather than present with an ERROR outcome) usually means a
    collection crash made the test vanish rather than merely fail. That is
    still `broken` -- the effect on the candidate is identical to a
    failure, and treating a vanished node id as unclassified would let it
    pass silently through diff_outcomes.
    """
    f2p, p2p, broken = [], [], []
    for nodeid, before_outcome in before.items():
        after_outcome = after.get(nodeid)
        if before_outcome == "FAILED" and after_outcome == "PASSED":
            f2p.append(nodeid)
        elif before_outcome == "PASSED" and after_outcome == "PASSED":
            p2p.append(nodeid)
        elif before_outcome == "PASSED" and after_outcome in ("FAILED", None):
            broken.append(nodeid)
    return {"f2p": sorted(f2p), "p2p": sorted(p2p), "broken": sorted(broken)}
