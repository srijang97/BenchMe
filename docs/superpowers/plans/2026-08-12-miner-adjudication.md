# Miner Adjudication and Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move every verdict decision out of `_measure` into a pure, unit-tested
adjudicator, add the arms that stop our own failures being recorded as verdicts
about commits, then sweep pydantic's v2 era.

**Architecture:** `_measure` becomes gather → adjudicate → record. A new pure
module `miner/adjudicate.py` owns the outcome diff, the failure labelling and
every decision arm, taking a `Measurements` namedtuple and returning a `Verdict`.
No I/O, so all arms are testable with plain dicts. Migration is extract-then-extend:
Task 1 moves existing behaviour with tests pinning it, Tasks 2–4 add new arms.

**Tech Stack:** Python 3 standard library only, pytest, Docker, git.

**Spec:** `docs/superpowers/specs/2026-08-12-miner-adjudication-and-sweep-design.md`

## Global Constraints

- **`rejected:*` is a verdict about the commit. `not_minable:*` means the commit
  is outside what this method can measure. `apparatus` is our tooling failing.
  `error` is a miner bug or transient infrastructure and is NON-terminal.** Never
  let one become another. This is the project's central discipline
  (`docs/AGENTS_LOG.md` standing rule 6).
- **Never default a missing or unparseable value to a qualifying outcome**
  (`validated`, `pass1_ok`). Silently rejecting a valid candidate shrinks the
  corpus; silently admitting an invalid one corrupts every number downstream.
- **Over-correcting is also a defect.** `apparatus` and `not_minable:*` are both
  terminal. Booking one of them where the honest answer is a verdict silently
  shrinks the corpus just as badly.
- **Do NOT modify `screener/metrics.py` or `screener/tierb.py`.** Both are shared
  with merged code.
- Python standard library only. No new third-party dependencies.
- Unit tests live in `miner/tests/`, run from the repo root with
  `python -m pytest miner/tests/ -v`. **There are 90 tests today and every one
  must stay green.** No assertion may be weakened to accommodate a new signature.
- Every design decision traces to the spec. Row numbers below refer to its §4
  verdict table.

### Status vocabulary after this plan

```
validated  pass1_ok
rejected:unchanged  rejected:no_runnable_tests  rejected:base_import_blocked
rejected:unstable   rejected:regression_broken
not_minable:foreign_project  not_minable:straddles_dependency_bump
not_minable:no_pytest_tests
apparatus  error
```

`record.is_done` currently matches `validated`, `apparatus`, and the `rejected:`
prefix. **`not_minable:` must be added** — it is terminal.

---

## File Structure

| File | Responsibility |
|---|---|
| `miner/adjudicate.py` | **Create.** Pure verdict logic: `Measurements` in, `Verdict` out. Owns the diff, the labels and every arm. |
| `miner/tests/test_adjudicate.py` | **Create.** One test per arm plus explicit ordering tests. |
| `miner/runner.py` | **Modify.** `_measure` becomes gather → adjudicate → record. `check_pass2_determinism`, `_labels_for` and the `EMPTY_*`/`PASS2_*` constants move out. |
| `miner/tests/test_runner.py` | **Modify.** Tests for moved functions follow them to `test_adjudicate.py`. |
| `miner/candidates.py` | **Modify.** Foreign-project and dependency-boundary filters. |
| `miner/tests/test_candidates.py` | **Create.** Unit tests for both filters. |
| `miner/record.py` | **Modify.** `is_done` recognises `not_minable:`. |
| `miner/report.py` | **Modify.** Report the `not_minable:*` family separately; pin the conversion denominators. |
| `docs/miner/2026-08-12-sweep-predictions.md` | **Create.** Committed before the sweep runs. |

---

## Task 1: Extract the adjudicator, behaviour unchanged

Spec §3. **This task changes no behaviour.** It moves decisions into a pure
function and pins them with tests. Any behaviour change here is a defect.

**Files:**
- Create: `miner/adjudicate.py`
- Create: `miner/tests/test_adjudicate.py`
- Modify: `miner/runner.py` — the pieces that move, at their current lines:
  `EMPTY_*` + `EMPTY_IS_A_VERDICT` (276–284), `PASS2_*` (435–438), `Pass2Check`
  (~439), `check_pass2_determinism` (443–491), `_labels_for` (493–510), and the
  decision arms inside `_measure` (548–915). `RunnableTargets` (287–299) and
  `_runnable_targets` (301–391) **stay** — they do I/O.
- Modify: `miner/tests/test_runner.py`

**Interfaces:**
- Consumes: `miner/outcomes.py` — `FAILURE`/`ERROR`/`PASSED`/`SKIPPED`,
  `Record(nodeid, when, outcome, message)`, `diff(before, after)` returning the
  six keys `f2p`/`p2p`/`broken`/`renamed`/`error_base`/`skipped_after`,
  `label(message)`.
