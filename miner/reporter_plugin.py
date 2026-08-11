"""Installed INTO the quarter container and loaded by pytest as `-p
benchme_reporter`. Never imported by the miner itself -- `miner/outcomes.py`
reads the JSONL this writes.

Why a plugin rather than parsing pytest's output:

  * `report.nodeid` is pytest's own node id, verbatim. Reconstructing one from
    JUnit XML means turning `classname="tests.test_x"` back into a path, and
    the XML carries no `file` attribute to check that guess against.
    Parametrised ids also legitimately contain " - " and nested brackets
    (measured: `test_param[1-x - y]`, `test_param[2-p[q]]`), which every
    text-scraping approach has to re-solve.
  * `report.when` gives the execution phase directly. An AttributeError raised
    inside a test body is `when="call"`; a broken fixture is `when="setup"`.
    That distinction is the whole admission gate and it is not recoverable
    from a short-summary line.
  * `longrepr.reprcrash.message` is never truncated to terminal width, so the
    COLUMNS/CI workaround stops being load-bearing.
  * These hooks fire regardless of the terminal reporter, so a plugin like
    pytest-pretty replacing the summary block can no longer blind the miner.

Appends, never truncates: the caller passes a fresh path per run.

The last thing written is a `sessionfinish` record, and `outcomes.parse_report`
REQUIRES it. Without a terminator a report that stopped mid-session at a clean
line boundary parses as a smaller-but-valid set of outcomes, the candidate's
oracle test is simply missing from `before`, and the run books
`rejected:unchanged` -- our crash wearing the shape of a verdict about the
commit. The terminator makes "the session ran to the end" a checkable fact
rather than an assumption.
"""
import json
import os

_OUT = os.environ.get("BENCHME_REPORT", "/tmp/benchme-report.jsonl")


def _message(report):
    crash = getattr(report.longrepr, "reprcrash", None)
    if crash is not None:
        return crash.message
    return str(report.longrepr) if report.longrepr is not None else None


def _emit(record):
    with open(_OUT, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def pytest_runtest_logreport(report):
    # A passing setup/teardown is noise: three records per green test would
    # triple a 6,400-test full-suite report for nothing.
    if report.outcome == "passed" and report.when != "call":
        return
    _emit({"kind": "test", "nodeid": report.nodeid, "when": report.when,
           "outcome": report.outcome, "message": _message(report)})


def pytest_collectreport(report):
    if report.outcome == "failed":
        _emit({"kind": "collect", "nodeid": report.nodeid, "when": "collect",
               "outcome": "failed", "message": _message(report)})


def pytest_sessionfinish(session, exitstatus):
    # The terminator. Its ABSENCE is the signal -- see the module docstring
    # and outcomes.parse_report. int() because pytest passes an ExitCode enum
    # on modern versions and a bare int on older ones, and json.dumps of an
    # IntEnum is version-dependent noise we do not want in the report.
    _emit({"kind": "sessionfinish", "exitstatus": int(exitstatus)})
