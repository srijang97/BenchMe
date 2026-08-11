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