- Produces:
  - `adjudicate.Measurements` and `adjudicate.Verdict` (fields below)
  - `adjudicate.adjudicate(m) -> Verdict`
  - `adjudicate.EMPTY_FILTERED`, `EMPTY_NOT_RUNNABLE`, `EMPTY_ABSENT`,
    `EMPTY_DELETED`, `EMPTY_OK`
  - `adjudicate.PASS2_ERROR`, `PASS2_APPARATUS`, `PASS2_UNSTABLE`,
    `PASS2_REPRODUCED`, `Pass2Check`, `check_pass2_determinism`
  - `adjudicate.labels_for(before_records, f2p)`

- [ ] **Step 1: Read the code you are moving**

Read `miner/runner.py` in full. The pieces that move are: the `EMPTY_*`
constants and `EMPTY_IS_A_VERDICT` (~line 276), `RunnableTargets` (~287),
`PASS2_*` and `Pass2Check` (~435), `check_pass2_determinism` (~443),
`_labels_for` (~493), and every decision arm inside `_measure` (~548–915).

Write down each arm as `(condition, status, reason)` before you touch anything.
There are 19 `status=` assignments and 13 early returns. You will need that list
in Step 3.

- [ ] **Step 2: Write the failing tests**

Create `miner/tests/test_adjudicate.py`. These pin **current** behaviour.

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adjudicate  # noqa: E402
import outcomes  # noqa: E402


def _m(**kw):
    """A Measurements with harmless defaults; override what the test is about."""
    base = dict(
        pass2=False,
        targets=adjudicate.TargetSelection(["tests/test_a.py"], adjudicate.EMPTY_OK, None),
        before={}, after={}, before_records=[], before_collect=[],
        after_collect=[], pass1_f2p=None,
    )
    base.update(kw)
    return adjudicate.Measurements(**base)


def test_no_test_paths_is_a_verdict():
    v = adjudicate.adjudicate(_m(
        targets=adjudicate.TargetSelection([], adjudicate.EMPTY_NO_TEST_PATHS, None)))
    assert v.status == "rejected:unchanged"


def test_deleted_targets_are_a_verdict():
    v = adjudicate.adjudicate(_m(
        targets=adjudicate.TargetSelection([], adjudicate.EMPTY_DELETED,
                                           "tests/test_gone.py")))
    assert v.status == "rejected:no_runnable_tests"


def test_absent_targets_are_ours():
    v = adjudicate.adjudicate(_m(
        targets=adjudicate.TargetSelection([], adjudicate.EMPTY_ABSENT, "tests/x.py")))
    assert v.status == "apparatus"


def test_empty_before_is_apparatus():
    v = adjudicate.adjudicate(_m(before={}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "apparatus"
    assert "before" in v.reason


def test_empty_after_is_apparatus():
    v = adjudicate.adjudicate(_m(before={"t.py::a": outcomes.PASSED}, after={}))
    assert v.status == "apparatus"
    assert "after" in v.reason


def test_no_f2p_is_unchanged():
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.PASSED}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "rejected:unchanged"


def test_pass1_success_records_the_oracle_and_its_label():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED},
        before_records=recs))
    assert v.status == "pass1_ok"
    assert v.fields["f2p"] == ["t.py::a"]
    assert v.fields["failure_labels"] == {"t.py::a": "assertion"}


def test_pass2_success_is_validated():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"], before_records=recs,
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "validated"
    assert v.fields["f2p_reproduced"] == ["t.py::a"]


def test_pass2_missing_pass1_oracle_is_a_miner_bug():
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=None,
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "error"


def test_pass2_unmeasured_oracle_is_apparatus():
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::gone"],
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "apparatus"


def test_pass2_measured_but_unreproduced_is_unstable():
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"],
        before={"t.py::a": outcomes.PASSED, "t.py::b": outcomes.FAILURE},
        after={"t.py::a": outcomes.PASSED, "t.py::b": outcomes.PASSED}))
    assert v.status == "rejected:unstable"
    assert v.fields["f2p"] == []


def test_pass2_regression_is_a_verdict():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"], before_records=recs,
        before={"t.py::a": outcomes.FAILURE, "t.py::keep": outcomes.PASSED},
        after={"t.py::a": outcomes.PASSED, "t.py::keep": outcomes.FAILURE}))
    assert v.status == "rejected:regression_broken"


def test_adjudicate_performs_no_io():
    """Guards the whole point of the extraction. If this module ever imports
    subprocess, quarters or record, the arms stop being testable without
    Docker and the ordering bugs come back."""
    src = (Path(__file__).resolve().parents[1] / "adjudicate.py").read_text(
        encoding="utf-8")
    for banned in ("import subprocess", "import quarters", "import record",
                   "import tierb", "open("):
        assert banned not in src, f"adjudicate.py must not use {banned!r}"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest miner/tests/test_adjudicate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'adjudicate'`

- [ ] **Step 4: Create `miner/adjudicate.py`**

Move — do not rewrite — the pieces listed in Step 1. Add the two namedtuples and
the `adjudicate` entry point. The arm order must reproduce `_measure`'s current
order exactly; you wrote that list down in Step 1.

```python
"""Pure verdict logic for stage 2. No I/O: no Docker, no git, no filesystem.

Split out of runner._measure, which had grown to 370 lines with 19 status
assignments and 13 early returns. Every fix round in the previous phase was an
ORDERING bug in that function -- an arm firing before another that should have
won -- and none was catchable by unit test, because _measure needs a container.

The three-way status discipline this module exists to protect:

  rejected:<reason>   a verdict about the COMMIT
  not_minable:<why>   the commit is outside what this method can measure
  apparatus           OUR tooling failed
  error               a miner bug or transient infrastructure; NON-terminal

Arm order is the design. Read `adjudicate` top to bottom; first match wins.
"""
from typing import NamedTuple

