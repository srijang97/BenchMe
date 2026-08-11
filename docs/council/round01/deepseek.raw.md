OpenAI Codex v0.144.2
--------
workdir: C:\Users\Srijan\Documents\BenchMe
model: opencode-go/deepseek-v4-flash
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fee15-5208-7683-bd5c-5fe130068066
--------
user
# Council round 1 — the oracle contract

You are one member of a seven-member council advising a solo technical founder.
Other members are different frontier models from different labs. Your answer
will be cross-critiqued by them and synthesised by a chair. Disagreement is
useful; do not hedge toward a middle position to seem agreeable.

---

## 1. What the project is

**BenchMe** is being built as *verification/CI for AI coding agents* — not a
benchmark company. The product is a private, execution-verified regression
suite that runs inside a customer's own CI and gates changes to their agent
stack the way unit tests gate changes to code.

The scored unit is never "a model". It is the whole configuration:

```
f(task, repo state, model, harness, prompt, context, tools,
  permissions, budget, environment, verifier, trial)
```

A **capsule** is one self-contained evaluation task: a repository pinned to a
base commit, a task statement, a hidden verifier, controls, an environment
reference, and an information policy.

## 2. The immediate context

The first corpus repository has just been selected by measurement: **pydantic**,
projected to yield about 35 capsules. The next step is to mine capsules from it.

The first experiment this corpus must support is a **model-tier comparison**:
one harness held fixed (Codex CLI), several model tiers varied (frontier vs
mid vs cheap open-weight), measuring **cost per solved task** — not pass rate.
The commercial thesis being tested is that cheap models can cost *more* per
solved task because they fail more often and burn tokens failing.

Constraints already fixed and not up for debate in this round:

- **Execution is primary for correctness.** Grading is by running code.
- **No composite score.** Metrics are reported separately, never blended.
- **k ≥ 5 trials** per cell. At 30 tasks × k=5 the minimum detectable effect is
  about 12.5 percentage points, so only large effects are observable.
- Corrections create a new capsule version; nothing is edited in place.
- The corpus will be mostly **pre-training-cutoff** — the fresh, contamination-
  resistant stream measured at under one capsule per repository.

## 3. The facts that bear on this decision

All figures are from published work; sources in the companion facts document.

**Test suites mined from history are usually too weak.** Mutation testing of
SWE-bench Verified found **77.0% of instances (385/500) accept at least one
wrong patch that still passes**. Re-scoring ten leading agents against
strengthened suites dropped resolve rates by **4.2–9.0 points**.

**They are simultaneously often too strict.** An audit found **≥59.4% of
examined problems have flawed tests** — 35.5% enforcing implementation details
the task never specified, so functionally correct answers are marked wrong.

**These two pull in opposite directions and no published method satisfies
both.** Hardening tests to kill mutants makes them stricter, which increases
false rejection of valid alternatives.

**Different-but-correct is common.** Differential testing found **7.8% of
patches marked correct fail the full developer suite**, and of patches that
diverged behaviourally from the reference, **46.8% were legitimate alternative
implementations**.

**The strongest published oracle design is implementation-agnostic.**
Hand-written verifiers that accept *any* implementation of the requested
behaviour achieved **1.4% disagreement with independent evaluators, versus
32.4%** for a comparable benchmark.

**Mutation score may not be valid for this use.** A 2026 replicability study
finds coverage and mutation scores give reliable signal in the *regression*
setting — where code is assumed correct — but are **not reliable when the goal
is exposing defects in buggy code**. Capsule hardening sits between those cases.

**The "never use an LLM judge" rule has a documented counter-example.** One
study comparing reward-hack detectors found held-out unit tests gave only
*minimal* improvement over alternatives, while an LLM judge was highly
effective on unambiguous cases. Against this, Databricks' published practice
refuses the LLM judge for correctness because it "rewards sounding right over
being right".

**Harnesses can be gamed.** Red-teaming ten benchmark harnesses achieved
near-perfect scores on nine **without solving a single task**, via 219 flaws in
8 classes.

**Repairing a benchmark moves scores more than upgrading a model**: patching 28
of 89 tasks moved an identical agent+model pairing by **+12.1 points**.

## 4. The existing draft schema

A capsule schema already exists (`benchme.task_capsule.v0.1`). Its oracle block
records an assurance level on a 5-rung ladder (O0–O4), the target tests, the
regression command, static checks, and a requirement→test map. It defines six
controls, of which the last two are currently **optional and marked "not run"**:

1. base negative — target fails before the fix
2. reference positive — a known-good patch passes
3. regression — unrelated behaviour still passes
4. no-op / near-miss — superficial compliance is rejected
5. **alternate-solution — a different correct implementation also passes** *(optional)*
6. **adversarial verifier probe — attempts to game the grader fail** *(optional)*

