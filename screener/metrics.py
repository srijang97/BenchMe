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

# A PEP 508 requirement: a distribution name, optional extras, then either
# end-of-line or a specifier / marker / URL / trailing comment. Prose fails it
# on the second word ("base.txt holds the pins" -> `holds` is not a specifier),
# which keeps a README under requirements/ from being scored as dependencies.
DEPENDENCY_LINE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]*"
    r"(\[[^\]]*\])?"
    r"\s*($|[=<>!~;@,(#].*)")

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


def _test_target_stem(path):
    """The source stem a test file names, or None if it follows no convention.

    Support code living in a tests directory -- conftest.py, __init__.py,
    helpers.py -- names no source file and never can, so it must not sit in
    the ratio's denominator dragging the reported number down. Being inside a
    tests directory makes a file a test file; only its *name* makes it a test.
    """
    stem = PurePosixPath(path).stem
    if stem.startswith("test_"):
        return stem[len("test_"):]
    if stem.endswith("_test"):
        return stem[: -len("_test")]
    return None


def _test_map_counts(tracked):
    """(matched, ambiguous, total) for the test-to-source naming map.

    Conventions: test_X.py -> **/X.py, and X_test.py -> **/X.py. A test counts
    as mapped when its stem resolves to ONE OR MORE source files.

    Uniqueness is deliberately NOT required. The metric exists to predict
    whether targeted test selection is possible, and selection addresses the
    TEST file (`pytest tests/test_main.py::test_x`) -- it never has to decide
    which source file the test corresponds to. How many source files happen to
    share a stem therefore has no bearing on what the metric predicts, and
    requiring uniqueness only penalised repos carrying a vendored or
    compatibility subtree (pydantic's `pydantic/v1/` duplicates ~25 module
    names, which collapsed its ratio to 0.03). Ambiguity stays visible as a
    reported column; it is no longer a penalty.
    """
    # NON_SOURCE_DIRS is applied to BOTH sides of the ratio. Applying it only to
    # sources was one-directional and could only depress the number: flask's
    # examples/tutorial/tests/test_auth.py sat in the denominator while its
    # tracked counterpart examples/tutorial/flaskr/auth.py was barred from being
    # a source, so it was counted as unmappable rather than left out.
    tests = [t for t in tracked
             if is_test_file(t)
             and _test_target_stem(t) is not None
             and not (NON_SOURCE_DIRS & set(PurePosixPath(t).parts))]
    if not tests:
        return 0, 0, 0

    by_stem = {}
    for s in tracked:
        if is_source_file(s):
            by_stem.setdefault(PurePosixPath(s).stem, []).append(s)

    matched = 0
    ambiguous = 0
    for t in tests:
        hits = by_stem.get(_test_target_stem(t), ())
        if len(hits) >= 1:
            matched += 1
        if len(hits) > 1:
            ambiguous += 1
    return matched, ambiguous, len(tests)


def test_map_ratio(tracked):
    """Fraction of test files resolvable to exactly one source file."""
    matched, _ambiguous, total = _test_map_counts(tracked)
    if not total:
        return 0.0
    return matched / total


def _is_requirements_file(path):
    """A pip requirements file, found by path rather than basename alone.

    Covers both the flat `requirements-dev.txt` form and the split
    `requirements/base.txt` layout, at any depth. `.in` files are excluded by
    the `.txt` suffix requirement, deliberately: a pip-compile `.in` is the
    unpinned SOURCE, and the pinned artefact is the `.txt` it generates.
    Counting the `.in` would dilute the ratio and fail a fully pinned repo.
    """
    p = PurePosixPath(path)
    if p.suffix != ".txt":
        return False
    if p.name.startswith("requirements"):
        return True
    return "requirements" in p.parts[:-1]


def _requirements_pinned(repo, req_files):
    """Tri-state pinning verdict, scored per file and never pooled.

    True  -- some file has dependency lines and clears PINNED_MIN.
    False -- some file has dependency lines, but no file clears the bar.
    None  -- no selected file has a single dependency line, so there is no
             pinning evidence either way and G7 must not be failed on it.

    Scoring is per file because pooling was itself a false-elimination bug: a
    prose README under requirements/ poured unpinned lines into one shared
    ratio and dragged a genuinely pinned requirements.txt below the bar. G7
    asks whether dependencies are pinned SOMEWHERE, not in every file, so a
    pinned requirements.txt beside a loose requirements-dev.txt still builds
    deterministically for the purpose the gate cares about.

    Lines beginning with `-` are pip directives (`-r base.txt`, `-e .`,
    `--index-url`), not dependencies. Counting them as unpinned is a category
    error that scores an all-include stub at 0% and eliminates the repo.
    """
    saw_dependencies = False
    for t in req_files:
        try:
            body = (repo / t).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        total = 0
        pinned = 0
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            if not DEPENDENCY_LINE.match(line):
                continue
            total += 1
            if any(marker in line for marker in PIN_MARKERS):
                pinned += 1
        if not total:
            continue
        saw_dependencies = True
        if (pinned / total) >= PINNED_MIN:
            return True
    return False if saw_dependencies else None


def detect_environment(repo, tracked):
    names = {PurePosixPath(t).name for t in tracked}
    lockfile = next((lf for lf in LOCKFILES if lf in names), None)
    requirements_unpinned = False
    if lockfile is None:
        req_files = [t for t in tracked if _is_requirements_file(t)]
        if req_files:
            verdict = _requirements_pinned(repo, req_files)
            if verdict is True:
                lockfile = "requirements"
            elif verdict is False:
                requirements_unpinned = True
            # verdict is None: nothing to judge, so no evidence either way.

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
        "has_ci": any(_under_ci(t) for t in tracked),
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