import outcomes

EMPTY_OK = "ok"                        # targets is non-empty
EMPTY_NO_TEST_PATHS = "no_test_paths"  # the commit changed no test files
EMPTY_FILTERED = "filtered"            # dropped by NON_PYTEST_TEST_DIRS
EMPTY_NOT_RUNNABLE = "not_runnable"    # fixtures/conftest only, nothing to run
EMPTY_ABSENT = "absent"                # not present, and not because of deletion
EMPTY_DELETED = "deleted"              # the COMMIT deleted its test files

PASS2_ERROR = "error"
PASS2_APPARATUS = "apparatus"
PASS2_UNSTABLE = "unstable"
PASS2_REPRODUCED = "reproduced"


class TargetSelection(NamedTuple):
    paths: list
    why: str        # one of the EMPTY_* constants
    detail: str     # human string naming the paths involved, or None


class Measurements(NamedTuple):
    pass2: bool
    targets: TargetSelection
    before: dict            # nodeid -> outcomes status
    after: dict             # nodeid -> outcomes status
    before_records: list    # outcomes.Record
    before_collect: list    # file paths that failed to collect
    after_collect: list
    pass1_f2p: list         # None on pass 1


class Verdict(NamedTuple):
    status: str
    reason: str
    fields: dict


class Pass2Check(NamedTuple):
    kind: str
    never_measured: list
    reproduced: list
```

Then port `check_pass2_determinism` and `_labels_for` (renamed `labels_for`,
now public since `runner.py` no longer owns them) verbatim, and write
`adjudicate(m)` as a straight transcription of `_measure`'s arms in their
current order.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest miner/tests/test_adjudicate.py -v`
Expected: PASS, 13 tests.

- [ ] **Step 6: Rewire `runner._measure`**

`_measure` keeps every `_checkout` / `_apply` / `_pytest` call and every
`out[...]` assignment that records *evidence* (`before_failed`,
`before_collect_errors`, `tests_seen`, `anchored`). It stops making decisions:
it builds a `Measurements`, calls `adjudicate`, and applies the result.

Two things must still short-circuit inside `_measure`, because they happen
before there is anything to adjudicate: an I/O failure returning a `Failure`
(clone, checkout, patch), and a `ValueError` from `_pytest`. Keep those exactly
as they are.

Delete from `runner.py`: the `EMPTY_*` constants, `EMPTY_IS_A_VERDICT`,
`PASS2_*`, `Pass2Check`, `check_pass2_determinism`, `_labels_for`. Import them
from `adjudicate` where still referenced. `RunnableTargets` stays in `runner.py`
— it is the probe's return type and carries `err`, which is I/O — but
`_measure` converts it into a `TargetSelection` before adjudicating.

- [ ] **Step 7: Move the tests that follow the code**

Tests in `miner/tests/test_runner.py` that exercise `check_pass2_determinism`
move to `test_adjudicate.py` and import from `adjudicate`. **Move them; do not
rewrite or weaken them.** Tests exercising `_pass2_targets`, `_runnable_targets`
or `is_non_pytest_test` stay in `test_runner.py`.

- [ ] **Step 8: Verify nothing regressed**

```bash
python -m pytest miner/tests/ -v
python -c "import sys; sys.path.insert(0,'screener'); sys.path.insert(0,'miner'); import runner, quarters, outcomes, adjudicate, report, candidates, record; print('ok')"
grep -n "check_pass2_determinism\|_labels_for\|EMPTY_IS_A_VERDICT" miner/runner.py
```

Expected: all tests pass (90 existing + 13 new = 103); imports clean; the grep
returns nothing.

- [ ] **Step 9: Commit**

```bash
git add miner/adjudicate.py miner/runner.py miner/tests/
git commit -m "refactor(miner): extract the verdict logic into a pure adjudicator"
```

---

## Task 2: Collection errors become a category, not a blanket

Spec §4.1, §4.2. Rows 9–12.

**Files:**
- Modify: `miner/adjudicate.py`
- Modify: `miner/tests/test_adjudicate.py`

**Interfaces:**
- Consumes: everything from Task 1.
- Produces: `adjudicate.import_block_kind(records, cleared) -> str` returning
  `"missing_symbol"`, `"warning_as_error"` or `"other"`.

