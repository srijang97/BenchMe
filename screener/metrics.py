"""Tier A metric definitions.

This module is the durable artifact. When the rest of the screener is thrown
away, these rules are harvested into the miner's stage 0. Change them
deliberately, and update screener/tests/test_metrics.py when you do.
"""
import fnmatch
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


COMPILED_SUFFIXES = (".pyx", ".pxd")
SERVICE_WORDS = re.compile(
    r"postgres|mysql|mariadb|redis|rabbitmq|kafka|mongodb|docker-compose", re.I)
CI_DIRS = (".github/workflows", ".gitlab-ci.yml", ".circleci", "azure-pipelines.yml")
LOCKFILES = ("uv.lock", "poetry.lock", "Pipfile.lock", "pdm.lock")

# Compose V2 renamed the default file to compose.yaml; both spellings, and the
# older docker-compose.* forms, declare backing services.
COMPOSE_GLOBS = ("docker-compose*.yml", "docker-compose*.yaml", "compose.y*ml")
SERVICE_CONFIG_NAMES = ("tox.ini", "pyproject.toml")
PYTEST_CONFIG_NAMES = ("pyproject.toml", "tox.ini", "setup.cfg", "pytest.ini")

# G7 asks for "lockfile OR fully pinned dependencies". A requirements file only
# substitutes for a real lockfile when it is actually pinned, so measure the
# pinning rather than trusting the filename.
PINNED_MIN = 0.8
PIN_MARKERS = ("==", " @ ")

# conftest.py is test *support*: it is a test file by location but can never
# name a source file, so counting it only depresses the mapping ratio.
TEST_MAP_EXCLUDE = {"conftest.py"}

REVERT = re.compile(r'^Revert "')
HOTFIX = re.compile(r"\b(hotfix|regression|fixup)\b", re.I)


def _under_ci(path):
    """True for CI-owned paths. Prefix semantics preserved from `has_ci`."""
    return any(path.startswith(d) or path == d for d in CI_DIRS)


def _is_compose(name):
    return any(fnmatch.fnmatch(name, g) for g in COMPOSE_GLOBS)


def _is_pytest_layout(path):
    """Structural evidence of pytest: `**/tests/**/test_*.py` or top-level `test_*.py`.

    A repo can run pytest without naming it in any config file, so the layout
    is treated as sufficient on its own. G1 eliminates a repo on a False here,
    which makes a missed detection far more expensive than a generous one.
    """
    p = PurePosixPath(path)
    if p.suffix != ".py" or not p.name.startswith("test_"):
        return False
    parts = p.parts
    return len(parts) == 1 or "tests" in parts[:-1]


def _test_map_counts(tracked):
    """(matched, ambiguous, total) for the test-to-source naming map.

    Conventions: test_X.py -> **/X.py, and X_test.py -> **/X.py. A test counts
    as mapped only when its stem resolves to exactly ONE source file: if two
    packages both define X.py, targeted test selection is precisely what is
    NOT possible, so the ambiguity is recorded rather than credited.
    """
    tests = [t for t in tracked
             if is_test_file(t) and PurePosixPath(t).name not in TEST_MAP_EXCLUDE]
    if not tests:
        return 0, 0, 0

    by_stem = {}
    for s in tracked:
        if is_source_file(s):
            by_stem.setdefault(PurePosixPath(s).stem, []).append(s)

    matched = 0
    ambiguous = 0
    for t in tests:
        stem = PurePosixPath(t).stem
        if stem.startswith("test_"):
            target = stem[len("test_"):]
        elif stem.endswith("_test"):
            target = stem[: -len("_test")]
        else:
            continue
        hits = by_stem.get(target, ())
        if len(hits) == 1:
            matched += 1
        elif len(hits) > 1:
            ambiguous += 1
    return matched, ambiguous, len(tests)


def test_map_ratio(tracked):
    """Fraction of test files resolvable to exactly one source file."""
    matched, _ambiguous, total = _test_map_counts(tracked)
    if not total:
        return 0.0
    return matched / total


def _requirements_pinned(repo, req_files):
    """True when at least PINNED_MIN of declared requirement lines carry a pin."""
    total = 0
    pinned = 0
    for t in req_files:
        try:
            body = (repo / t).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            total += 1
            if any(marker in line for marker in PIN_MARKERS):
                pinned += 1
    if not total:
        return False
    return (pinned / total) >= PINNED_MIN


def detect_environment(repo, tracked):
    names = {PurePosixPath(t).name for t in tracked}
    lockfile = next((lf for lf in LOCKFILES if lf in names), None)
    requirements_unpinned = False
    if lockfile is None:
        req_files = [t for t in tracked
                     if PurePosixPath(t).name.startswith("requirements")]
        if req_files:
            if _requirements_pinned(repo, req_files):
                lockfile = "requirements"
            else:
                requirements_unpinned = True

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

    # Every CI provider is read, not just GitHub Actions: a service declared in
    # .gitlab-ci.yml counts exactly as much as one declared in a workflow file.
    service = []
    for t in tracked:
        name = PurePosixPath(t).name
        if _under_ci(t) or _is_compose(name) or name in SERVICE_CONFIG_NAMES:
            try:
                body = (repo / t).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if SERVICE_WORDS.search(body):
                service.append(t)

    uses_pytest = False
    for t in tracked:
        if PurePosixPath(t).name in PYTEST_CONFIG_NAMES:
            try:
                body = (repo / t).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "pytest" in body:
                uses_pytest = True
                break
    if not uses_pytest:
        uses_pytest = any(_is_pytest_layout(t) for t in tracked)

    return {
        "lockfile": lockfile,
        "requirements_unpinned": requirements_unpinned,
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

    mapped, ambiguous, total_tests = _test_map_counts(tracked)

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
        "revert_commits": sum(1 for c in commits if REVERT.match(c.subject)),
        "hotfix_commits": sum(1 for c in commits if HOTFIX.search(c.subject)),
        "test_map_ratio": round(mapped / total_tests, 4) if total_tests else 0.0,
        "test_map_ambiguous": ambiguous,
        "tracked_files": len(tracked),
        "python_loc": loc,
    }
    record.update(detect_environment(repo, tracked))
    return record