## 5. What the council must decide

Answer these five questions directly.

**Q1. What is the minimum oracle a capsule must have to enter a decision-grade
run?** Name the specific required components. Be concrete about what is
mandatory versus nice-to-have.

**Q2. How is the strict-versus-weak tension resolved in practice?** Given
hardening increases false rejection and not hardening admits wrong patches,
what is the actual operating procedure? If your answer is "run the
alternate-solution control", say how many alternates, who writes them, and what
happens when an alternate fails.

**Q3. Should mutation survival be a gate, a reported number, or dropped?**
Given the replicability study casts doubt on its validity for this exact use,
and given a prior recommendation set a "≥20% of tasks survive hardening" gate.

**Q4. Does an LLM judge have any role in the oracle, and if so exactly where?**
The project's current doctrine says execution-primary and judge-only for what
execution cannot see (scope, compatibility, maintainability, is-this-a-hack).
Defend, narrow, or reject that position.

**Q5. Does the model-tier axis change any of the above?** Specifically: if
different model tiers produce systematically different *implementation styles*,
does an implementation-sensitive oracle measure style rather than capability —
and what follows?

## 6. Required output format

Keep the whole response under 900 words. Be specific and decisive.

```
POSITION: one paragraph stating your overall stance.

Q1: <answer>
Q2: <answer>
Q3: <answer>
Q4: <answer>
Q5: <answer>

STRONGEST OBJECTION TO MY OWN POSITION: <the best argument against you>

WHAT WOULD CHANGE MY MIND: <specific evidence or measurement>

CONFIDENCE: high | medium | low, with one line of reasoning.
```

codex
POSITION: BenchMe’s oracle should be an implementation-agnostic behavioral verifier validated from both directions, not a maximally hardened suite. A capsule may enter a decision-grade run only when it has a base negative, a reference positive, at least two independent alternate positives, a no-op rejection, a regression check, and a requirement-to-test map. Mutation survival and adversarial probes are diagnostics or iterative hardening, not entry gates. This is expensive, but BenchMe is a grading instrument; false labels invalidate every downstream comparison.

Q1: Mandatory: base negative (target fails before fix), reference positive (known-good patch passes), at least two alternate positives written blind to the reference implementation, a no-op or near-miss rejection, a regression command covering adjacent unchanged behavior, a reviewed requirement-to-test map, and pinned environment/budget/trial reproducibility. Nice-to-have: static checks, adversarial verifier probes, mutation survival, independent second review, and judge-generated candidate tests. The adversarial probe should become mandatory after the first gaming incident or on high-risk capsules, but it cannot be an entry gate because probing is open-ended and can always be extended.

Q2: Run the alternate-solution control, and treat the oracle as two-sided validation. Base negative plus no-op rejects known wrong patches; reference plus alternates prevents over-strictness. Minimum: two alternates per capsule for a decision-grade model-tier run. They must be written by people or models different from the verifier and reference authors, blind to the reference patch, and at least one should deliberately use a cheap-model-style implementation rather than the reference style. Hardening consists of rewriting tests to assert observable behavior, never implementation details. When an alternate fails, triage: if it satisfies the task statement, the verifier is too strict, so fix the verifier and rerun the full reference-plus-alternate set; if it violates a real requirement, reject that alternate and source another; if the task statement is ambiguous, create a new capsule version. Never weaken tests merely to accept an alternate, and never drop a failing alternate silently.

Q3: Mutation survival is a reported number, not a gate. Drop the “≥20% of tasks survive hardening” threshold. The replicability study is directly on point: mutation signal is validated in regression settings, not for exposing defects in buggy code, and capsule hardening sits between those cases. Report survival per capsule and as a corpus aggregate, use it to find verifiers worth inspecting, but decide entry eligibility on the functional controls in Q1 and Q2.

Q4: Narrow the judge role. A judge may generate candidate tests and alternates, flag execution-passing patches for manual review, classify scope, compatibility, and maintainability, and produce non-blocking auxiliary metrics. It cannot decide pass/fail, cannot override execution, and its flags must always land in a human review queue. The Databricks objection is decisive for correctness: judges reward plausible soundness. The documented counter-example supports triage, not verdicts.

Q5: Yes, the model-tier axis changes the requirements. For any capsule used in tier comparisons, the alternates must span implementation styles, and any verifier that rejects a valid style makes that capsule invalid for the comparison. Add a per-capsule style-sensitivity audit and report per-task failure reason codes so style-driven failures are visible rather than absorbed into cost per solved task. Residual sensitivity would bias cheap models upward, which is exactly the direction of the commercial thesis, so it is a self-confirmation risk. Treat style-correlated oracle failures as a confound, never as model capability.

