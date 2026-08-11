# Miner Classifier Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the miner's exception-name classifier with a structured pytest
reporter, so that failure kind labels a capsule instead of rejecting it, and so
that no tooling defect can become a verdict about a commit.

**Architecture:** A ~25-line pytest plugin is installed into the quarter
container once per container start. It writes one JSON line per test report,
carrying pytest's own node id verbatim, the execution phase, the outcome, and
the untruncated crash message. The miner reads that file instead of scraping the
terminal summary. A new pure-logic module `miner/outcomes.py` collapses those
records into per-test statuses, labels each failure, and diffs the before/after
runs with rename reconciliation. `miner/validate.py` keeps only its patch and
path responsibilities.

**Tech Stack:** Python 3, pytest 8.x plugin hooks (`pytest_runtest_logreport`,
`pytest_collectreport`), Docker, JSONL.

## Global Constraints

- **`rejected:*` is a verdict about the commit. `apparatus` is a verdict about
  us. `error` is a miner bug and is non-terminal.** Never let one become
  another. This is the project's central discipline.
- **Never default a missing or unparseable value to a qualifying one.** Silently
  rejecting a valid candidate shrinks the corpus; silently admitting an invalid
  one corrupts every number downstream.
- **Do not modify `screener/metrics.py` or `screener/tierb.py`.** Both are shared
  with the merged screener. `tierb.parse_outcomes` and `tierb.PYTEST_ARGV` stay
  exactly as they are; the miner stops *calling* `parse_outcomes`, it does not
  change it.
- Python: standard library only. No new third-party dependencies.
- Unit tests live in `miner/tests/`, run with
  `python -m pytest miner/tests/ -v` from the repo root.
- Every design decision below traces to `docs/council/ROUND_02_SYNTHESIS.md`.
  Decision numbers in task headers refer to its final table.

### Measured facts this plan depends on

All four were verified empirically against pytest 8.3.4 before this plan was
written. Do not re-litigate them; do not assume anything beyond them.

1. An `AttributeError`, `ImportError` or `ModuleNotFoundError` raised **inside a
   test body** is reported at `when="call"` with `outcome="failed"`. Only
   fixture/setup errors report at `when="setup"`. The phase is the
   assertion-versus-structural line.
2. `pytest.raises` not raising, `pytest.warns` not warning, and `pytest.fail()`
   all produce a message beginning `Failed: `.
3. `--tb=no` (already in `tierb.PYTEST_ARGV`) does **not** strip
   `report.longrepr.reprcrash.message`. Messages survive intact.
4. `--continue-on-collection-errors` stops one broken import from aborting the
   session. Without it, one bad file reduced a 20-test run to 1 reported test.

### What is NOT in scope

- Alternate-implementation sampling (decision 11) — capsule creation, later stage.
- Per-tier label distribution reporting (decision 10) — experiment-time, not miner.
- Quarter-boundary anchoring, `sqlalchemy` re-examination, `CONVERSION_RATE`
  recalibration. All remain parked.

---

## File Structure

| File | Responsibility |
|---|---|
| `miner/reporter_plugin.py` | **Create.** The pytest plugin source, installed into the container. Never imported by the miner itself. |
| `miner/outcomes.py` | **Create.** Pure logic: parse reporter JSONL, collapse to statuses, label failures, diff before/after with rename reconciliation. |
| `miner/tests/test_outcomes.py` | **Create.** Unit tests for the above. |
| `miner/validate.py` | **Modify.** Delete `diff_outcomes`, `parse_failures`, `classify`, `LINE`, `EXC_NAME`, `MISSING_API`, `STRUCTURAL`, `FAILURE_CLASSES`, `_split_nodeid_detail`. Keep `split_paths`, `_belongs_to_test_side`, `make_patch`. |
| `miner/tests/test_validate.py` | **Modify.** Remove tests for the deleted functions; keep `split_paths` coverage. |
| `miner/quarters.py` | **Modify.** Add `install_reporter(container)`. |
| `miner/runner.py` | **Modify.** Use the reporter; drop the gate; add determinism check; filter non-pytest test dirs. |
| `miner/candidates.py` | **Modify.** Per-repo non-pytest test directory config. |
| `miner/report.py` | **Modify.** Add the composition section and the apparatus tripwire; retire the dead base-negative-class breakdown. |
| `miner/record.py` | **Modify.** Docstring only — `validated` no longer means "assertion-class". |

---

## Task 1: The reporter plugin and its parser

Decisions 2, 3, 5.

