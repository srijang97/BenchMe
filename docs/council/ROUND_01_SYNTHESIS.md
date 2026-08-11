# Council round 1 — chair synthesis: the oracle contract

**Chair**: Opus 5 · **Date**: 2026-08-11 · **Motion**: `ROUND_01_MOTION.md`
**Raw responses**: `round01/*.raw.md` · **Extracted**: `round01/*.answer.md`

## Seats

| Member | Lab | Effort | Status |
|---|---|---|---|
| Gemini 3.6 Flash (High) | Google | high | complete |
| GPT 5.6 Luna | OpenAI | xhigh | complete |
| DeepSeek V4 Flash | DeepSeek | xhigh | complete |
| Kimi K3 | Moonshot | xhigh | complete |
| GLM 5.2 | Zhipu | xhigh | complete |
| Qwen3.8 Max | Alibaba | xhigh | **partial — truncated after Q1** |
| Grok 4.5 | xAI | — | unavailable (503 upstream) |
| GPT 5.6 Sol | OpenAI | xhigh | complete (run after synthesis) |

Quorum: 6 complete non-chair responses across 5 labs. Met.

---

## 1. Unanimous — treat as settled

**Mutation survival is a reported diagnostic, never a gate. The "≥20% of tasks
survive hardening" threshold is dropped.** All five complete answers reached
this independently, on three converging grounds: the replicability study
invalidates mutation score precisely for the defect-exposing setting capsule
hardening occupies; a published threshold with no derivation invites Goodharting
by whoever writes the tests; and — Kimi's observation, which is the sharpest —
**the gate is directionally backwards**. A weak capsule passes a survival gate
easily (everything survives, including wrong patches) while a legitimately
strict capsule fails it.

**No LLM judge decides solved/unsolved. Ever.** Unanimous. Permitted roles are
generation (alternates, mutants, probes — all then checked by execution) and
non-blocking audit of *passing* runs, reported as a separate metric under the
no-composite rule. Two narrowings worth adopting: GLM's — no model family judges
its own tier; and Kimi's — do not judge maintainability inside the oracle at all
for the tier experiment, because style judgement is exactly where
implementation bias enters.

**An implementation-sensitive oracle measures style, not capability, and that
is the central threat to the tier experiment.** Unanimous, and DeepSeek stated
the danger most precisely: residual style sensitivity would bias cheap models
*in the direction the commercial thesis predicts*. The experiment could confirm
its own hypothesis for entirely the wrong reason.

**When an alternate fails, triage before changing anything.** Unanimous
procedure: if the alternate satisfies the written task statement, the oracle is
defective — fix it, mint a new capsule version; if it violates a stated
requirement, the alternate is wrong — repair or discard it; if the statement
cannot settle it, the task is under-specified — rewrite or exclude. Nobody may
weaken a test merely to admit an alternate, and no failing alternate is dropped
silently.

---

## 2. Contested — chair rulings

### How many alternate implementations? (1 → 3 across the council)

Gemini says one; Kimi one required plus one attempted; Luna and DeepSeek two;
GLM a floor of three. This is the cost driver of the entire proposal.

**Ruling: one authored alternate is mandatory at capsule creation; further
alternates are harvested, not authored.**

The council treated alternates purely as an upfront cost, and I think that is a
modelling error. The tier experiment itself produces alternates for free —
every patch any tier submits is a candidate. So:

- **At creation**: one alternate, written from the task statement without
  reading the reference diff. That is the admission bar.
- **Continuously**: every patch the oracle *rejects* that a human confirms is
  behaviourally correct becomes a Type-N (narrow) oracle defect, triggers
  capsule vNext, and is retained as a permanent alternate.

This converts the expensive control into a byproduct of running the experiment,
while keeping a real bar at entry. It does introduce a mild circularity — using
the system under test to validate the instrument — but only in the
over-strictness direction, where it is sound: a correct patch that the oracle
rejected is an oracle defect no matter who produced it.

### Is the adversarial probe mandatory?

Kimi, GLM and Luna say yes; DeepSeek argues it cannot be an entry gate because
probing is open-ended and can always be extended further; Gemini calls it
nice-to-have.

**Ruling: the disagreement is definitional and dissolves.** A *fixed, bounded
probe battery* is mandatory — test modification, score-file spoof, output spoof,
importing the reference, sentinel presence. Open-ended red-teaming stays
optional. DeepSeek's objection is correct about unbounded probing and does not
apply to a fixed list.

Adopt Qwen's efficiency point here: verify sealing **once per environment
manifest**, not once per capsule — hidden tests absent, future git objects
absent, egress denied. Per-capsule probes then only cover capsule-specific
gaming.

### Hardening against what?