**Two behaviours change.** Today any pass-1 collection error books `apparatus`
immediately. After this task: an oracle found despite collection errors wins
(row 9), and an oracle *not* found is categorised by whether the code patch
cleared the errors (rows 10–12).

- [ ] **Step 1: Write the failing tests**

Append to `miner/tests/test_adjudicate.py`:

```python
def test_an_oracle_found_despite_collect_errors_still_counts():
    """Row 9 beats rows 10-12. THE aa7705f7 CASE: it had 869 tests collected
    and 773 passing, and was discarded because 2 of its 4 touched files failed
    to import. A collection error matters only when it left us unable to
    conclude."""
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.FAILURE}, after={"t.py::a": outcomes.PASSED},
        before_records=recs, before_collect=["tests/other.py"], after_collect=[]))
    assert v.status == "pass1_ok"
    assert v.fields["before_collect_errors"] == ["tests/other.py"]


def test_collect_errors_cleared_by_the_patch_are_a_verdict():
    """Row 10. The fix supplies what the test could not import, so the failure
    is intrinsic to the commit -- not our environment."""
    recs = [outcomes.Record("tests/test_f.py", "collect", "failed",
                            "ImportError: cannot import name 'NewThing'")]
    v = adjudicate.adjudicate(_m(
        before={}, after={"t.py::a": outcomes.PASSED}, before_records=recs,
        before_collect=["tests/test_f.py"], after_collect=[]))
    assert v.status == "rejected:base_import_blocked"
    assert v.fields["import_block_kind"] == "missing_symbol"


def test_collect_errors_that_persist_are_ours():
    """Row 11. The patch did not touch it, so the cause lives outside the
    commit."""
    v = adjudicate.adjudicate(_m(
        before={}, after={"t.py::a": outcomes.PASSED},
        before_collect=["tests/test_f.py"], after_collect=["tests/test_f.py"]))
    assert v.status == "apparatus"


def test_new_collect_errors_after_the_patch_are_ours():
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.PASSED}, after={"t.py::a": outcomes.PASSED},
        before_collect=[], after_collect=["tests/test_f.py"]))
    assert v.status == "apparatus"
    assert "after" in v.reason


def test_no_f2p_and_no_collect_errors_is_still_unchanged():
    """Row 12. Unchanged must survive as a genuine verdict."""
    v = adjudicate.adjudicate(_m(
        before={"t.py::a": outcomes.PASSED}, after={"t.py::a": outcomes.PASSED}))
    assert v.status == "rejected:unchanged"


def test_import_block_kind_recognises_a_missing_symbol():
    recs = [outcomes.Record("tests/test_f.py", "collect", "failed",
                            "ImportError: cannot import name 'UnsupportedFieldAttributeWarning'")]
    assert adjudicate.import_block_kind(recs, ["tests/test_f.py"]) == "missing_symbol"


def test_import_block_kind_recognises_a_warning_promoted_to_error():
    """THE aa7705f7 MECHANISM: filterwarnings = ['error'], the parent still
    emits the warning at import, and the test patch removed the suppression."""
    recs = [outcomes.Record("tests/test_p.py", "collect", "failed",
                            "PydanticExperimentalWarning: This module is experimental")]
    assert adjudicate.import_block_kind(recs, ["tests/test_p.py"]) == "warning_as_error"


def test_import_block_kind_falls_back_to_other():
    recs = [outcomes.Record("tests/test_f.py", "collect", "failed", "something odd")]
    assert adjudicate.import_block_kind(recs, ["tests/test_f.py"]) == "other"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest miner/tests/test_adjudicate.py -v -k "collect or import_block"`
Expected: FAIL — `import_block_kind` does not exist, and the row-9/10 arms
currently book `apparatus`.

- [ ] **Step 3: Implement `import_block_kind`**

```python
# Warning classes promoted to errors by a project's filterwarnings config do
# not follow the Error/Exception naming convention -- pydantic's
# PydanticExperimentalWarning is the measured case -- so match on the suffix
# rather than on a name table.
def import_block_kind(records, cleared):
    """Why the base state could not import: missing_symbol | warning_as_error | other.

    Sub-label only. The class it describes, rejected:base_import_blocked, is
    already decided by the time this is called; getting the sub-label wrong
    misreports a statistic and never changes a verdict.
    """
    cleared = set(cleared)
    for rec in records:
        if rec.when != "collect" or rec.nodeid not in cleared:
            continue
        msg = rec.message or ""
        head = msg.split(":", 1)[0].rsplit(".", 1)[-1].strip()
        if head.endswith("Warning"):
            return "warning_as_error"
        if head in ("ImportError", "ModuleNotFoundError", "AttributeError",
                    "NameError"):
            return "missing_symbol"
    return "other"
```

- [ ] **Step 4: Reorder the arms in `adjudicate`**

Place the f2p check **above** the collection arms, and split the empty-f2p case
three ways:

```python
    # ROW 9 -- an oracle was found, so the collection errors cost us potential
    # EXTRA oracle tests, not the answer. This ordering is the aa7705f7 fix:
    # it had 869 tests collected and 773 passing and was thrown away because 2
    # of its 4 touched files failed to import. The previous phase's own
    # reviewer warned in the same review that over-correcting into apparatus
    # is a defect too, because apparatus is terminal.
    if not d["f2p"]:
        cleared = [p for p in m.before_collect if p not in set(m.after_collect)]
        if cleared:
            # ROW 10 -- the code patch fixed the import, so the block is
            # intrinsic to the commit. Excluded from the corpus per council
            # decision 2 (the assertions never ran against unfixed code) but
            # COUNTED, which is what finally gives missing_api a denominator.
            fields["import_block_kind"] = import_block_kind(
                m.before_records, cleared)
            return Verdict("rejected:base_import_blocked", ..., fields)
        if m.before_collect:
            # ROW 11 -- unchanged by the patch, so the cause is outside the commit
            return Verdict("apparatus", ..., fields)
        # ROW 12
        return Verdict("rejected:unchanged", ..., fields)
```

Add the new-errors-after check (row 11's second half) immediately after the
empty-`after` guard, before the diff is computed:

```python
    new_after = [p for p in m.after_collect if p not in set(m.before_collect)]
    if new_after:
        return Verdict("apparatus",
                       f"{len(new_after)} file(s) failed to collect after the "
                       f"code patch but not before, first {new_after[0]!r}; "
                       f"the two sides were not measured comparably", fields)
```

Record `before_collect_errors` and `after_collect_errors` into `fields` on every
path, so the evidence survives whatever the verdict is.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS, 111 tests.

- [ ] **Step 6: Commit**

```bash
git add miner/adjudicate.py miner/tests/test_adjudicate.py
git commit -m "feat(miner): categorise base-state import blocks instead of blaming ourselves"
```

---

## Task 3: A vanished test is not a failed test

Spec §4.3. Row 14.

**Files:**
- Modify: `miner/outcomes.py`
- Modify: `miner/adjudicate.py`
- Modify: `miner/tests/test_outcomes.py`
- Modify: `miner/tests/test_adjudicate.py`

**Interfaces:**
- Consumes: `outcomes.diff` from Task 1's interface list.
- Produces: `outcomes.diff` returns a **seventh** key, `vanished`. `broken` now
  holds only tests that ran and failed.

- [ ] **Step 1: Write the failing tests**

Append to `miner/tests/test_outcomes.py`:

```python
def test_diff_separates_a_vanished_test_from_a_failed_one():
    """`broken` means RAN AND FAILED. A test that is not there did not run, so
    it is not evidence of breakage -- it is evidence the id space moved."""
    before = {"t.py::failed": outcomes.PASSED, "t.py::gone": outcomes.PASSED}
    after = {"t.py::failed": outcomes.FAILURE}
    d = outcomes.diff(before, after)
    assert d["broken"] == ["t.py::failed"]
    assert d["vanished"] == ["t.py::gone"]


def test_diff_still_reconciles_a_renumbered_parametrisation():
    before = {"t.py::d[a.md:10-20]": outcomes.PASSED,
              "t.py::d[a.md:30-40]": outcomes.PASSED}
    after = {"t.py::d[a.md:8-18]": outcomes.PASSED,
             "t.py::d[a.md:28-38]": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["renamed"] == ["t.py::d[a.md:10-20]", "t.py::d[a.md:30-40]"]
    assert d["vanished"] == [] and d["broken"] == []


def test_an_unreconciled_disappearance_is_vanished_not_broken():
    """THE f7a9b735 / aa7705f7 CASE. Each edited markdown file deleted one code
    example along with 12 lines of prose, so the counts did not balance and the
    exact-swap rule could not reconcile. Before this change all of them booked
    `broken` and produced 'N previously-passing tests fail' -- with N failures
    that never happened."""
    before = {"t.py::d[a.md:10-20]": outcomes.PASSED,
              "t.py::d[a.md:30-40]": outcomes.PASSED}
    after = {"t.py::d[a.md:8-18]": outcomes.PASSED}
    d = outcomes.diff(before, after)
    assert d["broken"] == []
    assert sorted(d["vanished"]) == ["t.py::d[a.md:10-20]", "t.py::d[a.md:30-40]"]
```

Append to `miner/tests/test_adjudicate.py`:

```python
def test_vanished_tests_alone_do_not_book_a_regression():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"], before_records=recs,
        before={"t.py::a": outcomes.FAILURE, "t.py::gone": outcomes.PASSED},
        after={"t.py::a": outcomes.PASSED}))
    assert v.status == "validated"
    assert v.fields["vanished"] == ["t.py::gone"]


def test_a_test_that_ran_and_failed_still_books_a_regression():
    recs = [outcomes.Record("t.py::a", "call", "failed", "assert 1 == 2")]
    v = adjudicate.adjudicate(_m(
        pass2=True, pass1_f2p=["t.py::a"], before_records=recs,
        before={"t.py::a": outcomes.FAILURE, "t.py::keep": outcomes.PASSED},
        after={"t.py::a": outcomes.PASSED, "t.py::keep": outcomes.FAILURE}))
    assert v.status == "rejected:regression_broken"
    assert "1 previously-passing" in v.reason
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest miner/tests/ -v -k "vanished or unreconciled or ran_and_failed"`
Expected: FAIL — `KeyError: 'vanished'`.

- [ ] **Step 3: Split `broken` in `outcomes.diff`**

In the `was == PASSED` branch, route `now is None` that fails the exact-swap
rule to a new `vanished` list rather than to `broken`. `broken` keeps only
`now == FAILURE`. Return `vanished` as a seventh sorted key and document all
seven in the docstring, including why the split exists:

> A vanished id means the *reference patch* reshaped the id space, which is a
> property of the commit. It is not an agent deleting a test to go green — at
> mining time the tests are fixed, and the graded agent cannot touch them.

- [ ] **Step 4: Consume it in `adjudicate`**

Record `fields["vanished"] = d["vanished"]`. The regression arm tests
`d["broken"]` only. Reword its reason to give the failed count, and mention the
vanished count separately when non-zero so the record stays self-explaining.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS, 116 tests.

- [ ] **Step 6: Commit**

```bash
git add miner/outcomes.py miner/adjudicate.py miner/tests/
git commit -m "fix(miner): a vanished test is not a failed test"
```

---

## Task 4: Enumeration filters and the not_minable family

Spec §5.1, §5.2, §4.4.

**Files:**
- Modify: `miner/candidates.py`
- Create: `miner/tests/test_candidates.py`
- Modify: `miner/adjudicate.py`
- Modify: `miner/record.py`
- Modify: `miner/tests/test_adjudicate.py`

**Interfaces:**
- Produces:
  - `candidates.EXPECTED_PROJECT` — `{"pydantic": "pydantic"}`
  - `candidates.project_name(pyproject_text) -> str | None`
  - `candidates.exact_pins(pyproject_text) -> dict[str, str]`
  - `candidates.not_minable_reason(repo_name, parent_toml, commit_toml) -> str | None`
    returning `"foreign_project"`, `"straddles_dependency_bump"` or `None`

- [ ] **Step 1: Write the failing tests**

Create `miner/tests/test_candidates.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "screener"))

import candidates  # noqa: E402

PYDANTIC = "[project]\nname = 'pydantic'\ndependencies = [\n 'pydantic-core==2.37.2',\n]\n"
PYDANTIC_BUMPED = PYDANTIC.replace("2.37.2", "2.38.0")
CORE = "[project]\nname = 'pydantic_core'\n"


def test_project_name_reads_single_and_double_quotes():
    assert candidates.project_name(PYDANTIC) == "pydantic"
    assert candidates.project_name('[project]\nname = "pydantic"\n') == "pydantic"
    assert candidates.project_name(CORE) == "pydantic_core"


def test_project_name_is_none_when_absent():
    """pydantic v1 predates pyproject.toml. Absence is NOT foreignness."""
    assert candidates.project_name("") is None


def test_a_foreign_project_is_not_minable():
    """105 of 1,568 candidates are pydantic-core commits grafted into the
    pydantic clone. They can never run in a pydantic image."""
    assert candidates.not_minable_reason("pydantic", CORE, CORE) == "foreign_project"


def test_a_missing_pyproject_is_not_foreign():
    assert candidates.not_minable_reason("pydantic", "", "") is None


def test_exact_pins_ignores_ranges():
    text = "dependencies = [\n 'a==1.0',\n 'b>=2.0',\n 'c',\n]\n"
    assert candidates.exact_pins(text) == {"a": "1.0"}


def test_a_changed_exact_pin_straddles_a_dependency_bump():
    """Before needs 2.37.2 and after needs 2.38.0. No single quarter image can
    serve both, and the container runs --network none by design."""
    assert candidates.not_minable_reason(
        "pydantic", PYDANTIC, PYDANTIC_BUMPED) == "straddles_dependency_bump"


def test_an_unchanged_pin_is_minable():
    assert candidates.not_minable_reason("pydantic", PYDANTIC, PYDANTIC) is None


def test_a_changed_range_dependency_is_not_a_boundary():
    a = "dependencies = [\n 'b>=2.0',\n]\n"
    b = "dependencies = [\n 'b>=3.0',\n]\n"
    assert candidates.not_minable_reason("pydantic", a, b) is None


def test_an_unknown_repo_filters_nothing():
    assert candidates.not_minable_reason("somethingelse", CORE, CORE) is None
```

Append to `miner/tests/test_adjudicate.py`:

```python
def test_targets_filtered_by_our_config_are_not_minable():
    """Neither a verdict about the commit nor a claim our tooling broke: given
    our declared policy about what counts as a pytest test, this commit changed
    none. Reverses a decision twice -- see the spec's footnote to row 2."""
    v = adjudicate.adjudicate(_m(
        targets=adjudicate.TargetSelection([], adjudicate.EMPTY_FILTERED,
                                           "tests/mypy/x.py")))
    assert v.status == "not_minable:no_pytest_tests"
    assert "tests/mypy" in v.reason
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest miner/tests/test_candidates.py miner/tests/test_adjudicate.py -v`
Expected: FAIL — the `candidates` helpers do not exist.

- [ ] **Step 3: Implement the filters in `miner/candidates.py`**

```python
import re

# Explicit per-repo, never inferred. A heuristic that guessed wrong would
# silently drop real candidates, which is the failure class this whole phase
# exists to remove.
EXPECTED_PROJECT = {"pydantic": "pydantic"}

_NAME = re.compile(r"""^\s*name\s*=\s*['"]([^'"]+)['"]""", re.M)
_PIN = re.compile(r"""['"]([A-Za-z0-9._-]+)==([0-9][^'"]*)['"]""")


def project_name(pyproject_text):
    """The [project] name, or None when there is no pyproject.toml at all.

    None is NOT foreignness: pydantic v1 predates pyproject.toml entirely.
    """
    m = _NAME.search(pyproject_text or "")
    return m.group(1) if m else None


def exact_pins(pyproject_text):
    """{name: version} for `name==version` pins only.

    Ranges are excluded deliberately. A `>=` bound that moves does not force a
    different environment; an exact pin does.
    """
    return {n: v for n, v in _PIN.findall(pyproject_text or "")}


def not_minable_reason(repo_name, parent_toml, commit_toml):
    """Why this candidate is outside what the method can measure, or None."""
    expected = EXPECTED_PROJECT.get(repo_name)
    if expected:
        actual = project_name(commit_toml)
        if actual is not None and actual.replace("-", "_") != expected.replace("-", "_"):
            return "foreign_project"
    before, after = exact_pins(parent_toml), exact_pins(commit_toml)
    for name, version in after.items():
        if name in before and before[name] != version:
            return "straddles_dependency_bump"
    return None
```

Wire it into `enumerate_candidates`: read `pyproject.toml` at the parent and at
the commit with a single `git cat-file --batch` call for the whole candidate
list — 1,568 individual `git show` invocations is minutes of avoidable work —
and stamp `not_minable` onto the candidate record. The validator skips any
candidate carrying it and writes a record with
`status=f"not_minable:{reason}"`, so it is **counted, never silently dropped.**

- [ ] **Step 4: Route `EMPTY_FILTERED` and teach `record.is_done`**

In `adjudicate`, `EMPTY_FILTERED` books `not_minable:no_pytest_tests` with the
matched prefix in the reason. `EMPTY_NOT_RUNNABLE` and `EMPTY_ABSENT` stay
`apparatus`; `EMPTY_DELETED` stays `rejected:no_runnable_tests`.

In `miner/record.py`, add `not_minable:` to `is_done`'s terminal prefixes and
update the module docstring's status list.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS, 126 tests.

- [ ] **Step 6: Commit**

```bash
git add miner/candidates.py miner/adjudicate.py miner/record.py miner/tests/
git commit -m "feat(miner): foreign-project and dependency-boundary filters"
```

---

## Task 5: Report the new families and pin the denominators

Spec §4.4, §6.2.

**Files:**
- Modify: `miner/report.py`
- Modify: `miner/compare_rerun.py`

- [ ] **Step 1: Add a not_minable section and fix the denominators**

`report.py` builds markdown by appending to a list `out`; every section is a
`_name(out, ...)` function called from `render()`. Follow that convention.

Add `_not_minable(out, done)` listing the family with counts and the reason
detail, and state in prose that these never entered a container.

Then make the funnel's denominators explicit, because this codebase has already
carried two meanings of "adjudicated":

```
attempted    = entered a container
adjudicated  = attempted − apparatus − error
conversion   = validated / adjudicated
not_minable  = reported separately; never entered a container
```

Every printed rate must name its denominator inline. The apparatus tripwire
keeps its own `processed` denominator and says so.

- [ ] **Step 2: Verify the report renders against existing records**

```bash
python -c "import sys; sys.path.insert(0,'screener'); sys.path.insert(0,'miner'); import report; print(report.render()[:600])"
```

Expected: no exception. Pre-redesign records lack every new field, so this also
proves the guards hold.

- [ ] **Step 3: Run the tests**

Run: `python -m pytest miner/tests/ -v`
Expected: PASS, 126 tests.

- [ ] **Step 4: Commit**

```bash
git add miner/report.py miner/compare_rerun.py
git commit -m "feat(miner): report the not_minable family and pin the rate denominators"
```

---

## Task 6: Stage 1 — the 2025Q3 known-answer run

Spec §6.1.

**Files:**
- Create: `docs/miner/2026-08-12-sweep-predictions.md`
- Modify: `docs/miner/2026-08-12-sweep-predictions.md` (results appended after the run)

- [ ] **Step 1: Commit the predictions BEFORE running anything**

Create `docs/miner/2026-08-12-sweep-predictions.md` with the table below, then
commit it. **This must be committed before the run.** In the previous phase the
predictions were partly wrong and that was only noticed afterwards, which makes
them a story rather than a test.

| candidate | predicted |
|---|---|
| `71a02fcf` `e28f7544` `eb2c860a` `a59dab90` `27aaf685` `8a62354c` `9c5eb6e5` | `validated`, same oracles as today |
| `aa7705f7` | `validated` — row 9 now beats the collection check |
| `f7a9b735` | `validated` — its `broken` set was 7 vanished and 0 failed |
| `3a7fe26a` | `rejected:base_import_blocked` / `missing_symbol` |
| `eea593b0` `0801aebc` | `not_minable:foreign_project` |
| `7c40924a` `ac4f3ccb` | `not_minable:straddles_dependency_bump` |
| `9b438b49` `dac3c437` `568509c0` | `not_minable:no_pytest_tests` |
| `4406b2be` `b0175de4` `4057cd2b` | `rejected:unchanged` |
| `ba91a3c9` | uncertain — its collect error is `tests/test_types.py`; `base_import_blocked` if the patch clears it, `apparatus` if not |

```bash
git add docs/miner/2026-08-12-sweep-predictions.md
git commit -m "docs(miner): commit sweep predictions before the run"
```

- [ ] **Step 2: Re-enumerate, so the new filters apply**

```bash
python miner/mine.py enumerate
```

Expected: the candidate file gains `not_minable` stamps. Report how many
candidates carry each reason across all 1,568.

- [ ] **Step 3: Run 2025Q3**

```bash
python miner/mine.py validate --quarter 2025Q3 --limit 21 --force
```

- [ ] **Step 4: Compare against the predictions**

```bash
python miner/compare_rerun.py
```

Append the actual results to `docs/miner/2026-08-12-sweep-predictions.md`, row by
row, marking each hit or miss. **A divergence is a finding to diagnose and write
down, not a number to adjust.** If apparatus is still above 10%, say so plainly
and diagnose each remaining case before Task 7.

- [ ] **Step 5: Commit**

```bash
git add docs/miner/2026-08-12-sweep-predictions.md miner/out/
git commit -m "test(miner): 2025Q3 known-answer run against committed predictions"
```

---

## Task 7: Stages 2 and 3 — the v2-era sweep

Spec §6.

**Files:**
- Create: `docs/miner/2026-08-12-v2-sweep.md`

- [ ] **Step 1: Stage 2 — four quarters**

```bash
for q in 2025Q4 2026Q1 2026Q2 2026Q3; do python miner/mine.py validate --quarter $q; done
```

Then render the funnel and **stop**. Report to the human partner: validated
count, apparatus rate with its denominator, the `not_minable` breakdown, the
label composition, and wall-clock per candidate. Do not start stage 3 until they
have seen it.

- [ ] **Step 2: Stage 3 — the remaining eight quarters**

```bash
for q in 2023Q3 2023Q4 2024Q1 2024Q2 2024Q3 2024Q4 2025Q1 2025Q2; do python miner/mine.py validate --quarter $q; done
```

- [ ] **Step 3: Write up the sweep**

Create `docs/miner/2026-08-12-v2-sweep.md` reporting, with denominators named:

- **conversion rate** = validated / adjudicated, and the raw counts
- **cost per candidate**: wall-clock and container time
- **corpus composition** by failure label
- **`not_minable` breakdown** and what fraction of history it removes
- **`rejected:base_import_blocked` count** — the first real denominator for
  `missing_api`, and the number that decides whether the §5.4 probe is worth
  building
- whether apparatus is under the 10% tripwire, and every remaining case's cause

State plainly whether there are enough validated capsules for the model-tier
experiment (~30 needed), and whether `CONVERSION_RATE` can now be recalibrated.

- [ ] **Step 4: Commit**

```bash
git add docs/miner/2026-08-12-v2-sweep.md miner/out/
git commit -m "test(miner): v2-era sweep across 13 quarters"
```

---

## Self-Review Notes

**Spec coverage.** §3 → Task 1. §4.1/§4.2 (rows 9–12) → Task 2. §4.3 (row 14) →
Task 3. §4.4 vocabulary → Tasks 4 and 5. §5.1/§5.2 → Task 4. §5.3 already built.
§5.4 explicitly deferred, no task. §6.1 → Task 6. §6.2 → Tasks 5 and 7. §7 →
tests inside every task. §8 success criteria → Task 7 Step 3.

**Type consistency.** `Measurements` fields are identical everywhere they appear:
`pass2`, `targets`, `before`, `after`, `before_records`, `before_collect`,
`after_collect`, `pass1_f2p`. `Verdict` is `(status, reason, fields)` throughout.
`outcomes.diff` returns six keys after Task 1 and seven after Task 3 — the extra
key is `vanished`, consumed only in Task 3 and later.

**Test counts** assume 90 existing: 103 after Task 1, 111 after Task 2, 116 after
Task 3, 126 after Task 4. Treat these as expectations to check, not targets — if
a count differs, find out why before proceeding.

**Ordering risk, stated because it is the whole point.** Task 1 must not change
behaviour and Task 2 must reorder deliberately. If Task 1's reviewer sees any
verdict change, that is a defect, not an improvement delivered early.
