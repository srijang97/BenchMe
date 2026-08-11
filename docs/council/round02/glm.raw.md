OpenAI Codex v0.144.2
--------
workdir: C:\Users\Srijan\Documents\BenchMe
model: opencode-go/glm-5.2
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019ff160-9418-7c31-a3fc-17582cfc9c96
--------
user
# Council round 2 — should failure kind gate the corpus, or label it?

You are one member of a council advising a solo technical founder. Other members
are different frontier models from different labs. Your answer will be
synthesised by a chair. Disagreement is useful; do not hedge toward the middle.

**This round revises a decision an earlier council made.** That council decided
correctly on the evidence it had. It has since been built and run, and the
evidence changed.

---

## 1. The project, briefly

**BenchMe** builds a private, execution-verified regression suite that gates
changes to a customer's AI coding-agent stack. A **capsule** is one evaluation
task mined from a repository's real history.

The mining procedure, which matters for everything below:

1. Find a commit that changed both source and tests.
2. Check out its **parent**.
3. Apply only the commit's **test changes** — the new tests now exist without the fix.
4. Run the touched tests. They should fail.
5. Apply the commit's **code changes** — the genuine upstream fix.
6. Run again. The tests should now pass.

A test that goes fail→pass across those two runs is the capsule's oracle,
called its **fail-to-pass** set.

The first real experiment this corpus supports holds the harness fixed and
varies **model tier** — frontier versus mid versus cheap open-weight — measuring
**cost per solved task**, not pass rate.

## 2. What round 1 decided

Round 1 ruled on the oracle contract. Unanimously: mutation survival is a
reported diagnostic and never a gate; no LLM judge decides solved/unsolved; an
implementation-sensitive oracle would measure style rather than capability.

It also adopted an existing rule: **a capsule's "base negative" must fail for the
right reason, and only an assertion failure qualifies.** `AttributeError`,
`ImportError` and `ModuleNotFoundError` mean the API is not there yet — feature
work — and are rejected. Collection and syntax errors are structural and
rejected.

The stated worry was that this would filter out feature work and cost yield, so
the build was instructed to count every rejection by class rather than assume
the rule was well calibrated.

## 3. What the first real batch showed

The miner has been built and run against `pydantic`, quarter 2025Q3.

| | |
|---|---|
| Candidates enumerated | 1,568 |
| Attempted | 21 |
| Validated | 1 |
| Rejected (verdict about the commit) | 10 |
| Apparatus (our tooling broke) | 10 |
| Conversion on adjudicated | **9.1%** — against 2.2% assumed |
| Cost | 34 s per candidate; whole corpus ≈ 20 h |

**The worry that motivated the rule did not materialise.** `missing_api`
rejections: **zero**. Not one candidate was rejected for being feature work.

**A different part of the rule cost heavily.** Of twelve classified
fail-to-pass tests, **six (50%) were rejected as `other:unparsed`** — because the
classifier reads the *exception name* and these had none it recognised:

- `Failed: DID NOT RAISE <class 'ValueError'>`
- `Failed: DID NOT WARN. No warnings of type ...`
- `PydanticDeprecatedSince20`
- `pydantic_core._pydantic_core.ValidationError`

The first three are pytest's own idiom for "the expected thing did not happen".
They are ordinary test failures that our name-matching could not identify.

**An audit of all ten rejections found seven were our defects, not properties of
the commits.** Three `regression_broken` verdicts were caused by a test that
parametrises on source line numbers — a patch shifts lines, the test's id
changes, and a renamed test was booked as a broken one. Four were the
`other:unparsed` cases above.

## 4. The reframe this round exists to test

Consider what the classification is actually deciding.

**Validity is already established by execution.** The "after" run applies the
*genuine upstream fix*. If a test fails before it and passes after it, then by
construction that failure was caused by the missing fix. The exception's name
adds no information about whether the task is real or solvable.

So the classifier is not deciding *is this a valid capsule*. It is deciding
*is this a bug fix or a feature addition* — *taxonomy*, not validity. Round 1's
rule rejects on a taxonomy judgement.

