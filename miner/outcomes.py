"""Stage 2 pure logic for reading the container reporter's output.

Split from validate.py deliberately: validate.py answers "which side of the
patch does this path belong on", this module answers "what did the test run
say". Both are pure and unit-tested; neither does I/O.

The admission rule this module encodes, per
docs/council/ROUND_02_SYNTHESIS.md:

    Gate on execution integrity. Label everything else.

A test that RAN and whose expectation was not met (`when="call"`,
`outcome="failed"`) is admissible whatever exception it raised. A test that
could not run -- a broken fixture, a collection error -- is not, because its
assertions never executed against the unfixed code, so a later pass proves
nothing about whether they detect the bug.
"""
import json
import re
from typing import NamedTuple

FAILURE = "failure"   # ran, expectation not met -- admissible
ERROR = "error"       # could not run -- not admissible as a base negative
PASSED = "passed"
SKIPPED = "skipped"

# setup/teardown outrank call: a test whose fixture blew up never asserted,
# and a test whose teardown blew up cannot be trusted to have left the
# process clean for the next one. Either way it is not a usable base
# negative, so ERROR wins over whatever `call` reported.
_STRUCTURAL_PHASES = ("setup", "teardown")

# pytest exit statuses this project is willing to draw a conclusion from:
#   0  every test passed
#   1  tests were collected and some failed
#   5  nothing was collected
# Everything else -- 2 interrupted, 3 internal error, 4 usage error -- means
# the session did NOT complete. 5 stays acceptable because runner._measure's
# `if not before` / `if not after` guards already handle "no outcomes" with a
# far better message than a generic exit-status complaint.
OK_EXIT_STATUSES = frozenset({0, 1, 5})


class Record(NamedTuple):
    nodeid: str
    when: str
    outcome: str
    message: str


class Report(NamedTuple):
    """What one pytest session said.

    `exitstatus` is carried out of the terminator rather than discarded,
    because the terminator's PRESENCE does not prove the session completed --
    see parse_report. `None` when the terminator carried no usable integer,
    which is never treated as acceptable.
    """
    tests: list
    collect: list
    exitstatus: int


def parse_report(text):
    """A `Report` (test records, collect-error records, exit status) from the
    reporter's JSONL.

    INVARIANT: the report must end with the reporter's `sessionfinish` record.
    That record is consumed here -- it is never returned as a test or a
    collect record -- and its ABSENCE raises ValueError.

    Two failures are therefore caught, and both are OURS, never a verdict
    about the commit:

      * a malformed line -- a partial or interleaved write. Skipping it would
        silently shrink the outcome set.
      * a missing terminator -- the plugin died mid-session mid-LINE, or never
        reached sessionfinish at all. A report cut at a clean line boundary is
        perfectly valid JSONL, so nothing else can tell it from a
        short-but-complete run. The candidate's oracle test would simply be
        absent from `before` and the run would book `rejected:unchanged`:
        apparatus wearing the shape of a verdict.

    The terminator is NOT sufficient on its own, which is why `exitstatus` is
    returned rather than dropped. pytest calls `pytest_sessionfinish` from
    `wrap_session`'s `finally` whenever `pytest_sessionstart` ran -- including
    on ExitCode.INTERRUPTED (2) and ExitCode.INTERNAL_ERROR (3). A session that
    dies mid-run therefore writes SOME records and then the terminator, and a
    parser that only checks for the terminator calls that partial report
    complete. The caller (`runner._pytest`) gates on OK_EXIT_STATUSES.

    `exitstatus` is None when the record carried no integer -- an old report,
    or a mangled value. None is deliberately not in OK_EXIT_STATUSES: a
    missing value must never default to the acceptable case.
    """
    tests, collect = [], []
    finished = False
    exitstatus = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"reporter line {lineno} is not valid JSON ({exc}); the "
                f"report was truncated or interleaved: {line[:120]!r}") from exc
        if raw.get("kind") == "sessionfinish":
            finished = True
            try:
                exitstatus = int(raw["exitstatus"])
            except (KeyError, TypeError, ValueError):
                exitstatus = None
            continue
        rec = Record(raw["nodeid"], raw["when"], raw["outcome"],
                     raw.get("message"))
        (collect if raw.get("kind") == "collect" else tests).append(rec)
    if not finished:
        raise ValueError(
            f"reporter report is truncated: no sessionfinish record, so the "
            f"pytest session did not run to the end "
            f"({len(tests)} test and {len(collect)} collect records read)")
    return Report(tests, collect, exitstatus)


