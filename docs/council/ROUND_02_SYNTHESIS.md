# Council round 2 — synthesis

**Motion:** `docs/council/ROUND_02_MOTION.md`
**Raw responses:** `docs/council/round02/`
**Seats:** Gemini 3.6 Flash (high), GPT‑5.6 Luna (xhigh), GPT‑5.6 Sol (xhigh),
DeepSeek V4 Flash (xhigh), Kimi K3 (xhigh), GLM 5.2 (xhigh), Qwen3.8 Max (high).
**Chair:** Opus 5.

Qwen exhausted its budget mid-deliberation on the first attempt and was re-run
with an explicit brevity constraint at `high`. The retry overwrote the first
transcript; excerpts captured before that are in
`round02/qwen.first-attempt.md`, flagged there as partial. They contain the
sharpest statement of the `<error>`-base hazard and are cited below.

---

## The vote

**7–0: label, do not reject.** No member defended taxonomy as an admission gate.
No member argued round 1 was right on the evidence now available.

**7–0: `Failed:` is assertion-class.** `pytest.raises` not raising, `pytest.warns`
not warning, and `pytest.fail()` are pytest's own report that a declared
expectation was not met. Unqualified agreement, no dissent, no caveats.

**7–0: stop reading exception names.** Every member independently reached the
same replacement: parse JUnit XML and classify on the element, not the string.

The unanimity is not the interesting part. The council converged on a
*different* gate than the one we had, and on three requirements round 1 never
contained.

---

## What replaces the rule

Round 1 said: *the base negative must fail for the right reason, and only an
assertion failure qualifies.*

The council's replacement: **gate on execution integrity, label everything else.**

A capsule is admitted when:

1. The base run records a JUnit `<failure>` for the target test — it ran, and an
   expectation was not met. Any exception name qualifies.
2. The after run records a pass for the *same logical test*.
3. Neither run is contaminated by a collection error elsewhere in the session.
4. The transition reproduces on an independent paired rerun.

A capsule is **not** admitted when the base records `<error>` — the test could
not run at all.

Everything else — `AssertionError`, `Failed: DID NOT RAISE`,
`PydanticDeprecatedSince20`, `ValidationError`, `AttributeError`,
`ModuleNotFoundError` — is admitted and **labelled**.

### The nuance that dissolves most of round 1's concern

Sol drew a distinction the rest of the council assumed without stating: an
`AttributeError` or `ImportError` **raised inside an executed test body** is a
`<failure>`, not an `<error>`. Only collection- and setup-phase errors are
`<error>`.

This matters more than it looks. Round 1's `missing_api` rejection class was
aimed at tests that touch an API that does not exist yet — and those tests
usually raise *during the call phase*. Under the new rule they are admitted
automatically and labelled `missing_api`. The rejection class does not need to
be argued away; the correct parser never produces it as a rejection.

### Why `<error>` still gates

Three members gave the same reason independently, and it is the one place where
execution evidence genuinely runs out.

GLM: with an `<error>` base, "fail-to-pass may reflect import wiring pulled in
by the patch rather than the intended behaviour."

Qwen's first transcript put the mechanism concretely: a commit fixes a subtle
bug in `Y` *and* adds a test-file import of a new helper. The base cannot
collect. The after run passes. The fail-to-pass signal is driven by the helper
existing — and the test's assertions never executed against the broken `Y`, so
we have no evidence at all that they detect it.

With a `<failure>` base we know the test ran against the broken code and caught
something. With an `<error>` base we know only that it could not run. That is a
real difference in evidence, not a taxonomy preference.

---

## Three requirements round 1 did not have

These were volunteered, unprompted, by multiple members. None is in the current
design.

**Determinism.** Kimi: run both phases twice; identical verdicts all four times.
Luna: one independent paired rerun in fresh subprocesses. Sol: rerun the
transition, or apply-then-revert the code patch and confirm it flips back.

Kimi's framing is the one that convinced me: *flakiness, not taxonomy, is the
plausible mechanism by which a test "passes for unrelated reasons."* The
counter-argument that motivated keeping a taxonomy gate is better answered by
two extra runs than by a name table.

Cost is negligible. The rerun applies only to candidates that already produced a
clean fail-to-pass — one in eleven adjudicated so far — not to every candidate.

**Isolation.** One collection error currently aborts the whole session and
zeroes unrelated tests. Kimi, Luna and Sol all flag this as a live corruption
source, and Sol names it as an admission condition: no unrelated collection
failure may explain the transition. Remedy: `--continue-on-collection-errors`
with explicit error accounting, and session scoping to the touched test files.