**Files:**
- Create: `miner/reporter_plugin.py`
- Create: `miner/outcomes.py`
- Create: `miner/tests/test_outcomes.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `outcomes.FAILURE = "failure"`, `outcomes.ERROR = "error"`,
    `outcomes.PASSED = "passed"`, `outcomes.SKIPPED = "skipped"`
  - `outcomes.Record` — `NamedTuple(nodeid: str, when: str, outcome: str, message: str | None)`
  - `outcomes.parse_report(text: str) -> tuple[list[Record], list[Record]]`
    returning `(test_records, collect_errors)`
  - `outcomes.collapse(records: list[Record]) -> dict[str, str]`
    mapping node id to one of the four status constants

**Note on where the plugin's name lives:** `outcomes.py` is pure parsing logic
and deliberately knows nothing about containers. The module name
(`benchme_reporter`), the install directory and the report-path environment
variable are properties of *installation*, so they belong in `quarters.py`
(Task 5), not here. Do not add them to `outcomes.py`.

- [ ] **Step 1: Write the plugin**

Create `miner/reporter_plugin.py`. This file is *never imported by the miner*.
It is read as text and written into the container, where pytest loads it by
module name. Keep it dependency-free and short.

```python
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
```

- [ ] **Step 2: Write the failing tests for the parser**

Create `miner/tests/test_outcomes.py`:

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import outcomes  # noqa: E402


def _jsonl(*records):
    return "\n".join(json.dumps(r) for r in records) + "\n"


def test_parse_report_separates_collect_errors_from_tests():
    text = _jsonl(
        {"kind": "collect", "nodeid": "tests/test_bad.py", "when": "collect",
         "outcome": "failed", "message": "ImportError while importing..."},
        {"kind": "test", "nodeid": "tests/test_a.py::test_x", "when": "call",
         "outcome": "failed", "message": "assert 1 == 2"},
    )
    tests, collect = outcomes.parse_report(text)
    assert [r.nodeid for r in tests] == ["tests/test_a.py::test_x"]
    assert [r.nodeid for r in collect] == ["tests/test_bad.py"]
    assert collect[0].when == "collect"


def test_parse_report_tolerates_blank_lines_and_preserves_message():
    text = "\n" + _jsonl(
        {"kind": "test", "nodeid": "t.py::a", "when": "call",
         "outcome": "failed",
         "message": "Failed: DID NOT RAISE <class 'ValueError'>"},
    ) + "\n"
    tests, collect = outcomes.parse_report(text)
    assert collect == []
    assert tests[0].message == "Failed: DID NOT RAISE <class 'ValueError'>"


def test_parse_report_raises_on_malformed_line():
    # A truncated or interleaved write is OUR failure, not the commit's. It
    # must surface as apparatus, never be skipped into a smaller result set
    # that reads like "this commit changed nothing".
    try:
        outcomes.parse_report('{"kind": "test", "nodei')
    except ValueError:
        return
    raise AssertionError("expected ValueError on malformed JSONL")


def test_collapse_call_failure_is_a_failure():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.FAILURE}


def test_collapse_setup_failure_is_an_error_not_a_failure():
    # The whole admission gate. A broken fixture never reached an assertion,
    # so it is not evidence that the test detects the bug.
    recs = [outcomes.Record("t.py::a", "setup", "failed", "RuntimeError: boom")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.ERROR}


def test_collapse_attribute_error_in_body_is_a_failure():
    # Measured against pytest 8.3.4: an AttributeError raised inside a test
    # body reports at when="call". Round 1 rejected these as `missing_api`;
    # they are ordinary executed failures and must reach the label layer.
    recs = [outcomes.Record("t.py::a", "call", "failed",
                            "AttributeError: module 'json' has no attribute 'z'")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.FAILURE}


def test_collapse_teardown_failure_outranks_a_passing_call():
    recs = [outcomes.Record("t.py::a", "call", "passed", None),
            outcomes.Record("t.py::a", "teardown", "failed", "IOError: x")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.ERROR}


def test_collapse_records_passed_and_skipped():
    recs = [outcomes.Record("t.py::a", "call", "passed", None),
            outcomes.Record("t.py::b", "call", "skipped", "needs network")]
    assert outcomes.collapse(recs) == {"t.py::a": outcomes.PASSED,
                                       "t.py::b": outcomes.SKIPPED}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest miner/tests/test_outcomes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'outcomes'`

- [ ] **Step 4: Implement `miner/outcomes.py`**

```python
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
from typing import NamedTuple

FAILURE = "failure"   # ran, expectation not met -- admissible
ERROR = "error"       # could not run -- not admissible as a base negative
PASSED = "passed"
SKIPPED = "skipped"

PLUGIN_MODULE = "benchme_reporter"
REPORT_ENV = "BENCHME_REPORT"

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
```

Add `import json` at the top of the file, above the `typing` import.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest miner/tests/test_outcomes.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 6: Commit**

```bash
git add miner/reporter_plugin.py miner/outcomes.py miner/tests/test_outcomes.py
git commit -m "feat(miner): structured pytest reporter and outcome collapse"
```

---

## Task 2: The failure label taxonomy

Decisions 1, 3, 4. This is where "label, do not reject" actually lives.

**Files:**
- Modify: `miner/outcomes.py`
- Modify: `miner/tests/test_outcomes.py`

**Interfaces:**
- Consumes: `outcomes.Record` from Task 1.
- Produces: `outcomes.label(message: str | None) -> str`, returning one of
  `"assertion"`, `"expectation"`, `"missing_api"`, `"type_error"`,
  `"exception:<Name>"`, `"unlabelled"`.

**This function never rejects anything.** It is descriptive only. There is no
qualifying label and no disqualifying label. `"unlabelled"` is a statement about
our parser, not about the commit, and it must not gate.

- [ ] **Step 1: Write the failing tests**

Append to `miner/tests/test_outcomes.py`. Every message below is real output
measured from pytest 8.3.4 or from the 2025Q3 pydantic batch.