def collapse(records):
    """node id -> one of FAILURE / ERROR / PASSED / SKIPPED.

    Several records can share a node id (a passing call plus a failing
    teardown, say). Precedence, highest first:

      1. a FAILED setup or teardown makes the whole test an ERROR. It never
         asserted, or it did not leave the process clean for the next test.
      2. a SKIPPED outcome in ANY phase makes the test SKIPPED. `@pytest.mark.
         skip`, `@pytest.mark.skipif` and a fixture calling `pytest.skip()` all
         report at `when="setup"` and emit no call record at all, so a
         call-only rule left the node ABSENT from this map rather than
         SKIPPED. Absence and skip are treated very differently downstream: a
         previously-passing test that a code patch newly skips would vanish,
         fail outcomes.diff's exact-swap rename rule, land in `broken`, and
         book a false `rejected:regression_broken` -- our reading of the run
         turned into a verdict about the commit. In practice `skipped_after`
         could only ever fire for an in-body `pytest.skip()` before this.
      3. otherwise the call phase decides.

    Ordering matters and is pinned by tests: a failed setup still outranks a
    skip (rule 1 is checked first, and the ERROR guard below stops a later
    skip record overwriting it), and a skip outranks a passing teardown.
    """
    status = {}
    for rec in records:
        if rec.outcome == "failed" and rec.when in _STRUCTURAL_PHASES:
            status[rec.nodeid] = ERROR
            continue
        if status.get(rec.nodeid) == ERROR:
            continue
        if rec.outcome == "skipped":
            status[rec.nodeid] = SKIPPED
            continue
        if rec.when != "call":
            continue
        if rec.outcome == "failed":
            status[rec.nodeid] = FAILURE
        else:
            status[rec.nodeid] = PASSED
    return status


# "Name: message" where Name is a possibly-dotted Python identifier. Matching
# the identifier-plus-colon shape rather than an Error/Exception/Warning
# suffix is deliberate: pydantic's PydanticDeprecatedSince20 carries none of
# those suffixes, and a suffix rule would drop it to `unlabelled`.
_EXC = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_.]*): ")

MISSING_API = {"AttributeError", "ImportError", "ModuleNotFoundError",
               "NameError"}


def label(message):
    """A description of how a test failed. NEVER a judgement about whether the
    candidate qualifies.

    Round 1 required an assertion-class base negative and rejected everything
    else. Round 2 retired that rule: fail-to-pass against the genuine upstream
    fix already establishes that the failure was caused by the missing fix, so
    the exception's name adds nothing about validity. It is still worth
    recording, because corpus composition is a reported property and because a
    later audit may find a label that predicts a weak oracle. Until such an
    audit exists, no label gates.

    `unlabelled` therefore means "our parser did not recognise this message",
    which is a fact about us. It must never become a rejection -- that is
    exactly the `other:unparsed` defect that cost half the first batch.
    """
    if not message:
        return "unlabelled"
    text = message.strip()
    if text.startswith("assert"):
        return "assertion"
    match = _EXC.match(text)
    if not match:
        return "unlabelled"
    name = match.group("name").rsplit(".", 1)[-1]
    if name == "AssertionError":
        return "assertion"
    # pytest raises _pytest.outcomes.Failed for pytest.fail(), for
    # pytest.raises that did not raise, and for pytest.warns that did not
    # warn. All three surface as "Failed: ...". Framework-level, so this
    # holds for every pytest project, not just pydantic.
    if name == "Failed":
        return "expectation"
    if name in MISSING_API:
        return "missing_api"
    if name == "TypeError":
        return "type_error"
    return f"exception:{name}"


