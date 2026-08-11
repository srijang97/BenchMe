OpenAI Codex v0.144.2
--------
workdir: C:\Users\Srijan\Documents\BenchMe
model: opencode-go-responses/gpt-5.6-luna
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fee15-5200-7bd1-bc9a-095245ce9a82
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
I’m treating this as a design-position memo rather than a code change. The key decision is whether “decision-grade” should mean merely executable and calibrated, or should also require evidence that the oracle accepts valid diversity and resists obvious gaming.
**Considering model evaluation**

I'm thinking about claims from a paper's counterexample, but there's not enough to outweigh correctness. I wonder if using an ensemble could help. If I do, I should freeze the model, version, and prompt for calibration, then report inter-rater and abstention. Overdoing it isn't necessary! Question 5 deals with style, as it's implementation-sensitive. Model tiers seem to have different implementations, so I might need to replace structural checks with behavioral ones and perform a style-blindness audit.
**Considering empirical calibration**

I'm thinking about the changes in mind when it comes to testing how capsules meet criteria and how independent evaluators are impacted. It seems like we'll need a specific measurement of blind samples, like 50 capsules with independent evaluation rates. I think we can work without tools this time and deliver the final result directly. I'll suggest a confidence level of "high," even though exact counts are uncertain, leaning towards a medium level in evidence.
codex
POSITION: Decision-grade capsules should require a semantic, executable oracle plus evidence that it accepts legitimate implementation diversity and resists common grader exploits. Controls 1–4 are necessary but insufficient; controls 5–6 should become mandatory for admission. Mutation score and LLM judgments should inform audit and secondary metrics, never substitute for behavioral execution or become a composite correctness gate.

Q1: A decision-grade capsule must contain:

- A pinned base commit, reproducible environment, exact command, timeout, resource limits, and deterministic verifier behavior.
- An explicit behavioral contract stating both requirements and important non-requirements.
- A hidden, implementation-agnostic executable verifier with a requirement-to-assertion map. Static checks are mandatory only when the task explicitly specifies the property; source-shape checks are not correctness checks by default.
- Passing base-negative, reference-positive, regression, and no-op/near-miss controls.
- Passing alternate-solution and adversarial-verifier controls.
- Independent review of the task specification and oracle.

A capsule lacking any of these is exploratory, not suitable for a model-tier decision. Mutation analysis, an LLM judge, extra alternates, and broad developer-suite execution are useful additions, but not admission requirements.

Q2: Make two materially different, spec-compliant alternate implementations mandatory. They should be written independently by implementers who did not write the verifier and who cannot inspect hidden tests. Ideally, use different algorithmic decompositions, not two minor variations of the reference patch.

If an alternate fails, diagnose before changing anything. If it is valid under the written contract, the verifier is defective: create a new capsule version and repair it. If the alternate is invalid, discard and replace it. If the contract cannot determine validity, the task is underspecified and must be rewritten or excluded. Never add a test solely because it kills a mutant if that test rejects a validated alternate. The adversarial probe should use a standard corpus-level pack covering applicable attacks such as hard-coded outputs, visible-test overfitting, test tampering, and environment inspection.

Q3: Mutation survival should be reported, not used as a gate, and not dropped. Remove the prior “≥20% survive” admission rule. The cited replicability result makes a universal threshold indefensible for capsule hardening.

Report survival per capsule and by mutant/operator class, excluding equivalent mutants where possible. A surviving non-equivalent mutant that targets an explicit requirement should trigger oracle review and likely a new capsule version. Mutation score is a diagnostic for finding blind spots, not evidence that a capsule is valid or invalid by itself.

Q4: Narrow the current doctrine. An LLM judge should have no authority over executable behavioral correctness or the solved/unsolved label. It may be used for:

- Flagging possible hacks or scope violations for human adjudication.
- Assessing separately reported non-functional properties such as maintainability when those properties cannot be operationalized.
- Generating candidate probes or review cases.

Any judge-based result must be separate from solve rate and cost per solved task, with a frozen model/prompt, a written rubric, calibration examples, abstention, and human review of consequential flags. “Sounds correct” is an unacceptable substitute for execution, even if judges perform well on unambiguous cases.

Q5: Yes. If the oracle rewards reference structure, idioms, file locations, or incidental implementation choices, model-tier comparison measures implementation style rather than capability. This is especially dangerous when cheaper models systematically produce different but valid designs.

The consequence is strict: behavioral acceptance must be implementation-agnostic unless the task explicitly requires a compatibility or structural property. Report style, maintainability, and compatibility as separate axes. Audit each capsule with the two alternates and targeted differential/property tests. Cost per solved task should be computed from semantic success; style failures should be classified separately rather than silently counted as capability failures.

