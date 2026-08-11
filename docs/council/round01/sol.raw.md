OpenAI Codex v0.144.2
--------
workdir: C:\Users\Srijan\Documents\BenchMe
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fee24-9bf9-7322-882d-cfb6fd9c99d5
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
POSITION: A decision-grade capsule needs a behaviourally specified, implementation-agnostic executable oracle with positive, negative, alternative-implementation, regression, and anti-gaming evidence. Test count, coverage, and mutation score are diagnostics—not proof. Any ambiguity should lead to quarantine, not a forced pass/fail, because oracle error can easily exceed the model-tier effect being measured.

Q1: Mandatory components:

- A pinned, reproducible environment and base commit.
- An explicit behavioural contract: requirements, permitted interfaces, compatibility expectations, and out-of-scope behaviour.
- A requirement→test map covering every claimed requirement.
- Hidden target tests that fail on the base state for the intended reason.
- A known-good reference patch that passes target and regression tests.
- Relevant upstream regression tests, plus deterministic static checks only where the task explicitly requires structural constraints.
- At least one credible near-miss per substantive requirement, demonstrating rejection of superficial or incomplete fixes.
- Two structurally distinct correct implementations that both pass.
- At least one task-specific adversarial probe covering likely grader attacks: test deletion, test/config bypass, hard-coded outputs, dependency/environment manipulation, or equivalent.
- A manual oracle review confirming that assertions test observable requirements rather than reference-patch details.

Thus controls 1–6 should all be mandatory for decision-grade runs. More mutants, fuzzing, property tests, platform variants, and additional alternates are valuable but not universal entry requirements. A capsule that cannot meet the minimum remains exploratory and must not influence purchasing or tier-selection decisions.

Q2: Use a contract-first, bidirectional challenge procedure.

First, write the behavioural contract independently of the reference diff. Then build tests from the contract. Challenge weakness with near-misses, real historical mistakes, generated candidate patches, fuzzing, and mutants. Challenge strictness with two meaningfully different correct solutions: one written by the capsule author and one independently written or reviewed by another competent engineer. LLMs may propose either, but a human must inspect and endorse their correctness without relying on the verifier result.

“Different” must mean a different algorithm, control flow, abstraction, or integration strategy—not renamed or reformatted reference code. For unusually constrained tasks, the reviewer may document why only one implementation family is plausible, but that exception should trigger additional property or differential testing.

If a valid alternate fails, the capsule is immediately quarantined. Determine which assertion rejected it:

- If the rejected behaviour is explicitly required and materially relevant, clarify the task contract and classify the alternate as invalid.
- If the assertion encodes an unstated implementation choice, weaken or replace it.
- If validity remains debatable, exclude the capsule.

After any change, create a new capsule version and rerun every control. Never “vote” between the test and the alternate while retaining the capsule in the run.

Q3: Mutation survival should be reported as a diagnostic, not gated and not dropped. Report mutation operator set, generated/killed/equivalent/unresolved counts, and requirement-level kill distribution. Use surviving mutants to discover missing assertions; use killed mutants to inspect possible overspecification.

There should be no universal mutation threshold and no “≥20% survive hardening” corpus gate. Survival is influenced by operator choice, equivalent mutants, code shape, and the mismatch between synthetic faults and agent-produced errors. The meaningful gate is demonstrated rejection of plausible wrong patches alongside acceptance of valid alternatives. Mutation results may justify further review, but cannot certify or disqualify a capsule mechanically.

Q4: An LLM judge should have no role in the binary solved/not-solved oracle for this experiment. It may assist offline with requirement extraction, alternate generation, mutant triage, identifying suspicious patches, and proposing adversarial probes—but its outputs require deterministic confirmation or human review.

Narrow the current doctrine further: scope and compatibility should normally be checked through diffs, policies, builds, API tests, and execution. “Maintainability” should not gate correctness unless converted into an explicit, predeclared mechanical constraint. “Is this a hack?” should trigger investigation and new executable probes, not an LLM-issued failure. If an inherently semantic concern cannot be operationalised, report it separately under blinded human review or mark the trial indeterminate. Do not include it in cost per solved task.

Q5: The model-tier axis makes implementation independence more important, not less. A reference-shaped oracle can systematically favour tiers that imitate familiar patches and penalise tiers that produce simpler, more defensive, or unconventional solutions. That would measure stylistic alignment with the oracle.

Use exactly the same versioned oracle for all tiers, keep it blind to model identity, and audit failures by tier and assertion. If one tier disproportionately fails a particular assertion while manual review finds legitimate solutions, invalidate that capsule’s results across every tier—not only for the disadvantaged tier—and rerun with a new version. Report results both overall and by task/requirement category so genuine capability differences are not confused with oracle-style interactions.

STRONGEST OBJECTION TO MY OWN POSITION: Requiring two correct alternates plus independent human review may make capsule production too expensive and slow for a solo founder, while still failing to enumerate the long tail of valid implementations. The apparent rigor could be costly theatre rather than comprehensive protection.

WHAT WOULD CHANGE MY MIND: A blinded study showing that a cheaper oracle protocol—such as one alternate plus property tests—has under 2% disagreement with independent expert adjudication across diverse agent patches, with no model-tier-correlated false rejection, would justify relaxing the minimum.