```python
def test_label_bare_assert():
    assert outcomes.label("assert 1 == 2") == "assertion"


def test_label_named_assertion_error():
    assert outcomes.label("AssertionError: values differ") == "assertion"


def test_label_pytest_expectation_protocol():
    # Round 1 rejected all three of these as `other:unparsed`. They were half
    # of the classified f2p tests in the first batch. They are pytest's own
    # idiom for "the expected thing did not happen".
    assert outcomes.label(
        "Failed: DID NOT RAISE <class 'ValueError'>") == "expectation"
    assert outcomes.label(
        "Failed: DID NOT WARN. No warnings of type (<class 'X'>,) were "
        "emitted.") == "expectation"
    assert outcomes.label("Failed: nope") == "expectation"


def test_label_missing_api_family():
    assert outcomes.label(
        "AttributeError: module 'json' has no attribute 'z'") == "missing_api"
    assert outcomes.label(
        "ModuleNotFoundError: No module named 'x'") == "missing_api"
    assert outcomes.label("ImportError: cannot import name 'y'") == "missing_api"
    assert outcomes.label("NameError: name 'q' is not defined") == "missing_api"


def test_label_type_error_is_its_own_bucket():
    # Kept separate from missing_api: a changed signature is not the same
    # claim as an absent attribute, and round 1 explicitly left this open.
    assert outcomes.label("TypeError: f() takes 1 arg") == "type_error"


def test_label_dotted_library_exception_keeps_the_leaf_name():
    assert outcomes.label(
        "pydantic_core._pydantic_core.ValidationError: 1 validation error "
        "for Model") == "exception:ValidationError"


def test_label_library_warning_class_without_an_error_suffix():
    # PydanticDeprecatedSince20 ends in neither Error nor Exception nor
    # Warning. Matching on a suffix would drop it to unlabelled; matching on
    # "dotted identifier followed by a colon" keeps it.
    assert outcomes.label(
        "pydantic.warnings.PydanticDeprecatedSince20: The `__fields__` "
        "attribute is deprecated") == "exception:PydanticDeprecatedSince20"


def test_label_unrecognised_message_is_unlabelled_not_an_error():
    assert outcomes.label("something we have never seen") == "unlabelled"
    assert outcomes.label(None) == "unlabelled"
    assert outcomes.label("") == "unlabelled"


def test_unlabelled_is_not_a_rejection_signal():
    # Guards the council's central decision against a future "tidy-up" that
    # reintroduces a qualifying-class check. If someone adds a set of
    # acceptable labels, this test should make them think twice.
    for message in ["assert x", "Failed: nope", "AttributeError: nope",
                    "TypeError: nope", "Zzz.Qqq: nope", "gibberish", None]:
        assert isinstance(outcomes.label(message), str)
        assert outcomes.label(message) != ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest miner/tests/test_outcomes.py -v -k label`
Expected: FAIL with `AttributeError: module 'outcomes' has no attribute 'label'`

- [ ] **Step 3: Implement `label`**

Add to `miner/outcomes.py`:

```python
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
```

Add `import re` to the imports at the top of `miner/outcomes.py`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest miner/tests/test_outcomes.py -v`
Expected: PASS, 16 tests.

- [ ] **Step 5: Commit**

```bash
git add miner/outcomes.py miner/tests/test_outcomes.py
git commit -m "feat(miner): descriptive failure labels that never reject"
```

---

## Task 3: Outcome diffing with rename reconciliation

Decision 6. This fixes the measured defect that fabricated three
`regression_broken` verdicts.

**Files:**
- Modify: `miner/outcomes.py`
- Modify: `miner/tests/test_outcomes.py`

**Interfaces:**
- Consumes: the status constants and `collapse` from Task 1.
- Produces: `outcomes.base_id(nodeid: str) -> str` and
  `outcomes.diff(before: dict, after: dict) -> dict` with keys
  `"f2p"`, `"p2p"`, `"broken"`, `"renamed"`, `"error_base"` — every value a
  sorted list of node ids.

**The defect being fixed:** pydantic's `test_docstrings_examples` parametrises
on source line numbers, producing ids like
`test_docstrings_examples[pydantic/types.py:1064-1069]`. Applying the code patch
shifts those lines, so the id changes. The old rule ("passed before, absent
after → broken") booked the rename as the code patch breaking a test.

- [ ] **Step 1: Write the failing tests**

Append to `miner/tests/test_outcomes.py`:

```python
def test_base_id_strips_parametrisation():
    assert outcomes.base_id("t.py::test_a[1-2]") == "t.py::test_a"
    assert outcomes.base_id("t.py::test_a") == "t.py::test_a"
    # Nested brackets: split on the FIRST "[", so the whole tail goes.
    assert outcomes.base_id("t.py::test_a[p[q]]") == "t.py::test_a"
    assert outcomes.base_id("t.py::C::test_a[x - y]") == "t.py::C::test_a"


