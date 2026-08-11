OpenAI Codex v0.144.2
--------
workdir: C:\Users\Srijan\Documents\BenchMe
model: opencode-go/glm-5.2
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fee16-87d5-79d1-ab49-da527806fbc6
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
POSITION: Execution stays the ground truth for correctness, but any test suite pulled from history is guilty until proven innocent. The oracle that gates a decision-grade run is hand-written to a behavior spec written *before* the existing tests are read, with at least two independently authored alternate implementations proving it is implementation-agnostic. Mutation score is published, not gated. The LLM judge is forbidden as a scorer and permitted only as a generator of probes and alternates, on properties execution genuinely cannot see.

Q1: Mandatory to enter a decision-grade run:
- An implementation-agnostic behavior spec (inputs, observable outputs, side effects, documented constraints) written before any existing test is read.
- base negative: the target patch does *not* pass the oracle pre-fix (the bug is real and visible).
- reference positive: a known-good patch passes (the oracle is satisfiable).
- regression: at least one unaffected behavioral facet still passes (no over-constraint).
- ≥2 alternate implementations that pass, written from the spec alone with no access to the object's test suite — one by the capsule author, one by a second reviewer.
- adversarial-verifier probe: at least one known game-the-grader attempt (e.g. patching the test instead of the code) must fail.

Nice-to-have, explicitly non-gating: no-op/near-miss variants (fold into alternates), broad mutation coverage, judge-based scope checks. A capsule missing these can still enter but is tagged coarse.

Q2: Resolve the tension by separating the two failure modes and hardening against the one that actually matters.
- Against wrong-accepts: run k≥3 baseline trials with a weak model on each capsule before hardening. Any passing patch a human confirms does not match the spec becomes a *no-accept* regression check — derived from a spec property the patch violates, not by tightening the spec arbitrarily. This hardens against real failure modes, not abstract mutants.
- Against false-rejects: each alternate written from spec alone must pass. If an alternate fails, the bug is in the spec/oracle, not the alternate. New capsule version; nothing edited in place.
- Floor is three alternates: author, second reviewer, one generated by an independent model under spec-only conditions. Two passing is the bar; the third breaks spec-ambiguity ties.

Q3: Reported number, not gate. The replicability study directly undercuts mutation score for the defective-code setting, and a hard threshold invites Goodhart — authors optimize against the gate rather than against real reward hacks. Publish per capsule; treat very low scores (<10%) as a documentary smell triggering human review, not automatic exclusion. The more directly relevant signal — does the oracle reject actual weak-model patches — is what the hardening loop already targets.

Q4: Defend the doctrine's direction, narrow its border.
- The judge is forbidden as scorer for any property execution can observe.
- Permitted in exactly two places: (a) generating adversarial probes and alternate implementations, which are then run against execution so the judge's bias cannot enter the score directly; (b) judging scope/compat/maintainability where the property genuinely has no executable signal — but even there the judge writes its verdict as a runnable test (e.g. asserts the public API surface), not as a per-patch opinion.
- Same-family judging is forbidden: no model family judges its own tier.

Q5: Yes; this is the central risk and the model-tier experiment must be designed against it. An implementation-sensitive oracle measures style fit, not capability. Structural fixes:
- The model-tier experiment is restricted to capsules meeting the ≥2-alternate bar.
- Publish a per-capsule *oracle sensitivity* number: fraction of confirmed-good alternates passing. Capsules below 1.0 are flagged style-biased.
- Report cost-per-solved-task two ways: over the strict oracle subset and over the impl-agnostic-only subset. Divergence beyond the ~12.5-point MDE is reported as style-contamination evidence, not noise.
- A capsule with zero confirmed alternates is unsafe for cross-model comparison regardless of other metrics.

STRONGEST OBJECTION TO MY OWN POSITION: Two independently authored alternates per capsule is a heavy lift for a solo founder over 35 capsules, and "alternate passes" is a weak proxy for impl-agnosticity — alt authors share the spec author's interpretation by construction. A perfect oracle shipping six months late validates nothing, and a cheaper mutation-based signal on actual agent patches might catch more wrong-accepts than two hand-written alts ever would.

WHAT WOULD CHANGE MY MIND: Evidence on real agent-generated patches (not hand-crafted mutants) that impl-agnostic oracles with k<2 alternates achieve <10% disagreement against a blinded independent evaluator; or that mutation survival on real agent patches in these harness+model-tier configurations correlates with false-acceptance.