The proposal: **label, do not reject.** Record the failure kind on every capsule,
report corpus composition, and let each downstream experiment select the mix it
wants. Rejecting bakes one taxonomy choice permanently into the corpus;
labelling leaves it a reportable property.

**The honest counter-argument**, which you should weigh rather than dismiss: a
fail-to-pass against the reference patch proves the task is *solvable*, but not
that the *oracle is strong*. A test can pass for reasons unrelated to the
intended behaviour. Failure kind may be a cheap proxy for oracle quality that
the fail-to-pass check cannot supply, and discarding it may remove a guard whose
value is not visible in one batch of 21.

## 5. One relevant technical finding

Empirical, verified during this round's preparation. pytest can emit JUnit XML,
which distinguishes structurally:

- `<failure>` — the test ran and its expectation was not met
- `<error>` — the test could not run at all

That is the assertion-versus-structural distinction, supplied by pytest itself
with no name matching. The XML message is also not truncated to terminal width,
unlike the human-readable summary we currently parse.

Separately: **a single collection error aborts the entire pytest session.** With
one broken import present, none of six tests in another file ran.

## 6. What the council must decide

**Q1. Should failure kind gate corpus admission, or only label it?** If it should
still gate, say precisely which kinds are disqualifying and why execution
evidence is insufficient.

**Q2. What is the minimum evidence that a mined capsule is valid?** Does
fail-to-pass against the genuine reference patch suffice? If not, what does it
fail to establish, and what is the cheapest thing that closes the gap?

**Q3. Is pytest's `Failed:` protocol assertion-class?** `pytest.raises` not
raising, `pytest.warns` not warning, and explicit `pytest.fail()` all produce it.
It is library-independent — every pytest project emits it.

**Q4. Given the corpus will carry labels, what should the model-tier experiment
include or exclude?** Bug fixes only, or everything with the composition
reported? Note the minimum detectable effect is roughly 12.5 points at 30 tasks
with 5 trials, so corpus size has real statistical value.

**Q5. Does anything else in round 1's contract need amending in light of this?**
Round 1 required one authored alternate implementation at capsule creation,
conditional on a continuous per-tier oracle-rejection audit.

## 7. Required output format

Under 900 words. Be specific and decisive.

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
POSITION: Label failure kind; gate only on what execution already proves. The fail-to-pass check against a genuine reference patch is the strongest validity signal we have. The classification we lose is a taxonomy decision, not a validity decision, and one batch of 21 has shown the gate kills real capsules for classifier defects rather than commit properties. Gate on the distinction pytest already makes structurally (assertion-ran vs. could-not-run), label everything else, and let downstream experiments select.

Q1: Label, with one narrow gate retained. The only execution-derived distinction worth gating on is structural: did the test run at all? Use pytest's own `<failure>` vs `<error>` from JUnit XML, not name-matching. A test that could not collect or errored at setup is not a fair oracle — its fail-to-pass may reflect import wiring pulled in by the patch rather than the intended behavior. Everything that ran and asserted (`<failure>`) is admissible, including the `Failed: DID NOT RAISE` / `DID NOT WARN` / explicit `pytest.fail()` idioms. `missing_api` no longer gates; it labels. Execution evidence is insufficient only for the "test never ran" case, because that's the one case where fail-to-pass can be a side effect of the patch wiring up imports rather than the test's claim being met.

Q2: Fail-to-pass against the genuine reference patch is necessary and nearly sufficient. It establishes solvable and caused-by-the-fix. What it does *not* establish is oracle strength: that the test fails for the reason capsule intends and passes for the intended reason too. The cheapest closure is the structural `<failure>`/`<error>` split above — that distinguishes "asserted and was wrong" from "didn't run," which is where fail-to-pass is least informative. Beyond that we accept residual oracle weakness and surface it as a per-corpus composition label rather than a per-capsule gate. Anything stricter (mutation survival, behavior-coverage probes) is diagnostic, not gate — consistent with round 1.

