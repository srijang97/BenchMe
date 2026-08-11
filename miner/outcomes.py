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
