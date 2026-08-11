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