STRONGEST OBJECTION TO MY OWN POSITION: My answer treats over-strictness as the problem to engineer around, while the evidence says false acceptance is the larger failure. Alternates and a single no-op check do not catch the wrong-patch class that passes 77% of mined suites, and demoting mutation survival to a report removes the only existing quantitative guard without replacing it with a measured false-accept control.

WHAT WOULD CHANGE MY MIND: Per-capsule validation sets containing known-wrong patches (mutants plus real failed patches) and style-diverse correct patches, measured to show the full oracle holds false-accept and false-reject rates below roughly 2% each across the corpus. Also useful: evidence that mutation score predicts false acceptance on buggy-patch populations, or a controlled fresh-task comparison showing judge-only grading has lower net error than execution-based grading.

CONFIDENCE: medium. The direction is defensible, but mandatory alternates and mutation-as-report are policy choices unvalidated for this exact setting, so they need measurement before scale-up.
tokens used
956
POSITION: BenchMe’s oracle should be an implementation-agnostic behavioral verifier validated from both directions, not a maximally hardened suite. A capsule may enter a decision-grade run only when it has a base negative, a reference positive, at least two independent alternate positives, a no-op rejection, a regression check, and a requirement-to-test map. Mutation survival and adversarial probes are diagnostics or iterative hardening, not entry gates. This is expensive, but BenchMe is a grading instrument; false labels invalidate every downstream comparison.

Q1: Mandatory: base negative (target fails before fix), reference positive (known-good patch passes), at least two alternate positives written blind to the reference implementation, a no-op or near-miss rejection, a regression command covering adjacent unchanged behavior, a reviewed requirement-to-test map, and pinned environment/budget/trial reproducibility. Nice-to-have: static checks, adversarial verifier probes, mutation survival, independent second review, and judge-generated candidate tests. The adversarial probe should become mandatory after the first gaming incident or on high-risk capsules, but it cannot be an entry gate because probing is open-ended and can always be extended.

Q2: Run the alternate-solution control, and treat the oracle as two-sided validation. Base negative plus no-op rejects known wrong patches; reference plus alternates prevents over-strictness. Minimum: two alternates per capsule for a decision-grade model-tier run. They must be written by people or models different from the verifier and reference authors, blind to the reference patch, and at least one should deliberately use a cheap-model-style implementation rather than the reference style. Hardening consists of rewriting tests to assert observable behavior, never implementation details. When an alternate fails, triage: if it satisfies the task statement, the verifier is too strict, so fix the verifier and rerun the full reference-plus-alternate set; if it violates a real requirement, reject that alternate and source another; if the task statement is ambiguous, create a new capsule version. Never weaken tests merely to accept an alternate, and never drop a failing alternate silently.

Q3: Mutation survival is a reported number, not a gate. Drop the “≥20% of tasks survive hardening” threshold. The replicability study is directly on point: mutation signal is validated in regression settings, not for exposing defects in buggy code, and capsule hardening sits between those cases. Report survival per capsule and as a corpus aggregate, use it to find verifiers worth inspecting, but decide entry eligibility on the functional controls in Q1 and Q2.

Q4: Narrow the judge role. A judge may generate candidate tests and alternates, flag execution-passing patches for manual review, classify scope, compatibility, and maintainability, and produce non-blocking auxiliary metrics. It cannot decide pass/fail, cannot override execution, and its flags must always land in a human review queue. The Databricks objection is decisive for correctness: judges reward plausible soundness. The documented counter-example supports triage, not verdicts.

Q5: Yes, the model-tier axis changes the requirements. For any capsule used in tier comparisons, the alternates must span implementation styles, and any verifier that rejects a valid style makes that capsule invalid for the comparison. Add a per-capsule style-sensitivity audit and report per-task failure reason codes so style-driven failures are visible rather than absorbed into cost per solved task. Residual sensitivity would bias cheap models upward, which is exactly the direction of the commercial thesis, so it is a self-confirmation risk. Treat style-correlated oracle failures as a confound, never as model capability.

STRONGEST OBJECTION TO MY OWN POSITION: My answer treats over-strictness as the problem to engineer around, while the evidence says false acceptance is the larger failure. Alternates and a single no-op check do not catch the wrong-patch class that passes 77% of mined suites, and demoting mutation survival to a report removes the only existing quantitative guard without replacing it with a measured false-accept control.

WHAT WOULD CHANGE MY MIND: Per-capsule validation sets containing known-wrong patches (mutants plus real failed patches) and style-diverse correct patches, measured to show the full oracle holds false-accept and false-reject rates below roughly 2% each across the corpus. Also useful: evidence that mutation score predicts false acceptance on buggy-patch populations, or a controlled fresh-task comparison showing judge-only grading has lower net error than execution-based grading.

CONFIDENCE: medium. The direction is defensible, but mandatory alternates and mutation-as-report are policy choices unvalidated for this exact setting, so they need measurement before scale-up.