GLM contributed the most original idea in the round and it deserves promotion.
Rather than hardening against synthetic mutants, **harden against observed
failure modes**: run a weak model against each capsule k≥3 times *before*
hardening, and any patch that passes but which a human confirms does not meet
the specification becomes a no-accept regression check derived from the
specification property it violates.

This is strictly better than mutation hardening for our purpose. It targets the
wrong-accept class that actually occurs in our configuration, rather than the
class an operator-rule generator happens to produce — and it sidesteps the
validity objection to mutation score entirely, because it never uses mutation
score as evidence of anything.

---

## 3. Chair's own position, where it differs from the council

**The yield objection is misdirected.** Kimi and GLM both warn that mandatory
alternates could push the corpus below the ~30 capsules the power analysis
needs. That conflates two different things. Alternates do not reduce *yield* —
yield is fixed by stages 0–2, which decide how many commits convert. Alternates
raise *cost per surviving capsule*. The project's stated pivot criterion has two
arms — fewer than 8 valid tasks, **or** more than one engineer-day per task —
and mandatory alternates load the second arm only. That matters because the two
arms have different remedies: low yield means change repository, high curation
cost means change procedure.

**The self-confirmation risk needs a pre-registered falsifier, not just a
report.** DeepSeek and Kimi propose reporting per-tier oracle-rejection rates.
Necessary but not sufficient — a number reported after the fact can always be
explained away. The project's own doctrine already requires pre-registering
metrics and stopping rules. So: **before running the tier experiment, commit in
writing that if the cost-per-solved inversion appears AND per-tier
oracle-rejection asymmetry exceeds a stated threshold, the result is void.**
Write the falsifier down first, when it is still cheap to be honest.

**Nobody costed the recommendation.** At 35 capsules with one authored alternate
each at roughly 30–60 minutes, that is 18–35 engineer-hours before any
experiment runs — against a 16-week solo window with industry re-entry running
in parallel. This is affordable at one alternate and clearly not at three, which
is the strongest practical argument for the staged ruling above.

---

## 4. Minority reports, preserved

