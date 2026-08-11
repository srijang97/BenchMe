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


class Record(NamedTuple):
    nodeid: str
    when: str
    outcome: str
    message: str


def parse_report(text):
    """(test_records, collect_error_records) from the reporter's JSONL.

    Raises ValueError on a malformed line. A partial or interleaved write is
    OUR failure; skipping the line would silently shrink the outcome set,
    which downstream reads as "this commit changed nothing" -- apparatus
    wearing the shape of a verdict.
    """
    tests, collect = [], []
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
        rec = Record(raw["nodeid"], raw["when"], raw["outcome"],
                     raw.get("message"))
        (collect if raw.get("kind") == "collect" else tests).append(rec)
    return tests, collect


def collapse(records):
    """node id -> one of FAILURE / ERROR / PASSED / SKIPPED.

    Several records can share a node id (a passing call plus a failing
    teardown, say). Precedence: a failure in setup or teardown makes the whole
    test an ERROR; otherwise the call phase decides.
    """
    status = {}
    for rec in records:
        if rec.outcome == "failed" and rec.when in _STRUCTURAL_PHASES:
            status[rec.nodeid] = ERROR
            continue
        if status.get(rec.nodeid) == ERROR:
            continue
        if rec.when != "call":
            continue
        if rec.outcome == "failed":
            status[rec.nodeid] = FAILURE
        elif rec.outcome == "skipped":
            status[rec.nodeid] = SKIPPED
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

    f2p        -- FAILURE before, PASSED after. The oracle. Requires an exact
                  node id match on both sides.
    p2p        -- PASSED on both. The regression set.
    broken     -- PASSED before, and after either FAILURE or gone, where the
                  disappearance is not explained by a rename.
    renamed    -- PASSED before and gone after, but the same test function
                  still has at least as many passing cases. Reported, not
                  penalised.
    error_base -- could not run before, PASSED after. Not admissible as an
                  oracle (decision 2), but counted so the cost of that gate
                  is measurable.

    Why renames are reconciled at all: pydantic parametrises one test on
    source line numbers, so applying the code patch renumbers the ids without
    changing behaviour. Treating that as a broken regression rejected three
    good candidates in the 2025Q3 batch. The reconciliation is deliberately
    narrow -- it requires the passing count for that test function not to
    drop -- so it cannot excuse a test that genuinely disappeared.
    """
    f2p, p2p, broken, renamed, error_base = [], [], [], [], []

    after_pass_by_base = {}
    for nodeid, status in after.items():
        if status == PASSED:
            key = base_id(nodeid)
            after_pass_by_base[key] = after_pass_by_base.get(key, 0) + 1
    before_pass_by_base = {}
    for nodeid, status in before.items():
        if status == PASSED:
            key = base_id(nodeid)
            before_pass_by_base[key] = before_pass_by_base.get(key, 0) + 1

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
            elif now is None:
                key = base_id(nodeid)
                if after_pass_by_base.get(key, 0) >= before_pass_by_base[key]:
                    renamed.append(nodeid)
                else:
                    broken.append(nodeid)
            else:
                broken.append(nodeid)
    return {"f2p": sorted(f2p), "p2p": sorted(p2p), "broken": sorted(broken),
            "renamed": sorted(renamed), "error_base": sorted(error_base)}
