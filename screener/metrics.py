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

# Bot email anchors first: unambiguous, checked before the bare-name
# alternatives. The bare names are word-bounded so "Claude" as a human given
# name (e.g. "Co-authored-by: Claude Dubois <c.dubois@example.com>") does not
# match on name alone.
AI_TRAILER = re.compile(
    r"co-authored-by:[^\n]*"
    r"(noreply@anthropic\.com|devin-ai|copilot@|codex@"
    r"|\bcopilot\b|\bdevin\b|\bclaude\b|\bcodex\b)", re.I)
AI_MARKER = re.compile(
    r"generated with[^\n]*(claude code|codex|copilot)", re.I)

# Basenames that are Python but never behavioural source: packaging and
# tooling entry points. Matched against the file's basename only.
NON_SOURCE_NAMES = {"setup.py", "noxfile.py", "conftest.py"}

# Directories whose Python contents are never behavioural source, regardless
# of basename. Matched if any path segment equals one of these.
NON_SOURCE_DIRS = {"docs", "doc", "examples", "example", "scripts", "benchmarks"}


def is_test_file(path):
    p = PurePosixPath(path)
    if p.suffix != ".py":
        return False
    if "tests" in p.parts:
        return True
    return p.name.startswith("test_") or p.stem.endswith("_test")


def is_source_file(path):
    p = PurePosixPath(path)
    if p.suffix != ".py":
        return False
    if is_test_file(path):
        return False
    if p.name in NON_SOURCE_NAMES:
        return False
    if NON_SOURCE_DIRS & set(p.parts):
        return False
    return True


def is_human(commit):
    """False for bot identities, AI co-author trailers, and generation markers.

    This rule deliberately errs toward exclusion: wrongly dropping a human's
    commit costs one candidate out of hundreds, whereas wrongly admitting an
    agent's commit reintroduces the circularity the rule exists to prevent.
    """
    identity = f"{commit.author} {commit.committer}"
    if BOT_IDENTITY.search(identity):
        return False
    message = f"{commit.subject}\n{commit.body}"
    if AI_TRAILER.search(message) or AI_MARKER.search(message):
        return False
    return True


def is_candidate_pair(commit, max_files=10):
    """A commit that could in principle become a capsule.

    Self-enforcing on merges: a commit with 2 or more parents is excluded
    here directly, rather than relying on a caller to have passed
    `git log --no-merges` upstream.
    """
    if len(commit.parents) >= 2:
        return False
    if not is_human(commit):
        return False
    if len(commit.files) > max_files:
        return False
    has_source = any(is_source_file(f) for f in commit.files)
    has_test = any(is_test_file(f) for f in commit.files)
    return has_source and has_test


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