STRONGEST OBJECTION TO MY OWN POSITION: Two alternates and adversarial probes materially increase capsule-mining cost, may introduce reviewer judgment, and still cannot prove that a verifier accepts every valid solution. A smaller corpus with stronger oracles may also reduce statistical power.

WHAT WOULD CHANGE MY MIND: A blinded study over a substantial capsule sample showing that controls 1–4 predict independent evaluator agreement and false-accept/false-reject rates as well as controls 5–6, with negligible incremental benefit from alternates and adversarial probes. Conversely, measured false-rejection from validated alternates would justify increasing the alternate count.

CONFIDENCE: medium. The direction is strongly supported; the exact minimum of two alternates and the probe pack is an engineering threshold requiring calibration data.
tokens used
51,545
POSITION: Decision-grade capsules should require a semantic, executable oracle plus evidence that it accepts legitimate implementation diversity and resists common grader exploits. Controls 1–4 are necessary but insufficient; controls 5–6 should become mandatory for admission. Mutation score and LLM judgments should inform audit and secondary metrics, never substitute for behavioral execution or become a composite correctness gate.

Q1: A decision-grade capsule must contain:

- A pinned base commit, reproducible environment, exact command, timeout, resource limits, and deterministic verifier behavior.
- An explicit behavioral contract stating both requirements and important non-requirements.
- A hidden, implementation-agnostic executable verifier with a requirement-to-assertion map. Static checks are mandatory only when the task explicitly specifies the property; source-shape checks are not correctness checks by default.
- Passing base-negative, reference-positive, regression, and no-op/near-miss controls.
- Passing alternate-solution and adversarial-verifier controls.
- Independent review of the task specification and oracle.

A capsule lacking any of these is exploratory, not suitable for a model-tier decision. Mutation analysis, an LLM judge, extra alternates, and broad developer-suite execution are useful additions, but not admission requirements.

Q2: Make two materially different, spec-compliant alternate implementations mandatory. They should be written independently by implementers who did not write the verifier and who cannot inspect hidden tests. Ideally, use different algorithmic decompositions, not two minor variations of the reference patch.

If an alternate fails, diagnose before changing anything. If it is valid under the written contract, the verifier is defective: create a new capsule version and repair it. If the alternate is invalid, discard and replace it. If the contract cannot determine validity, the task is underspecified and must be rewritten or excluded. Never add a test solely because it kills a mutant if that test rejects a validated alternate. The adversarial probe should use a standard corpus-level pack covering applicable attacks such as hard-coded outputs, visible-test overfitting, test tampering, and environment inspection.

Q3: Mutation survival should be reported, not used as a gate, and not dropped. Remove the prior “≥20% survive” admission rule. The cited replicability result makes a universal threshold indefensible for capsule hardening.

Report survival per capsule and by mutant/operator class, excluding equivalent mutants where possible. A surviving non-equivalent mutant that targets an explicit requirement should trigger oracle review and likely a new capsule version. Mutation score is a diagnostic for finding blind spots, not evidence that a capsule is valid or invalid by itself.

Q4: Narrow the current doctrine. An LLM judge should have no authority over executable behavioral correctness or the solved/unsolved label. It may be used for:

- Flagging possible hacks or scope violations for human adjudication.
- Assessing separately reported non-functional properties such as maintainability when those properties cannot be operationalized.
- Generating candidate probes or review cases.

Any judge-based result must be separate from solve rate and cost per solved task, with a frozen model/prompt, a written rubric, calibration examples, abstention, and human review of consequential flags. “Sounds correct” is an unacceptable substitute for execution, even if judges perform well on unambiguous cases.

Q5: Yes. If the oracle rewards reference structure, idioms, file locations, or incidental implementation choices, model-tier comparison measures implementation style rather than capability. This is especially dangerous when cheaper models systematically produce different but valid designs.

The consequence is strict: behavioral acceptance must be implementation-agnostic unless the task explicitly requires a compatibility or structural property. Report style, maintainability, and compatibility as separate axes. Audit each capsule with the two alternates and targeted differential/property tests. Cost per solved task should be computed from semantic success; style failures should be classified separately rather than silently counted as capability failures.

STRONGEST OBJECTION TO MY OWN POSITION: Two alternates and adversarial probes materially increase capsule-mining cost, may introduce reviewer judgment, and still cannot prove that a verifier accepts every valid solution. A smaller corpus with stronger oracles may also reduce statistical power.

WHAT WOULD CHANGE MY MIND: A blinded study over a substantial capsule sample showing that controls 1–4 predict independent evaluator agreement and false-accept/false-reject rates as well as controls 5–6, with negligible incremental benefit from alternates and adversarial probes. Conversely, measured false-rejection from validated alternates would justify increasing the alternate count.

CONFIDENCE: medium. The direction is strongly supported; the exact minimum of two alternates and the probe pack is an engineering threshold requiring calibration data.
