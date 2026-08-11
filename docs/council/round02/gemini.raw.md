POSITION:
Failure kind must **label, not gate** corpus admission, subject to one hard execution boundary: JUnit XML `<failure>` versus `<error>`. Round 1’s rule was designed to prevent feature-work pollution (`missing_api`), but real-world execution against `pydantic` yielded zero `missing_api` rejections while string-matching regexes incorrectly discarded 50% of valid test failures. When a test transitions from fail to pass strictly across an authentic reference patch, validity and solvability are established by execution. Rejecting tasks based on exception taxonomy bakes subjective filters into the dataset and destroys yield; labelling preserves maximum experimental control without data loss.

Q1: **Label only**, using a single binary execution boundary: **JUnit XML `<failure>` (admit) versus `<error>` (reject)**. String-matching exception names caused a 50% false-rejection rate to solve a problem (`missing_api` pollution) that empirically measured 0%. A test that executes, fails under harness assertion, and passes when the upstream commit is applied is a valid capsule. Store failure taxonomy (`AssertionError`, `pytest.raises`, `AttributeError`, `ValidationError`) strictly as metadata tags so downstream consumers can filter cohorts as needed.

Q2: **Minimum evidence requires three criteria:**
1. **Invocation integrity:** Pre-fix execution yields JUnit XML `<failure>` (confirming the test body executed and an expectation failed), not `<error>` (collection/import failure).
2. **Causal execution transition:** The exact test set transitions from fail to pass ($Fail \rightarrow Pass$) upon applying the reference fix patch.
3. **Identity stability:** Test identity is verified via AST `nodeid` (e.g., `test_mod.py::test_func[param]`), insulating the miner against line-number shifts.

Fail-to-pass against the reference patch proves task solvability and causal attribution. It does not prove high oracle precision (e.g., preventing weak assertions), but exception name parsing does not measure oracle precision either—an `AssertionError` can be just as weak as an unhandled exception.

Q3: **Yes, unequivocally.** In pytest, `pytest.fail()`, `pytest.raises` failure ("DID NOT RAISE"), and `pytest.warns` failure ("DID NOT WARN") throw `Failed` exceptions, which standard JUnit XML loggers serialize natively as `<failure>`. They represent harness-level expectation breaches, distinct from uncaught setup or syntax crashes (`<error>`). All `Failed:` protocol outputs belong to the assertion class.

Q4: **Include all admitted capsules (both bug fixes and feature additions), while reporting cohort breakdowns.** The primary metric is cost per solved task across model tiers. With 30 tasks yielding a minimum detectable effect of ~12.5 points, dropping valid tasks via taxonomy gating severely degrades statistical power. Models should be evaluated across the full distribution of real-world tasks, with cost-efficiency curves reported both in aggregate and stratified by failure label.

Q5: **Amended in two places:**
1. **Parsing & Tracking Contract:** Replace terminal summary name-matching with JUnit XML parsing (`<failure>` vs `<error>`), and replace line-number matching with AST `nodeid` tracking.
2. **Alternate Implementation Gate:** Drop mandatory authored alternate implementations prior to capsule admission. Requiring upfront alternate patches creates an unsustainable human bottleneck. Replace it with post-hoc alternate-patch validation on a sampled audit (e.g., 10% of admitted capsules).

STRONGEST OBJECTION TO MY OWN POSITION:
Execution-only fail-to-pass could admit **brittle or coincidental oracles**. A test might fail pre-fix due to an unhandled side effect or state pollution, and pass post-fix simply because the reference patch incidentally resets global state or changes execution order, rather than satisfying the core underlying task logic. Exception-class filtering acted as a coarse defense against these non-causal state transitions.

WHAT WOULD CHANGE MY MIND:
A blind audit showing that >10% of capsules admitted under the pure `<failure>` execution contract can be solved by a "null patch" (e.g., `pass` or returning default values) or an unrelated baseline edit, indicating that the fail-to-pass transition is uncoupled from true task satisfaction.

CONFIDENCE:
High. The empirical data invalidated Round 1's core risk assumption (0 missing API rejections) while demonstrating massive, unnecessary task loss (50%) from exception-name gating.