CONFIDENCE: medium. The published evidence points cleanly at impl-agnostic hand-written oracles, but the operating procedure has not been validated on agent-generated patches in this configuration, and at N=35, k=5 only large effects are observable regardless of oracle quality — so rigor may matter less than effect size.
tokens used
14,160
POSITION: Execution stays the ground truth for correctness, but any test suite pulled from history is guilty until proven innocent. The oracle that gates a decision-grade run is hand-written to a behavior spec written *before* the existing tests are read, with at least two independently authored alternate implementations proving it is implementation-agnostic. Mutation score is published, not gated. The LLM judge is forbidden as a scorer and permitted only as a generator of probes and alternates, on properties execution genuinely cannot see.

Q1: Mandatory to enter a decision-grade run:
- An implementation-agnostic behavior spec (inputs, observable outputs, side effects, documented constraints) written before any existing test is read.
- base negative: the target patch does *not* pass the oracle pre-fix (the bug is real and visible).
- reference positive: a known-good patch passes (the oracle is satisfiable).
- regression: at least one unaffected behavioral facet still passes (no over-constraint).
- ≥2 alternate implementations that pass, written from the spec alone with no access to the object's test suite — one by the capsule author, one by a second reviewer.
- adversarial-verifier probe: at least one known game-the-grader attempt (e.g. patching the test instead of the code) must fail.

Nice-to-have, explicitly non-gating: no-op/near-miss variants (fold into alternates), broad mutation coverage, judge-based scope checks. A capsule missing these can still enter but is tagged coarse.

Q2: Resolve the tension by separating the two failure modes and hardening against the one that actually matters.
- Against wrong-accepts: run k≥3 baseline trials with a weak model on each capsule before hardening. Any passing patch a human confirms does not match the spec becomes a *no-accept* regression check — derived from a spec property the patch violates, not by tightening the spec arbitrarily. This hardens against real failure modes, not abstract mutants.
- Against false-rejects: each alternate written from spec alone must pass. If an alternate fails, the bug is in the spec/oracle, not the alternate. New capsule version; nothing edited in place.
- Floor is three alternates: author, second reviewer, one generated by an independent model under spec-only conditions. Two passing is the bar; the third breaks spec-ambiguity ties.

Q3: Reported number, not gate. The replicability study directly undercuts mutation score for the defective-code setting, and a hard threshold invites Goodhart — authors optimize against the gate rather than against real reward hacks. Publish per capsule; treat very low scores (<10%) as a documentary smell triggering human review, not automatic exclusion. The more directly relevant signal — does the oracle reject actual weak-model patches — is what the hardening loop already targets.

Q4: Defend the doctrine's direction, narrow its border.
- The judge is forbidden as scorer for any property execution can observe.
- Permitted in exactly two places: (a) generating adversarial probes and alternate implementations, which are then run against execution so the judge's bias cannot enter the score directly; (b) judging scope/compat/maintainability where the property genuinely has no executable signal — but even there the judge writes its verdict as a runnable test (e.g. asserts the public API surface), not as a per-patch opinion.
- Same-family judging is forbidden: no model family judges its own tier.

Q5: Yes; this is the central risk and the model-tier experiment must be designed against it. An implementation-sensitive oracle measures style fit, not capability. Structural fixes:
- The model-tier experiment is restricted to capsules meeting the ≥2-alternate bar.
- Publish a per-capsule *oracle sensitivity* number: fraction of confirmed-good alternates passing. Capsules below 1.0 are flagged style-biased.
- Report cost-per-solved-task two ways: over the strict oracle subset and over the impl-agnostic-only subset. Divergence beyond the ~12.5-point MDE is reported as style-contamination evidence, not noise.
- A capsule with zero confirmed alternates is unsafe for cross-model comparison regardless of other metrics.

STRONGEST OBJECTION TO MY OWN POSITION: Two independently authored alternates per capsule is a heavy lift for a solo founder over 35 capsules, and "alternate passes" is a weak proxy for impl-agnosticity — alt authors share the spec author's interpretation by construction. A perfect oracle shipping six months late validates nothing, and a cheaper mutation-based signal on actual agent patches might catch more wrong-accepts than two hand-written alts ever would.

WHAT WOULD CHANGE MY MIND: Evidence on real agent-generated patches (not hand-crafted mutants) that impl-agnostic oracles with k<2 alternates achieve <10% disagreement against a blinded independent evaluator; or that mutation survival on real agent patches in these harness+model-tier configurations correlates with false-acceptance.

CONFIDENCE: medium. The published evidence points cleanly at impl-agnostic hand-written oracles, but the operating procedure has not been validated on agent-generated patches in this configuration, and at N=35, k=5 only large effects are observable regardless of oracle quality — so rigor may matter less than effect size.