def base_id(nodeid):
    """The node id without its parametrisation, e.g.
    `t.py::test_a[1-2]` -> `t.py::test_a`.

    Splits on the FIRST "[" so nested brackets in a parameter value
    (`test_a[p[q]]`, measured) take the whole tail with them.
    """
    head, sep, _ = nodeid.partition("[")
    return head if sep else nodeid


def diff(before, after):
    """Compare two collapsed status maps.

    f2p           -- FAILURE before, PASSED after. The oracle. Requires an
                      exact node id match on both sides.
    p2p           -- PASSED on both. The regression set.
    broken        -- PASSED before, and after either FAILURE, ERROR, or gone,
                      where a disappearance is not explained by an exact
                      rename swap.
    renamed       -- PASSED before and gone after, reconciled against an
                      equal-sized batch of newly-appeared passing cases under
                      the same test function. Reported, not penalised.
    error_base    -- could not run before, PASSED after. Not admissible as an
                      oracle (decision 2), but counted so the cost of that
                      gate is measurable.
    skipped_after -- PASSED before, SKIPPED after. Not a regression -- the
                      test did not fail -- but suspicious enough (a patch
                      that skips a previously-passing test) to stay visible
                      rather than being folded into `broken` or dropped.

    Why renames are reconciled at all: pydantic parametrises one test on
    source line numbers, so applying the code patch renumbers the ids without
    changing behaviour. Treating that as a broken regression rejected three
    good candidates in the 2025Q3 batch.

    The reconciliation is deliberately narrow, and it is an EXACT swap, not a
    "count did not drop" check: for each test function, it counts the passing
    node ids that vanished (passed before, absent after) against the passing
    node ids that appeared (passing after, absent before), and excuses the
    vanished ones as `renamed` only when those two counts are equal. A
    "count did not drop" rule can be satisfied by an unrelated gain masking a
    genuine loss elsewhere in the same function (one test vanishes, two
    unrelated ones appear) -- that is a real regression wearing a rename's
    clothes. At the node-id level a renumbering and a delete-plus-unrelated-
    add are genuinely indistinguishable, so the equal-counts tie-break is a
    deliberate choice, not an oversight: it recognises the measured pydantic
    case (a patch shifts source lines, every id under the base is renumbered,
    the count is unchanged) while refusing the ambiguous ones. Ambiguity
    resolves toward `broken`, i.e. toward rejecting the candidate, because a
    false rejection only costs one candidate out of thousands whereas a false
    admission puts a capsule with a real regression into the corpus.
    """
    f2p, p2p, broken = [], [], []
    renamed, error_base, skipped_after = [], [], []

    vanished_by_base = {}
    for nodeid, status in before.items():
        if status == PASSED and nodeid not in after:
            key = base_id(nodeid)
            vanished_by_base[key] = vanished_by_base.get(key, 0) + 1
    appeared_by_base = {}
    for nodeid, status in after.items():
        if status == PASSED and nodeid not in before:
            key = base_id(nodeid)
            appeared_by_base[key] = appeared_by_base.get(key, 0) + 1

    for nodeid, was in before.items():
        now = after.get(nodeid)
        if was == FAILURE and now == PASSED:
            f2p.append(nodeid)
        elif was == ERROR and now == PASSED:
            error_base.append(nodeid)
        elif was == PASSED:
            if now == PASSED:
                p2p.append(nodeid)
            elif now == FAILURE:
                broken.append(nodeid)
            elif now == SKIPPED:
                skipped_after.append(nodeid)
            elif now is None:
                key = base_id(nodeid)
                if vanished_by_base.get(key, 0) == appeared_by_base.get(key, 0):
                    renamed.append(nodeid)
                else:
                    broken.append(nodeid)
            else:
                broken.append(nodeid)
    return {"f2p": sorted(f2p), "p2p": sorted(p2p), "broken": sorted(broken),
            "renamed": sorted(renamed), "error_base": sorted(error_base),
            "skipped_after": sorted(skipped_after)}
