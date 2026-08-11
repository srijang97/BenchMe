"""Stage 2 pure logic. No I/O, no containers -- which is why this is the only
file in the miner with unit tests. Each function here fails SILENTLY if wrong:
a bad patch split hands the agent the answer or strips the fix; a bad outcome
diff records the wrong tests as the oracle.
"""
import re
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


# pytest's FAILED/ERROR short-summary lines, e.g.
#   FAILED tests/test_x.py::test_y - AttributeError: no attribute 'z'
#   FAILED tests/test_x.py::test_y - assert 1 == 2
#   ERROR  tests/test_x.py::test_y - RuntimeError: fixture blew up
#   ERROR  tests/test_x.py                      (collection error: no detail)
#
# The runner that produces this stdout MUST set both COLUMNS (wide, e.g.
# 200) and CI=1. Confirmed against pytest 8.3.4 / Python 3.14.4: without a
# wide COLUMNS, pytest trims the "- detail" portion to terminal width and,
# when it doesn't fit, omits it entirely -- a truncated line is then
# indistinguishable from a line that never had a detail. CI=1 makes
# _pytest.config.running_on_ci() true, which additionally disables that
# trimming. A first capture attempt without COLUMNS set truncated real
# output to "- Attri...", corrupting the exception name.
#
# Node ids can contain spaces inside parametrised brackets, so the node id
# is never matched as \S+: the screener learned this the hard way, when a
# \S+ node-id pattern silently dropped 1,604 of 1,977 tests. Node ids can
# also contain the literal separator " - " inside their own brackets, e.g.
# test_range[1 - 2] (confirmed against real pytest output), so the split
# between node id and detail is not a single non-greedy regex group -- see
# _split_nodeid_detail, which scans for the first " - " that leaves the
# node id's brackets balanced.
LINE = re.compile(r"^(?P<kind>FAILED|ERROR) (?P<rest>\S.*)$", re.M)
EXC_NAME = re.compile(r"^(?P<exc>[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Exit))\b")

MISSING_API = {"AttributeError", "ImportError", "ModuleNotFoundError",
               "NameError"}
# CollectError, not CollectionError: pytest's own exception class for a
# collection failure. Reachable now via the ERROR-line branch of
# parse_failures below, not via EXC_NAME (pytest's collection-error summary
# line carries no "CollectError:" prefix to match against at all -- see the
# module comment above).
STRUCTURAL = {"SyntaxError", "IndentationError", "TabError", "CollectError"}
FAILURE_CLASSES = {"assertion", "missing_api", "structural"}


def _split_nodeid_detail(rest):
    """Split "nodeid - detail" at the first " - " that leaves the node id's
    brackets balanced (parametrised brackets can contain " - " themselves,
    e.g. test_range[1 - 2]).

    Returns (nodeid, detail) when a balanced separator is found, else
    (rest, None). None is not itself an error: pytest's own collection-error
    summary lines (`ERROR path/to/test.py`, no trailing detail) legitimately
    carry no separator at all. Callers decide what an absent separator means
    for their line kind.
    """
    start = 0
    while True:
        idx = rest.find(" - ", start)
        if idx == -1:
            return rest, None
        candidate = rest[:idx]
        if candidate.count("[") == candidate.count("]"):
            return candidate, rest[idx + 3:]
        start = idx + 3


def parse_failures(stdout):
    """node id -> exception type name, from pytest's FAILED and ERROR
    short-summary lines.

    FAILED lines: pytest never emits a bare "FAILED nodeid" with no detail
    for a genuine failure, so a FAILED line with no " - " separator means
    the line was truncated by terminal width (see the module comment on
    COLUMNS/CI). That is a misconfigured-capture signal, not a line to
    skip, so it raises rather than being silently dropped -- the same
    silent-drop failure class as the \\S+ node-id regression.

    A bare `assert` prints no exception name at all ("- assert 1 == 2"), so
    that detail is mapped to AssertionError explicitly. Everything else
    that isn't an "ExcName: message" recognised by EXC_NAME and doesn't
    start with "assert" maps to the raw identity "unparsed" -- which
    classify() then reports as "other:unparsed", rejected and counted --
    rather than falling through to AssertionError. That fallback used to
    silently *admit* invalid candidates: confirmed against real pytest
    output, `Failed: DID NOT RAISE <class 'ValueError'>` from pytest.fail()
    and bare exception names pytest doesn't prefix with
    Error/Exception/Exit (StopIteration, a Django *.DoesNotExist,
    KeyboardInterrupt) all used to land in AssertionError -> "assertion"
    and be wrongly accepted as valid base negatives.

    ERROR lines (fixture/setup errors, and collection errors such as a
    module-level SyntaxError or ImportError) never reached an assertion, so
    they are unconditionally structural regardless of detail. Confirmed
    against real pytest output that collection errors summarize as `ERROR
    path` with no detail at all, while setup/fixture errors summarize as
    `ERROR nodeid - ExcName: message`; both forms are handled the same way
    here since neither can be a valid "assertion" base negative.
    """
    out = {}
    for m in LINE.finditer(stdout):
        kind = m.group("kind")
        rest = m.group("rest").strip()
        nodeid, detail = _split_nodeid_detail(rest)
        nodeid = nodeid.strip()

        if kind == "ERROR":
            out[nodeid] = "CollectError"
            continue

        if detail is None:
            raise RuntimeError(
                f"FAILED line has no ' - ' separator, which pytest never "
                f"omits for a genuine failure -- this line was truncated "
                f"by terminal width. Re-capture with COLUMNS set wide and "
                f"CI=1: {rest!r}"
            )
        detail = detail.strip()
        exc = EXC_NAME.match(detail)
        if exc:
            out[nodeid] = exc.group("exc")
        elif detail.startswith("assert") or detail == "":
            out[nodeid] = "AssertionError"
        else:
            # Raw identity only -- classify() owns the "other:" prefix, the
            # same as it does for any other unrecognised exc_name.
            out[nodeid] = "unparsed"
    return out


def classify(exc_name):
    """Per the council contract: only assertion failures qualify as a valid
    base negative. missing_api and structural are rejected -- but counted by
    class, because the assertion-only rule filters out feature work (a new
    feature's test fails at the parent with AttributeError) and we need to
    know what that costs in yield before assuming the rule was right.

    TypeError (e.g. from a changed function signature) is deliberately left
    to fall through to `other:TypeError` rather than being folded into
    MISSING_API -- whether a signature change should count as missing_api
    is a rule question for the project's decision council, not a code fix.
    """
    if exc_name == "AssertionError":
        return "assertion"
    if exc_name in MISSING_API:
        return "missing_api"
    if exc_name in STRUCTURAL:
        return "structural"
    return f"other:{exc_name}"