**Gemini (high confidence, against the majority's caution)**: false rejections
are the dominant commercial risk, because a CI tool that blocks valid work gets
switched off. It would accept a weaker guard against wrong-accepts to protect
developer velocity. Everyone else weights the two error directions more evenly.

**DeepSeek, against its own recommendation**: the evidence says false
*acceptance* is the larger measured failure (77% of mined suites), and the
package here — alternates plus a no-op check — does not directly target that
class, while demoting mutation survival removes the only existing quantitative
guard without replacing it with a measured false-accept control. This is the
strongest objection anyone raised, including against my own ruling. GLM's
weak-model hardening loop is the partial answer; it should be treated as
answering DeepSeek's objection specifically.

**Kimi**: mandatory controls plus curation cost may be commercially wrong at
solo scale, and O1-level capsules with good seals ship months earlier while
still beating public benchmarks.

---

## 5. Risk register

| Risk | Severity | Mitigation | Owner |
|---|---|---|---|
| Oracle style-bias confirms the commercial thesis artifactually | **Critical** | Pre-registered falsifier; per-tier oracle-rejection rate as a headline | before experiment |
| Wrong-accepts survive because mutation gate was dropped | High | GLM weak-model hardening loop; curated known-wrong panel per capsule | during mining |
| Curation cost exceeds one engineer-day per capsule | High | One authored alternate; harvest the rest | measure on first 10 |
| Alternates share the spec author's interpretation by construction | Medium | Alternate written from statement only, never from the reference diff | procedure |
| Capsule versions proliferate as Type-N defects are found | Medium | Expected and correct; never edit in place | procedure |
| Judge drift changes audit results over time | Low | Log model and prompt version with every verdict | procedure |

---

## 5b. Addendum — GPT 5.6 Sol (xhigh), run after the synthesis above

Sol ran on the identical motion with no sight of the other answers or of this
synthesis. It confirms the three unanimous findings, making them **6 of 6**, and
narrows Q4 further than anyone else: maintainability must not gate correctness
unless first converted into an explicit predeclared mechanical constraint, and
"is this a hack?" should trigger investigation and new executable probes rather
than an LLM-issued failure.

### The argument that changes the weighting

> "Oracle errors of 4–12 points are comparable to or larger than the
> experiment's detectable model effects."

This is the sharpest quantitative point of the round and nobody else made it.
Re-scoring against hardened suites moved published agents by 4.2–9.0 points.
Our minimum detectable effect at 30 tasks × k=5 is about 12.5 points. **The
oracle's own error bar is the same order of magnitude as the effect we are
trying to measure.** That is a strong argument for strictness at entry, and it
cuts directly against my staged ruling.

### Four mechanisms adopted from Sol

1. **Quarantine, never repair in place, never "vote".** If a valid alternate
   fails, the capsule leaves the run immediately. It does not stay in while
   someone adjudicates test-versus-alternate. If validity stays debatable, the
   capsule is excluded rather than resolved by judgement.
2. **A tier-correlated oracle defect invalidates the capsule across *all*
   tiers, not only the disadvantaged one.** Correcting only where a tier was
   hurt is itself a biased correction.
3. **A near-miss per substantive requirement**, not one per capsule. Near-misses
   are mechanical and cheap; one per capsule under-tests multi-requirement tasks.
4. **`indeterminate` becomes a trial outcome.** When a semantic concern cannot
   be operationalised, mark the trial indeterminate and exclude it from cost per
   solved task rather than forcing a pass or a fail. This stops judge-shaped
   concerns leaking into the headline metric.

### Revised ruling on alternate count

Sol requires two structurally distinct alternates at entry, joining Luna and
DeepSeek. That is now four of seven seats against my one-at-entry ruling, and
Sol supplies the quantitative reason.

**I am amending rather than reversing, because the two positions are coupled in
a way no seat noticed.** Harvesting alternates from the experiment only surfaces
over-strictness that somebody actually looks at — which means reviewing rejected
patches. But everyone already agreed to a per-tier oracle-rejection audit, and
that audit *is* a review of rejected patches. The harvesting cost is therefore
already committed; it is a byproduct of an audit we are doing regardless.

So the amended ruling:

- **One authored alternate at entry is sufficient *if and only if* the per-tier
  oracle-rejection audit is mandatory and runs continuously.**
- **If that audit is ever descoped, the entry bar rises to two alternates.**

The alternate count and the audit trade off against each other. What is not
acceptable is one alternate *and* no audit, which is where cost pressure will
naturally push.

---

## 6. The contract, as it now stands

A capsule may enter a decision-grade run when it has:

1. an implementation-agnostic behavioural specification, with a
   requirement→test map where every graded assertion traces to a stated
   requirement — unmapped assertions are excluded from grading;
2. base negative, with the pre-patch failure verified to be an assertion
   failure, not a collection or import error;
3. reference positive;
4. regression check on adjacent unchanged behaviour;
5. a near-miss rejection **per substantive requirement**, not one per capsule;
6. **one authored alternate that passes**, written from the statement without
   sight of the reference diff — conditional on the audit in the note below;
7. the fixed adversarial probe battery, with environment-level sealing verified
   once per environment manifest;
8. determinism preflight — reference passes k=3 consecutive runs;
9. pinned environment, budget and trial policy.

**Coupling condition**: item 6 stands at one alternate *only while* the per-tier
oracle-rejection audit is mandatory and continuous. Descope the audit and the
entry bar becomes two alternates. One alternate with no audit is not a
permitted configuration.

**Failure handling**: a failing valid alternate quarantines the capsule
immediately — no in-place repair, no adjudication while it remains in the run.
A tier-correlated oracle defect invalidates that capsule across every tier, not
only the tier it disadvantaged. Debatable validity means exclusion, not a
casting vote.

**Trial outcomes** are solved, unsolved, or `indeterminate`. Indeterminate
trials are excluded from cost per solved task and reported separately.

Reported but never gating: mutation survival, judge-based scope and hack audit
on a sample of passing runs, per-tier oracle-rejection rate.

---

## 7. What would change this

- Per-capsule oracle-rejection rates statistically indistinguishable across
  tiers on ~20 capsules × 3 tiers → the style-bias concern is theoretical and
  the alternate requirement can drop to attempted-not-required.
- Curated-panel kill-rate correlating strongly with alternate-based oracle
  quality over the first 50 capsules → promote it to a gate; a validated proxy
  beats principled refusal.
- Curation cost above ~3 engineer-hours per capsule at pydantic scale →
  mandatory-alternate becomes mandatory-attempt with a documented waiver.

---

## 8. Process notes

- Qwen3.8 Max truncated after Q1; its contributions on `error2pass` at entry,
  the k=3 determinism preflight, and environment-level rather than per-capsule
  sealing are adopted above. Q2–Q5 from that seat are missing, not disagreeing.
- Grok 4.5 was unreachable — 503 at the router on three attempts.
- Cross-critique was not run. Convergence on Q3, Q4 and Q5 was already
  unanimous, and the live disagreement (alternate count, curation economics) is
  an empirical question that critique cannot settle — only measurement can.
- This council did not use the octo runner. That runner assigns one default
  model per provider and cannot address five distinct models through the codex
  provider, which was the specified roster. Dispatch was via
  `scripts/ask-model.sh`; six models genuinely answered.