Q3: Yes. `pytest.raises` not raising, `pytest.warns` not warning, and `pytest.fail()` all assert an expectation about program behavior, and pytest emits them as `<failure>` in JUnit XML. That is the failure class being labeled sanctions-worthy-by-our-ability-to-parse-exception-names-against, not any authentic property of the oracle. It is library-independent — every pytest project emits it. Treating it as not-an-assertion was a classifier bug.

Q4: Include failure-run tests; gate on ran-and-asserted broadly; label composition and report it. This batch caps at a 9.1% conversion rate; at 30 tasks/trial × 5 trials with MDE ~12.5 points, every capsule has real statistical value. The experiment should take all admissible capsules (ran-and-asserted), report the labeled mix (bug-fix vs feature vs refactor-attributed by commit message and most frequent failure kind), and verify the three tiers landed on comparable mixtures. If tiers vary in composition, a stratified analysis (cost-per-solved within each stratum and overall) is more honest than a bug-fix-only subset — bug-fix-only would let model-tier performance regress to "wins on the easy taxonomic stratum." The failure kind stays a recorded covariate and a candidate stratifier.

Q5: Two amendments. First, keep the one authored alternate implementation at capsule creation, but scope its authoring to the *new* narrow gate — anything that ran and asserted. It's a guard against the unauthorial test solving itself by reasserting, and execution-loss narrowed neither weakens nor strengthens it; execution-less confused-corecapsule is orthogonal. Second — and new — fix the per-tier audit to not only hold the tier-rejection fraction but also the failure-kind label by tier. The conditional trigger should compare labeled failure-kind distribution across tiers, not just counts. If one tier systematically selects tests with weaker oracles (e.g., library-idiom-heavy DID-NOT-RAISE tests that some models pattern-match cheaply), that is the confound the audit needs to catch; raw rejection counts would mask it.

STRONGEST OBJECTION TO MY OWN POSITION: Oracle strength is real and failure kind might be the only cheap proxy for it. A `DID NOT RAISE ValueError` assertion can pass after a model adds any `raise ValueError` anywhere upstream — even in unrelated code paths — without the model fixing the intended behavior. Fail-to-pass proves the test is solvable, not that the test discriminates correct fixes from plausible incorrect ones. Relabeling and discarding the gate removes a guard that, on N=21, is invisible but may matter at scale when models learn to satisfy weak oracles cheaply. The "label stratifier" response assumes we'll analyze by label; if models exploit weak oracles uniformly across the labels we record, the stratifier won't catch it.

WHAT WOULD CHANGE MY MIND: A second batch (N ≥ 50, multi-project) showing the narrow `<error>`-only gate admits capsules whose pass-after-fix is reproducible by patches that do *not* implement the intended behavior — e.g., an alternate patch that satisfies the oracle without addressing the commit's stated purpose succeeds on a meaningful fraction (≥15%) of admissible capsules. That would be direct evidence that fail-to-pass is not oracle-strength-sufficient and that the discarded gate (or a better one) buys real discrimination.

CONFIDENCE: medium. The argument from execution semantics is tight and the batch evidence is concrete, but N=21 is small, one project is one project, and pydantic's high-assertion-density codebase may not generalize. The structural-gate narrowing depends on pytest's own semantics holding across the next several projects, which is reasonable but not yet shown.
tokens used
11,693
POSITION: Label failure kind; gate only on what execution already proves. The fail-to-pass check against a genuine reference patch is the strongest validity signal we have. The classification we lose is a taxonomy decision, not a validity decision, and one batch of 21 has shown the gate kills real capsules for classifier defects rather than commit properties. Gate on the distinction pytest already makes structurally (assertion-ran vs. could-not-run), label everything else, and let downstream experiments select.

Q1: Label, with one narrow gate retained. The only execution-derived distinction worth gating on is structural: did the test run at all? Use pytest's own `<failure>` vs `<error>` from JUnit XML, not name-matching. A test that could not collect or errored at setup is not a fair oracle — its fail-to-pass may reflect import wiring pulled in by the patch rather than the intended behavior. Everything that ran and asserted (`<failure>`) is admissible, including the `Failed: DID NOT RAISE` / `DID NOT WARN` / explicit `pytest.fail()` idioms. `missing_api` no longer gates; it labels. Execution evidence is insufficient only for the "test never ran" case, because that's the one case where fail-to-pass can be a side effect of the patch wiring up imports rather than the test's claim being met.