**Stable test identity.** Five members raise it; it is the direct fix for the
defect that fabricated three `regression_broken` verdicts. Sol's formulation is
the operational one: **a node-ID change is a rename requiring reconciliation,
never automatic regression breakage.**

---

## The experiment

7–0: include every admitted capsule, report the composition, pre-register a
pooled primary analysis and a bug-fix-only sensitivity analysis. At MDE ≈ 12.5
points on 30 tasks, discarding validated capsules on an uncalibrated taxonomy is
— Qwen's phrase — statistical self-harm.

GLM contributed the one point no other member reached, and it is a real
confound-detector: **audit the failure-kind distribution *by tier*, not just
rejection counts.** If a cheap tier disproportionately solves one label's
stratum — say, `DID NOT RAISE` tests satisfiable by raising the right exception
anywhere — aggregate cost-per-solved hides it and per-label reporting exposes
it. Adopted.

---

## Round 1 amendments

**Alternate implementation — de-universalised, 6–1.** Gemini (10% post-hoc),
Sol (stratified sample), Kimi (~20% plus audit-flagged), DeepSeek (contingent on
the audit showing need), Qwen (scope to capsules actually used), GLM (narrowed).
At 9.1% conversion, a universal authored alternate gates the pipeline on the
scarcest resource in the project.

**Luna dissented** and the dissent improves the outcome. Luna wants the
alternate kept as *predeclared coverage across failure labels* rather than
conditional on observed rejections — because a sample that never touches a label
cannot tell you that label is safe. The resolution takes both: **sample the
alternate implementation, but stratify the sample by failure label rather than
drawing it at random.** That buys Luna's coverage guarantee at the majority's
cost.

**Unchanged from round 1:** mutation survival stays a reported diagnostic and
never a gate. No LLM judge decides solved/unsolved. Both reaffirmed by every
member who addressed them.

**Adopted from Kimi, operational:** if apparatus-class outcomes exceed ~10% of a
batch, stop mining and fix tooling before spending more corpus budget. This
batch ran at 48% apparatus.

**Declined:** Qwen's static check that a test body must contain at least one
assertion or explicit expectation. It is cheap, but it is a fourth mechanism
doing what the `<failure>` element already does, and it would misfire on tests
whose expectation is expressed through a fixture or helper.

---

## The reservation the chair is recording rather than resolving

Kimi and GLM held at **medium** confidence while five members held high. Their
shared objection is correct and should not be smoothed over.

Zero `missing_api` rejections in 21 candidates does **not** establish that
feature work is rare. Kimi did the arithmetic: zero observed in 21 is consistent
with a true rate near 14%. We are removing the gate because it is *miscalibrated
and expensive*, not because we have shown the thing it guarded against does not
exist.

Kimi's sharper objection deserves a concrete answer rather than agreement:

> labels only protect the corpus if someone acts on them, and a solo founder may
> never run the stratified audit, in which case "label" degenerates to "admit
> everything".

**Answer: make composition a mandatory output, not an optional analysis.** The
funnel report prints the label mix on every run. A founder who never opens an
analysis notebook still cannot avoid seeing it. This is a build requirement, not
an intention.

---

## One number that changes

Of ten rejections, seven were our defects. Removing them leaves **1 validated
against 3 genuinely rejected**.

The 9.1% conversion figure was computed against a denominator that was 64%
tooling failure. The corrected figure is nearer 25% — on n=4, which is not an
estimate so much as a statement that we do not yet know the conversion rate at
all. `CONVERSION_RATE` should not be recalibrated until the re-run.

---

## Decisions carried into the build

| # | Decision | Vote |
|---|---|---|
| 1 | Failure kind labels; it does not gate | 7–0 |
| 2 | Gate on JUnit `<failure>` vs `<error>`; base `<error>` disqualifies | 7–0 |
| 3 | Exception raised in the call phase is `<failure>`, whatever its name | Sol, uncontested |
| 4 | `Failed:` protocol is assertion-class | 7–0 |
| 5 | Replace summary parsing with JUnit XML | 7–0 |
| 6 | Node-ID change is a rename to reconcile, never a regression | 5 members |
| 7 | One paired rerun; the transition must reproduce | 3 members, adopted |
| 8 | `--continue-on-collection-errors` + session scoping | 3 members, adopted |
| 9 | Pooled primary analysis, bug-fix-only sensitivity | 7–0 |
| 10 | Report failure-kind distribution per tier | GLM, adopted |
| 11 | Alternate implementation sampled, stratified by label | 6–1, dissent folded in |
| 12 | Composition printed by the funnel report, mandatory | Chair, answering Kimi |
| 13 | Halt mining if apparatus exceeds 10% of a batch | Kimi, adopted |
| 14 | Mutation survival diagnostic only; no LLM judge | unchanged |