CONFIDENCE: high, because oracle errors of 4–12 points are comparable to or larger than the experiment’s detectable model effects, making strict admission and quarantine essential.
tokens used
15,400
POSITION: A decision-grade capsule needs a behaviourally specified, implementation-agnostic executable oracle with positive, negative, alternative-implementation, regression, and anti-gaming evidence. Test count, coverage, and mutation score are diagnostics—not proof. Any ambiguity should lead to quarantine, not a forced pass/fail, because oracle error can easily exceed the model-tier effect being measured.

Q1: Mandatory components:

- A pinned, reproducible environment and base commit.
- An explicit behavioural contract: requirements, permitted interfaces, compatibility expectations, and out-of-scope behaviour.
- A requirement→test map covering every claimed requirement.
- Hidden target tests that fail on the base state for the intended reason.
- A known-good reference patch that passes target and regression tests.
- Relevant upstream regression tests, plus deterministic static checks only where the task explicitly requires structural constraints.
- At least one credible near-miss per substantive requirement, demonstrating rejection of superficial or incomplete fixes.
- Two structurally distinct correct implementations that both pass.
- At least one task-specific adversarial probe covering likely grader attacks: test deletion, test/config bypass, hard-coded outputs, dependency/environment manipulation, or equivalent.
- A manual oracle review confirming that assertions test observable requirements rather than reference-patch details.

Thus controls 1–6 should all be mandatory for decision-grade runs. More mutants, fuzzing, property tests, platform variants, and additional alternates are valuable but not universal entry requirements. A capsule that cannot meet the minimum remains exploratory and must not influence purchasing or tier-selection decisions.

Q2: Use a contract-first, bidirectional challenge procedure.

First, write the behavioural contract independently of the reference diff. Then build tests from the contract. Challenge weakness with near-misses, real historical mistakes, generated candidate patches, fuzzing, and mutants. Challenge strictness with two meaningfully different correct solutions: one written by the capsule author and one independently written or reviewed by another competent engineer. LLMs may propose either, but a human must inspect and endorse their correctness without relying on the verifier result.

“Different” must mean a different algorithm, control flow, abstraction, or integration strategy—not renamed or reformatted reference code. For unusually constrained tasks, the reviewer may document why only one implementation family is plausible, but that exception should trigger additional property or differential testing.

If a valid alternate fails, the capsule is immediately quarantined. Determine which assertion rejected it:

- If the rejected behaviour is explicitly required and materially relevant, clarify the task contract and classify the alternate as invalid.
- If the assertion encodes an unstated implementation choice, weaken or replace it.
- If validity remains debatable, exclude the capsule.

After any change, create a new capsule version and rerun every control. Never “vote” between the test and the alternate while retaining the capsule in the run.

Q3: Mutation survival should be reported as a diagnostic, not gated and not dropped. Report mutation operator set, generated/killed/equivalent/unresolved counts, and requirement-level kill distribution. Use surviving mutants to discover missing assertions; use killed mutants to inspect possible overspecification.

There should be no universal mutation threshold and no “≥20% survive hardening” corpus gate. Survival is influenced by operator choice, equivalent mutants, code shape, and the mismatch between synthetic faults and agent-produced errors. The meaningful gate is demonstrated rejection of plausible wrong patches alongside acceptance of valid alternatives. Mutation results may justify further review, but cannot certify or disqualify a capsule mechanically.

Q4: An LLM judge should have no role in the binary solved/not-solved oracle for this experiment. It may assist offline with requirement extraction, alternate generation, mutant triage, identifying suspicious patches, and proposing adversarial probes—but its outputs require deterministic confirmation or human review.

Narrow the current doctrine further: scope and compatibility should normally be checked through diffs, policies, builds, API tests, and execution. “Maintainability” should not gate correctness unless converted into an explicit, predeclared mechanical constraint. “Is this a hack?” should trigger investigation and new executable probes, not an LLM-issued failure. If an inherently semantic concern cannot be operationalised, report it separately under blinded human review or mark the trial indeterminate. Do not include it in cost per solved task.

Q5: The model-tier axis makes implementation independence more important, not less. A reference-shaped oracle can systematically favour tiers that imitate familiar patches and penalise tiers that produce simpler, more defensive, or unconventional solutions. That would measure stylistic alignment with the oracle.

Use exactly the same versioned oracle for all tiers, keep it blind to model identity, and audit failures by tier and assertion. If one tier disproportionately fails a particular assertion while manual review finds legitimate solutions, invalidate that capsule’s results across every tier—not only for the disadvantaged tier—and rerun with a new version. Report results both overall and by task/requirement category so genuine capability differences are not confused with oracle-style interactions.

STRONGEST OBJECTION TO MY OWN POSITION: Requiring two correct alternates plus independent human review may make capsule production too expensive and slow for a solo founder, while still failing to enumerate the long tail of valid implementations. The apparent rigor could be costly theatre rather than comprehensive protection.

WHAT WOULD CHANGE MY MIND: A blinded study showing that a cheaper oracle protocol—such as one alternate plus property tests—has under 2% disagreement with independent expert adjudication across diverse agent patches, with no model-tier-correlated false rejection, would justify relaxing the minimum.

CONFIDENCE: high, because oracle errors of 4–12 points are comparable to or larger than the experiment’s detectable model effects, making strict admission and quarantine essential.