def test_diff_finds_fail_to_pass_and_pass_to_pass():
    before = {"t.py::new": outcomes.FAILURE, "t.py::old": outcomes.PASSED}
    after = {"t.py::new": outcomes.PASSED, "t.py::old": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["f2p"] == ["t.py::new"]
    assert d["p2p"] == ["t.py::old"]
    assert d["broken"] == []


def test_diff_excludes_an_error_base_from_f2p_and_records_it():
    # Decision 2: a test that could not run is not a usable base negative.
    # It is counted separately so a later audit can measure what the gate
    # costs -- the mistake round 1 made was rejecting without counting.
    before = {"t.py::a": outcomes.ERROR}
    after = {"t.py::a": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["f2p"] == []
    assert d["error_base"] == ["t.py::a"]


def test_diff_reports_a_genuinely_broken_test():
    before = {"t.py::a": outcomes.PASSED}
    after = {"t.py::a": outcomes.FAILURE}
    assert outcomes.diff(before, after)["broken"] == ["t.py::a"]


def test_diff_treats_a_renumbered_parametrisation_as_a_rename():
    # THE MEASURED DEFECT. Line numbers shift when the patch is applied, so
    # the parametrised ids change while the same number of cases still pass.
    # Booking this as `broken` fabricated 3 of the 10 rejections in the
    # 2025Q3 batch.
    before = {
        "t.py::test_docs[pydantic/types.py:1064-1069]": outcomes.PASSED,
        "t.py::test_docs[pydantic/types.py:2001-2010]": outcomes.PASSED,
    }
    after = {
        "t.py::test_docs[pydantic/types.py:1071-1076]": outcomes.PASSED,
        "t.py::test_docs[pydantic/types.py:2008-2017]": outcomes.PASSED,
    }
    d = outcomes.diff(before, after)
    assert d["broken"] == []
    assert d["renamed"] == [
        "t.py::test_docs[pydantic/types.py:1064-1069]",
        "t.py::test_docs[pydantic/types.py:2001-2010]",
    ]


def test_diff_does_not_hide_a_real_loss_behind_a_rename():
    # Two passed before, only one passes after. The count dropped, so this
    # is a genuine loss and must NOT be excused as a rename. Without this the
    # reconciliation would become a blanket amnesty for vanished tests.
    before = {"t.py::test_d[a]": outcomes.PASSED,
              "t.py::test_d[b]": outcomes.PASSED}
    after = {"t.py::test_d[c]": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["renamed"] == []
    assert d["broken"] == ["t.py::test_d[a]", "t.py::test_d[b]"]


def test_diff_treats_a_wholly_vanished_test_as_broken():
    before = {"t.py::gone": outcomes.PASSED}
    after = {}
    assert outcomes.diff(before, after)["broken"] == ["t.py::gone"]


def test_diff_requires_an_exact_nodeid_match_for_f2p():
    # A rename is forgivable for a regression test, which only needs to show
    # nothing was lost. It is NOT forgivable for the oracle: claiming f2p
    # across two differently-named tests would put a test in the oracle that
    # never failed on the before side.
    before = {"t.py::test_d[old]": outcomes.FAILURE}
    after = {"t.py::test_d[new]": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["f2p"] == []


def test_diff_ignores_skipped_tests_entirely():
    before = {"t.py::s": outcomes.SKIPPED}
    after = {"t.py::s": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert all(d[k] == [] for k in ("f2p", "p2p", "broken", "renamed",
                                    "error_base"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest miner/tests/test_outcomes.py -v -k "diff or base_id"`
Expected: FAIL with `AttributeError: module 'outcomes' has no attribute 'base_id'`

- [ ] **Step 3: Implement `base_id` and `diff`**

Add to `miner/outcomes.py`:

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest miner/tests/test_outcomes.py -v`
Expected: PASS, 25 tests.

- [ ] **Step 5: Commit**

```bash
git add miner/outcomes.py miner/tests/test_outcomes.py
git commit -m "fix(miner): reconcile renamed parametrised tests instead of booking them broken"
```

---

## Task 4: Retire the old classifier from validate.py

Decision 5. Pure deletion, so that no code path can reach the retired rule.

**Files:**
- Modify: `miner/validate.py`
- Modify: `miner/tests/test_validate.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `miner/validate.py` exporting only `split_paths`,
  `_belongs_to_test_side` and `make_patch`.

- [ ] **Step 1: Delete the retired code from `miner/validate.py`**

Delete these, entire:
- `diff_outcomes` (superseded by `outcomes.diff`)
- `parse_failures` (superseded by the reporter)
- `classify` (superseded by `outcomes.label`)
- `_split_nodeid_detail`
- the `LINE` and `EXC_NAME` regexes
- the `MISSING_API`, `STRUCTURAL` and `FAILURE_CLASSES` constants
- the long module-level comment block above `LINE` about COLUMNS/CI and node
  ids containing `" - "` — it documents a parsing approach that no longer
  exists
- the now-unused `import re`

Keep `import subprocess`, `import sys`, the `pathlib` imports and the
`metrics` import.

- [ ] **Step 2: Update the module docstring**

Replace the docstring at the top of `miner/validate.py` with:

```python
"""Stage 2 patch and path logic. No I/O beyond `git diff`, no containers.

Reading a test run is NOT here -- see miner/outcomes.py. The two were split
when the exception-name classifier was retired: this module answers "which
side of the patch does this path belong on", outcomes.py answers "what did
the run say". Both are pure and unit-tested.

Each function here fails SILENTLY if wrong: a bad patch split hands the agent
the answer or strips the fix.
"""
```

- [ ] **Step 3: Delete the corresponding tests**

In `miner/tests/test_validate.py`, delete every test that references
`validate.diff_outcomes`, `validate.parse_failures` or `validate.classify`.
Keep `test_split_paths_separates_tests_from_code` and any other `split_paths`
or `make_patch` coverage.

- [ ] **Step 4: Verify nothing still references the deleted names**

Run:

```bash
grep -rn "parse_failures\|validate.classify\|validate.diff_outcomes\|FAILURE_CLASSES" miner/ --include=*.py
```

Expected: matches ONLY in `miner/runner.py`, which Task 5 rewrites. If anything
else matches, stop and report it rather than editing beyond this task's files.

- [ ] **Step 5: Run the unit tests**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS. `test_outcomes.py` fully green; `test_validate.py` green with
the deleted tests gone.

- [ ] **Step 6: Commit**

```bash
git add miner/validate.py miner/tests/test_validate.py
git commit -m "refactor(miner): retire the exception-name classifier"
```

---

## Task 5: Wire the reporter into the runner

Decisions 1, 2, 5, 8. The runner stops scraping stdout and stops gating on
failure kind.

**Files:**
- Modify: `miner/quarters.py`
- Modify: `miner/runner.py`

**Interfaces:**
- Consumes: `outcomes.parse_report`, `outcomes.collapse`, `outcomes.diff`,
  `outcomes.label`, `outcomes.PLUGIN_MODULE`, `outcomes.REPORT_ENV`.
- Produces: `quarters.install_reporter(container) -> str | None` returning an
  error string or None; `runner._pytest(...)` returning
  `(status_map, collect_errors, log_text)`.

- [ ] **Step 1: Add `install_reporter` to `miner/quarters.py`**

Add near `start_container`:

```python
REPORTER_DIR = "/opt/benchme"
# The plugin's module name and the variable it reads its output path from.
# These live here rather than in outcomes.py because they are facts about
# INSTALLING the plugin; outcomes.py only parses what it writes and stays free
# of any container knowledge.
PLUGIN_MODULE = "benchme_reporter"
REPORT_ENV = "BENCHME_REPORT"


def install_reporter(container):
    """Write the pytest reporter plugin into a running container.

    Once per container, not per candidate. Lives outside the checkout so it
    cannot be collected as a test, cannot appear in `git status` inside the
    workdir, and survives the workdir being deleted between candidates.

    Written as BYTES for the same reason runner._apply is: subprocess wraps a
    text-mode stdin in a TextIOWrapper with newline=None, which on Windows
    turns every "\\n" into "\\r\\n". A CRLF Python file still imports, but the
    same defect silently corrupted patch application twice before, so the
    habit is worth keeping.
    """
    source = (Path(__file__).resolve().parent / "reporter_plugin.py").read_bytes()
    target = f"{REPORTER_DIR}/{PLUGIN_MODULE}.py"
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "sh", "-c",
         f"mkdir -p {REPORTER_DIR} && cat > {target}"],
        input=source, capture_output=True, env=tierb.docker_env())
    if proc.returncode != 0:
        return f"could not install reporter: {proc.stderr.decode()[:200]}"
    return None
```

`Path`, `subprocess` and `tierb` are already imported in `miner/quarters.py`
(verified). Do **not** import `outcomes` there — see the note in Task 1.

- [ ] **Step 2: Update the pytest invocation in `miner/runner.py`**

Replace the `PYTEST_ENV` and `PYTEST_EXTRA` constants and their comment blocks
with:

```python
# The reporter plugin reads its destination from this variable; the runner
# passes a distinct path per phase so the two runs cannot append to one file.
#
# COLUMNS/CI are gone: they existed only to stop pytest truncating the
# short-summary detail to terminal width. The reporter takes its message from
# report.longrepr.reprcrash, which is never truncated -- verified against
# pytest 8.3.4, including under the --tb=no already in tierb.PYTEST_ARGV.
#
# `-p no:pretty` is also gone as a correctness measure. pytest-pretty replaced
# the summary block, which used to blind the old parser completely; the
# reporter hooks pytest_runtest_logreport and is indifferent to whatever the
# terminal reporter does.
#
# `--continue-on-collection-errors` is load-bearing. Measured: with one broken
# import present, a 20-test run reported 1 test -- a single collection error
# aborts the whole session, so an unrelated bad file silently zeroes a
# candidate's outcomes and it books as apparatus or `rejected:unchanged`.
PYTEST_EXTRA = ["--continue-on-collection-errors"]
```

- [ ] **Step 3: Rewrite `_pytest` to read the reporter**

Replace the whole `_pytest` function with:

```python
def _pytest(container, workdir, targets, log_path, phase, timeout=1800):
    """Run pytest on `targets`; return (status_map, collect_errors, output).

    `status_map` is node id -> one of outcomes.FAILURE/ERROR/PASSED/SKIPPED.
    Raises ValueError (from outcomes.parse_report) when the report is
    malformed; the caller books that as apparatus.

    The checkout goes on PYTHONPATH because the image deliberately does NOT
    contain the project itself -- see quarters' module docstring. The reporter
    directory goes on PYTHONPATH too, so `-p benchme_reporter` can import it.
    """
    report_path = f"/tmp/benchme-{phase}-{Path(workdir).name}.jsonl"
    wd = shlex.quote(workdir)
    cmd = (
        "cd {wd} && rm -f {rp} && {env}={rp} PYTHONPATH={rd}:{wd} "
        "{argv} -p {plugin} {t} 2>&1"
    ).format(
        wd=wd, rp=shlex.quote(report_path), env=quarters.REPORT_ENV,
        rd=quarters.REPORTER_DIR, plugin=quarters.PLUGIN_MODULE,
        argv=" ".join([*tierb.PYTEST_ARGV, *PYTEST_EXTRA]),
        t=" ".join(shlex.quote(t) for t in targets))
    r = _guard(quarters.exec_in(container, ["sh", "-c", cmd], timeout=timeout),
               "pytest")
    out = r.stdout + r.stderr
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    Path(log_path).write_text(f"$ {cmd}\n{out}", encoding="utf-8")

    # Read the report as a SEPARATE exec. Interleaving it into the pytest
    # command would mix it with pytest's own stdout, which is exactly the
    # coupling this redesign removes.
    rr = _guard(quarters.exec_in(container, ["cat", report_path]),
                "read report")
    if rr.returncode != 0:
        # An empty or absent report is indistinguishable from "no tests ran"
        # to every downstream check, so it must surface here rather than
        # become `rejected:unchanged`.
        raise ValueError(
            f"reporter wrote nothing for the {phase} run (rc={rr.returncode}); "
            f"pytest exited {r.returncode}: {out[-300:]}")
    tests, collect = outcomes.parse_report(rr.stdout)
    return outcomes.collapse(tests), collect, out
```

Add `import outcomes` to the imports in `miner/runner.py`.

- [ ] **Step 4: Install the reporter when the container starts**

In `validate_quarter`, immediately after the `if not cid:` guard:

```python
    err = quarters.install_reporter(cid)
    if err:
        quarters.stop_container(cid)
        raise SystemExit(f"{quarter}: {err}")
```

- [ ] **Step 5: Rewrite the measurement body of `_measure`**

Replace everything from the `before_out = _pytest(...)` line to the end of the
function with:

```python
    try:
        before, before_collect, _ = _pytest(
            container, workdir, targets, logs / f"{BEFORE}.log", BEFORE)
    except ValueError as exc:
        out.update(status="apparatus", reason=f"before report: {exc}"[:300])
        return out
    # Recorded on every candidate that got a before run, because it is the
    # only way to audit a `rejected:unchanged` afterwards. The image is
    # anchored to the lockfile at the quarter's LAST commit, so a candidate
    # from mid-quarter can see hundreds of failures that have nothing to do
    # with it (measured: 840 of 6437 on 2025Q3, from a pydantic-core version
    # skew).
    out["before_failed"] = sum(1 for v in before.values()
                               if v == outcomes.FAILURE)
    out["before_collect_errors"] = [r.nodeid for r in before_collect]

    err = _apply(container, workdir, code_patch, "code")
    if err:
        out.update(status="apparatus", reason=err)
        return out

    try:
        after, after_collect, _ = _pytest(
            container, workdir, targets, logs / f"{AFTER}.log", AFTER)
    except ValueError as exc:
        out.update(status="apparatus", reason=f"after report: {exc}"[:300])
        return out
    out["after_collect_errors"] = [r.nodeid for r in after_collect]

    if not before:
        out.update(status="apparatus",
                   reason="no test outcomes on the before side")
        return out
    # The after side needs the same guard. An empty after makes every f2p
    # comparison fail, so diff["f2p"] is empty and the next branch books
    # `rejected:unchanged`: apparatus wearing a verdict.
    if not after:
        out.update(status="apparatus",
                   reason="no test outcomes on the after side")
        return out

    d = outcomes.diff(before, after)
    out["f2p"] = d["f2p"]
    out["p2p_count"] = len(d["p2p"])
    out["broken"] = d["broken"]
    out["renamed"] = d["renamed"]
    out["error_base"] = d["error_base"]
    out["tests_seen"] = len(before)

    if not d["f2p"]:
        # error_base is spelled out in the reason because it is the one
        # rejection the new contract still makes on failure kind, and it is
        # the number a future audit of decision 2 will need.
        detail = "no test went fail->pass"
        if d["error_base"]:
            detail += (f"; {len(d['error_base'])} test(s) went error->pass, "
                       f"which is not an admissible base negative")
        out.update(status="rejected:unchanged", reason=detail)
        return out

    # LABEL, never gate. Round 1 required an assertion-class base negative;
    # round 2 retired that rule because fail-to-pass against the genuine
    # upstream fix already establishes the failure was caused by the missing
    # fix. A node id with no reporter message still gets a label
    # ("unlabelled") rather than being rejected or defaulted to a qualifying
    # class -- see outcomes.label.
    messages = {r.nodeid: r.message for r in
                [rec for rec in _before_records] if r.nodeid in d["f2p"]}
    out["failure_labels"] = {t: outcomes.label(messages.get(t))
                             for t in d["f2p"]}

    if pass2 and d["broken"]:
        out.update(status="rejected:regression_broken",
                   reason=f"{len(d['broken'])} previously-passing tests fail "
                          f"after the code patch")
        return out

    out.update(status="validated" if pass2 else "pass1_ok", reason=None)
    return out
```

**Note for the implementer:** the `messages` line above references
`_before_records`, which does not exist yet. `_pytest` currently returns a
collapsed status map and discards the per-record messages. Change `_pytest` to
return the test records as a fourth element — `(status_map, collect_errors,
records, output)` — thread it through both call sites, and build `messages`
from the before-run records directly:

```python
    messages = {r.nodeid: r.message for r in before_records
                if r.nodeid in set(d["f2p"])}
```

Update the `Produces` interface note accordingly. Do not fake this with a
second pytest run.

- [ ] **Step 6: Verify no gate on failure kind survives**

Run:

```bash
grep -n "assertion\|missing_api\|structural" miner/runner.py
```

Expected: no match that participates in a status decision. The only
`rejected:` statuses reachable in `_measure` must now be `rejected:unchanged`
and `rejected:regression_broken`.

- [ ] **Step 7: Run the unit tests**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add miner/quarters.py miner/runner.py
git commit -m "feat(miner): read a structured reporter; label failures instead of rejecting"
```

---

## Task 6: Determinism, non-pytest directories, and the funnel report

Decisions 7, 12, 13.

**Files:**
- Modify: `miner/runner.py`
- Modify: `miner/candidates.py`
- Modify: `miner/report.py`
- Modify: `miner/record.py` (docstring only)

**Interfaces:**
- Consumes: everything from Task 5.
- Produces: records carrying `"f2p_reproduced"` (list) and
  `"f2p_pass1"` (list); `candidates.NON_PYTEST_TEST_DIRS`.

- [ ] **Step 1: Require pass 2 to reproduce pass 1's oracle**

The council asked for an independent paired rerun. Pass 2 already provides one
for free: it is a fresh clone, a fresh patch application, and a full-suite
selection rather than the touched files. Requiring pass 1's f2p set to
reproduce there is therefore a *stronger* check than repeating pass 1, because
it also catches a test that only fails when run in isolation. No extra
container time.

In `validate_quarter`, carry pass 1's f2p forward. Change the survivor list to
hold `(cand, f2p)` pairs:

```python
        survivors = []
        try:
            for cand in queue:
                rec = attempt(cand, pass2=False)
                if rec["status"] == "pass1_ok":
                    survivors.append((cand, rec["f2p"]))
                else:
                    write(rec)
            for cand, pass1_f2p in survivors:
                write(attempt(cand, pass2=True, pass1_f2p=pass1_f2p))
```

Thread `pass1_f2p` through `attempt`, `validate_one` and `_measure` as a
keyword argument defaulting to `None`.

In `_measure`, immediately before the `pass2 and d["broken"]` check:

```python
    if pass2:
        # Decision 7: the transition must reproduce. Pass 2 is an independent
        # measurement -- fresh clone, fresh patch, full-suite selection rather
        # than the touched files -- so an f2p that appears in pass 1 and not
        # here is either flaky or selection-dependent. Kimi's point in round
        # 2: flakiness, not taxonomy, is the plausible mechanism by which a
        # test "passes for unrelated reasons".
        reproduced = [t for t in (pass1_f2p or []) if t in set(d["f2p"])]
        out["f2p_pass1"] = sorted(pass1_f2p or [])
        out["f2p_reproduced"] = sorted(reproduced)
        if pass1_f2p and not reproduced:
            out.update(
                status="rejected:unstable",
                reason=f"none of {len(pass1_f2p)} pass-1 fail->pass test(s) "
                       f"reproduced in the full-suite run")
            return out
        if reproduced:
            # The oracle is the INTERSECTION. A test that only flips in one of
            # the two runs is not something we are willing to grade an agent
            # on.
            out["f2p"] = sorted(reproduced)
```

- [ ] **Step 2: Filter directories that are not pytest tests**

Eight of the ten apparatus cases in the 2025Q3 batch pointed pytest at
`tests/typechecking/*.py`, which are mypy/pyright fixtures, not pytest tests.
They collect nothing, so the run produces no outcomes and a good candidate
books as apparatus.

Add to `miner/candidates.py`, near the other module constants:

```python
# Paths that satisfy metrics.is_test_file but are not pytest tests, so
# pointing pytest at them collects nothing and the candidate books as
# apparatus. Deliberately explicit per-repo config rather than a heuristic:
# a heuristic that guessed wrong would silently drop real tests, and the
# whole point of this redesign is that our defects must not become verdicts.
#
# pydantic/tests/typechecking: static type-checker fixtures, asserted by mypy
# and pyright, never executed by pytest. Eight of ten apparatus cases in the
# first 2025Q3 batch.
NON_PYTEST_TEST_DIRS = {
    "pydantic": ("tests/typechecking/",),
}


def is_non_pytest_test(repo_name, path):
    return any(path.startswith(prefix)
               for prefix in NON_PYTEST_TEST_DIRS.get(repo_name, ()))
```

In `runner._runnable_targets`, extend the `wanted` filter:

```python
    wanted = [t for t in tests
              if metrics.is_test_file(t)
              and PurePosixPath(t).name != "conftest.py"
              and not candidates.is_non_pytest_test(record.REPO.name, t)]
```

Add `import candidates` to `miner/runner.py`.

- [ ] **Step 3: Report composition and the apparatus tripwire**

Decision 12 is the chair's answer to Kimi's objection that labels only help if
someone looks at them: the mix is printed on every run, not left to an optional
analysis.

`miner/report.py` builds a markdown document by appending to a list `out`;
every section is a `_name(out, ...)` function called from `render()`. Follow
that convention exactly — do not invent a different return style.

Add to `miner/report.py`:

```python
APPARATUS_TRIPWIRE = 10.0


def _composition(out, done):
    """Label mix across validated oracles, plus the apparatus tripwire.

    Emitted unconditionally, including when it is empty. Round 2 retired
    failure kind as a gate on the understanding that composition becomes a
    REPORTED property -- the chair's answer to the objection that labels only
    protect the corpus if someone actually looks at them. A section that
    disappears when it has nothing to say is a section nobody notices is
    missing.
    """
    labels = Counter()
    for rec in done:
        if rec.get("status") == "validated":
            labels.update((rec.get("failure_labels") or {}).values())
    total = sum(labels.values())

    out += ["## Oracle composition", "",
            "How the fail-to-pass tests failed, across validated capsules. "
            "Descriptive only -- no label gates admission "
            "(`docs/council/ROUND_02_SYNTHESIS.md`).", ""]
    if not total:
        out += ["_No validated capsules yet._", ""]
    else:
        out += ["| label | count | share |", "|---|---|---|"]
        for lbl, n in labels.most_common():
            out.append(f"| `{lbl}` | {n} | {100.0 * n / total:.1f}% |")
        out.append("")

    adjudicated = [r for r in done if r.get("status") != "error"]
    if adjudicated:
        apparatus = [r for r in adjudicated if r.get("status") == "apparatus"]
        rate = 100.0 * len(apparatus) / len(adjudicated)
        out += [f"Apparatus: {len(apparatus)}/{len(adjudicated)} adjudicated "
                f"candidates ({rate:.1f}%).", ""]
        # Decision 13. The first 2025Q3 batch ran at 48%: mining on would have
        # spent candidates on our own defects and called the result a yield.
        if rate > APPARATUS_TRIPWIRE:
            out += [f"> **TRIPWIRE** apparatus is {rate:.1f}%, above the "
                    f"{APPARATUS_TRIPWIRE:.0f}% threshold. Stop mining and fix "
                    f"tooling before spending more of the corpus.", ""]
```

Call it from `render()`, after `_verdicts(out, done)`:

```python
    _verdicts(out, done)
    _composition(out, done)
```

- [ ] **Step 3b: Retire the dead rejection-class section**

`_rejections` renders `missing_api` and the other base-negative classes,
"emitted at both levels even when zero: the whole point of the number is to
price the assertion-only rule". The assertion-only rule is gone, so those rows
now price nothing and would show a permanent zero that reads like evidence.

Remove the base-negative-class portion of `_rejections` and its
`missing_api`-always-emitted logic. Keep the top-level rejection-class table —
`rejected:unchanged`, `rejected:regression_broken` and `rejected:unstable` are
all still real. Update the docstring to say why the base-negative breakdown was
removed and point at the round 2 synthesis.

- [ ] **Step 3c: Update the status vocabulary in `record.py`**

`miner/record.py`'s module docstring describes `validated` as "fail-to-pass
established, assertion-class, regressions clean". Assertion-class is retired.
Change that line to:

```
  validated          fail-to-pass established and reproduced, regressions clean
```

`is_done` needs no change: it already matches `rejected:` by prefix, so
`rejected:unstable` is terminal automatically (verified).

- [ ] **Step 4: Run the unit tests**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add miner/runner.py miner/candidates.py miner/report.py miner/record.py
git commit -m "feat(miner): determinism check, non-pytest dir filter, composition report"
```

---

## Task 7: Re-run 2025Q3 as a known-answer regression

The 2025Q3 batch has been hand-audited. That audit is now the test: the new
classifier must reproduce the outcomes we established by hand, and must convert
the seven defect-driven rejections into something other than a rejection.

**Files:**
- Create: `docs/miner/2025Q3-rerun.md`
- Modify: none (this task runs the miner and records what happened)

- [ ] **Step 1: Archive the old results so the comparison is possible**

```bash
cp miner/out/validated.jsonl miner/out/validated.2025Q3-preredesign.jsonl
git add miner/out/validated.2025Q3-preredesign.jsonl
git commit -m "chore(miner): archive pre-redesign 2025Q3 results for comparison"
```

- [ ] **Step 2: Re-run the same 21 candidates**

```bash
python miner/mine.py validate --quarter 2025Q3 --limit 21 --force
```

- [ ] **Step 3: Write the comparison**

Create `docs/miner/2025Q3-rerun.md` recording, per candidate sha, the old
status and the new one. State plainly for each of the ten previously-rejected
candidates which of these happened:

- the rejection was a defect and the candidate now validates
- the rejection was a defect and the candidate now fails for a *different*
  reason (say which)
- the rejection stands

**Expected, from the hand audit — these are predictions, not targets. Record
what actually happens, including where it contradicts this list:**

- 3 × `regression_broken` on `test_docstrings_examples` — the ids should now
  reconcile as `renamed`, so these should no longer be rejected on that ground.
- 4 × `other:unparsed` — should now be labelled `expectation` or
  `exception:*` and admitted.
- 8 × apparatus on `tests/typechecking/` — should no longer be attempted.
- 2 × apparatus on grafted pydantic-core commits — expected to remain
  apparatus. This redesign does not address them.

- [ ] **Step 4: Report honestly, including regressions**

If the new run validates fewer candidates than the audit predicted, say so and
diagnose before proceeding. If it validates *more* than the audit predicted,
that is not automatically good news — check that each new validation has a real
f2p set and a plausible label, because the whole risk of retiring a gate is
admitting something that should not have been admitted.

- [ ] **Step 5: Commit**

```bash
git add docs/miner/2025Q3-rerun.md miner/out/
git commit -m "test(miner): 2025Q3 known-answer rerun against the hand audit"
```

---

## Self-Review Notes

**Spec coverage.** Council decisions 1–9 and 12–13 each map to a task: 1/3/4 →
Task 2; 2 → Tasks 1 and 3; 5 → Tasks 1, 4, 5; 6 → Task 3; 7 → Task 6; 8 → Task
5; 9 → not miner work; 10 and 11 → explicitly out of scope, stated above; 12
and 13 → Task 6. Decision 14 requires no change.

**Known rough edge, flagged rather than hidden.** Task 5 Step 5 initially
writes a `messages` expression that references a name `_before_records` which
does not exist, then instructs the implementer to change `_pytest`'s return
signature to supply it. That is deliberate — it is the one place where the
required change is a signature change rippling through two call sites, and
burying it would produce a subtly broken implementation. The implementer must
do the signature change, not paper over it.

**Type consistency.** `outcomes.diff` returns the five keys `f2p`, `p2p`,
`broken`, `renamed`, `error_base` in Task 3 and every consumer in Tasks 5 and 6
uses exactly those. `outcomes.label` returns a string in every branch. Record
fields written by the runner: `f2p`, `p2p_count`, `broken`, `renamed`,
`error_base`, `tests_seen`, `before_failed`, `before_collect_errors`,
`after_collect_errors`, `failure_labels`, `f2p_pass1`, `f2p_reproduced`.
`report.composition` reads `status` and `failure_labels` only.

**Status vocabulary after this plan.** `validated`, `pass1_ok`, `apparatus`,
`error`, `rejected:unchanged`, `rejected:regression_broken`,
`rejected:unstable`. The classes `rejected:missing_api`,
`rejected:structural` and `rejected:other` are gone. `record.is_done` treats
`rejected:*` as terminal by prefix, so `rejected:unstable` needs no change
there — verify this when implementing Task 6.
