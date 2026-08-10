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