Q2: Fail-to-pass against the genuine reference patch is necessary and nearly sufficient. It establishes solvable and caused-by-the-fix. What it does *not* establish is oracle strength: that the test fails for the reason capsule intends and passes for the intended reason too. The cheapest closure is the structural `<failure>`/`<error>` split above — that distinguishes "asserted and was wrong" from "didn't run," which is where fail-to-pass is least informative. Beyond that we accept residual oracle weakness and surface it as a per-corpus composition label rather than a per-capsule gate. Anything stricter (mutation survival, behavior-coverage probes) is diagnostic, not gate — consistent with round 1.

Q3: Yes. `pytest.raises` not raising, `pytest.warns` not warning, and `pytest.fail()` all assert an expectation about program behavior, and pytest emits them as `<failure>` in JUnit XML. That is the failure class being labeled sanctions-worthy-by-our-ability-to-parse-exception-names-against, not any authentic property of the oracle. It is library-independent — every pytest project emits it. Treating it as not-an-assertion was a classifier bug.

Q4: Include failure-run tests; gate on ran-and-asserted broadly; label composition and report it. This batch caps at a 9.1% conversion rate; at 30 tasks/trial × 5 trials with MDE ~12.5 points, every capsule has real statistical value. The experiment should take all admissible capsules (ran-and-asserted), report the labeled mix (bug-fix vs feature vs refactor-attributed by commit message and most frequent failure kind), and verify the three tiers landed on comparable mixtures. If tiers vary in composition, a stratified analysis (cost-per-solved within each stratum and overall) is more honest than a bug-fix-only subset — bug-fix-only would let model-tier performance regress to "wins on the easy taxonomic stratum." The failure kind stays a recorded covariate and a candidate stratifier.

Q5: Two amendments. First, keep the one authored alternate implementation at capsule creation, but scope its authoring to the *new* narrow gate — anything that ran and asserted. It's a guard against the unauthorial test solving itself by reasserting, and execution-loss narrowed neither weakens nor strengthens it; execution-less confused-corecapsule is orthogonal. Second — and new — fix the per-tier audit to not only hold the tier-rejection fraction but also the failure-kind label by tier. The conditional trigger should compare labeled failure-kind distribution across tiers, not just counts. If one tier systematically selects tests with weaker oracles (e.g., library-idiom-heavy DID-NOT-RAISE tests that some models pattern-match cheaply), that is the confound the audit needs to catch; raw rejection counts would mask it.

STRONGEST OBJECTION TO MY OWN POSITION: Oracle strength is real and failure kind might be the only cheap proxy for it. A `DID NOT RAISE ValueError` assertion can pass after a model adds any `raise ValueError` anywhere upstream — even in unrelated code paths — without the model fixing the intended behavior. Fail-to-pass proves the test is solvable, not that the test discriminates correct fixes from plausible incorrect ones. Relabeling and discarding the gate removes a guard that, on N=21, is invisible but may matter at scale when models learn to satisfy weak oracles cheaply. The "label stratifier" response assumes we'll analyze by label; if models exploit weak oracles uniformly across the labels we record, the stratifier won't catch it.

WHAT WOULD CHANGE MY MIND: A second batch (N ≥ 50, multi-project) showing the narrow `<error>`-only gate admits capsules whose pass-after-fix is reproducible by patches that do *not* implement the intended behavior — e.g., an alternate patch that satisfies the oracle without addressing the commit's stated purpose succeeds on a meaningful fraction (≥15%) of admissible capsules. That would be direct evidence that fail-to-pass is not oracle-strength-sufficient and that the discarded gate (or a better one) buys real discrimination.

CONFIDENCE: medium. The argument from execution semantics is tight and the batch evidence is concrete, but N=21 is small, one project is one project, and pydantic's high-assertion-density codebase may not generalize. The structural-gate narrowing depends on pytest's own semantics holding across the next several projects, which is reasonable but not yet shown.
