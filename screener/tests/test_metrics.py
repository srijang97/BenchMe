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
