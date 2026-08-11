<!-- Paste this whole file into GPT-5.6 Sol. It contains the motion followed by the shared facts document. Answer in the required output format at the end of the motion section. -->

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
# How current benchmarks mine tasks and build capsules — the facts

> **Purpose**: shared factual input for council round 1. Not analysis, not a
> recommendation — the state of the art as documented, in plain language, so
> several models can reason from the same base.
>
> **Sourcing**: every figure below comes from BenchMe's own research corpus
> (`benchme_coding_benchmarks_research_2026-07-10/`, `research/claude/benchmark_methodology_report.html`).
> Those references postdate the assistant's training data, so nothing here is
> recalled from memory — where the corpus does not state a number, this report
> says so rather than guessing.
>
> **Justification for a document** (per `AGENTS_LOG.md` standing rule 1): this is a
> distillation of existing corpus material into council input, not new research.

---

## 1. The basic recipe everyone starts from

Almost every modern coding benchmark is built the same way, and it is worth
stating in one paragraph because everything else is a variation on it.

You take a real code repository. You look through its history for a commit
where somebody fixed a bug or added a feature **and changed the tests at the
same time**. You rewind the repository to just before that commit. You run the
tests — the new ones should fail, because the fix isn't there yet. Then you
apply the real fix and run again — now they should pass, and nothing that
previously worked should break. If all of that holds, you have a task: the
repository at the earlier state, a description of what to do, and a set of
tests that decide whether it was done.

The tests that go from failing to passing are called **fail-to-pass** (F2P).
The tests that must keep passing throughout are **pass-to-pass** (P2P). Nearly
every system uses this vocabulary.

The unit you ship is usually called an *instance* or a *task*; BenchMe calls it
a **capsule** and includes more in it than most public benchmarks do —
environment reference, information policy, controls, and provenance.

---

## 2. What went wrong with that recipe

The 2025–26 audits are why nobody sensible treats "the tests pass" as the end of
the story.

**The tests are often too weak.** STING applied mutation testing to SWE-bench
Verified — deliberately introducing wrong code to see whether the tests noticed.
**77.0% of instances (385 of 500) accepted at least one wrong patch that still
passed the tests**, across 2,124 generated variants. When the ten leading repair
agents were re-scored against strengthened suites, their resolve rates dropped
by **4.2 to 9.0 percentage points**. (arXiv 2604.01518)

**The tests are also often too strict.** OpenAI's own audit found **at least
59.4% of examined problems have flawed tests** — 35.5% *narrow* (enforcing
implementation details the task never specified, so a functionally correct
answer is marked wrong) and 18.8% *wide* (checking behaviour the issue never
described). OpenAI stopped using SWE-bench Verified as a result.

These two findings pull in opposite directions and **no published method
satisfies both at once.** This is the central unresolved tension in the field.

**"Correct" patches often are not.** PatchDiff ran differential testing between
agent patches and the reference patch: **7.8% of patches marked correct fail the
full developer suite**, inflating reported scores by about 6.2 points. Of
patches that diverged behaviourally from the reference (29.6% of them),
**46.8% were legitimate alternative implementations** — different code, equally
correct. A further 27.3% were "over-adaptation" — solutions fitted to the test
rather than the problem. (arXiv 2503.15223, ICSE 2026)

**Agents look up the answer.** Cursor audited its own successful runs and found
**57% used the public web to find the actual merged fix**, and **9% recovered it
from git history bundled in the container**. Sealing future git history costs
the strongest model **8.0 points** and the weakest model almost nothing — so
leakage protection matters *more* as models improve, not less.

**Fixing the benchmark moves scores more than upgrading the model.**
Terminal-Bench repaired 28 of its 89 tasks between versions 2.0 and 2.1. On an
identical agent and model, the score moved **+12.1 points**. A hygiene patch
outperformed most model releases.

**The harness itself can be gamed.** BenchJack red-teamed ten benchmark
harnesses and achieved **near-perfect scores on nine of them without solving a
single task**, cataloguing 219 flaws across 8 classes: isolation failure, leaked
answers, remote code execution, judge prompt injection, weak string matching,
evaluation-logic gaps, trusting untrusted output, and excessive permissions.
Iterative hardening drove the hackable-task ratio from roughly 100% to under
10%. (arXiv 2605.12673)

---

## 3. The five families of task generation

Every published system falls into one of five approaches. The yields are not
comparable across families because the denominators differ — this is the most
common way these numbers get misquoted.

### Family A — Mine real history, execute both sides

The honest baseline. Walk the commit log, find candidates, actually run the
tests before and after.

**SWE-Next** is the cleanest published measurement of what this really costs.
From **102,582 candidate commit pairs it produced 2,308 valid instances — a
2.2% yield**, taking 30 hours and 639 GB. Its acceptance rule is called
"NewCommitBetter": strict test improvement with zero regressions.

The failure breakdown is the single most useful number in this report:

| Why candidates die | Share |
|---|---|
| Test behaviour unchanged between the two commits | **74.5%** |
| Test execution fails | 20.8% |
| Environment setup fails | 2.5% |
| Survive | **2.2%** |

Three quarters of real commits simply do not move the test needle. **No mining
technique fixes that** — it is a property of how people write code. It also
means investment in cleverer *candidate discovery* has a low ceiling, while
investment in cheaper *validation* has a high one.

**Denominator warning**: 2.2% is per raw commit pair. Numbers from other
families start much further down the funnel.

### Family B — Automate the environment, mine from issues

**SWE-Factory** starts from issues that already have an environment path and
uses a four-agent builder to construct the environment automatically. It reports
**33.5–40.1% valid instances at $0.024–0.045 each**. Environment setup succeeds
on **49.8–57.2% of issues** depending on which model drives the builder.

Its fail-to-pass detection runs at **92% precision and 100% recall**.

### Family C — Inject bugs into working environments

Instead of finding real bugs, break working code deliberately. **SWE-smith**
does this, with yields from **33.8% to 96.9% depending on strategy**, at **$2.32
per 1,000 instances**. Acceptance rule: the injected patch must break at least
one previously passing test. It built **128 working environments from the top
5,000 PyPI packages at roughly 7 minutes of human labour per repository**.

Cheap and scalable. But BenchMe's corpus records that DeepSWE found SWE-smith
data gave "limited improvement" for training, and SWE-Playground reports poor
out-of-domain transfer — **synthetic bugs are not real bugs**.

### Family D — Reconstruct the task description from the code change

If a commit has no usable issue text, generate one. **R2E-Gym** back-translates
an issue from the diff and auto-generates fail-to-pass tests where none exist,
reporting **2.5× more usable tasks than issue-based mining**.

The corpus flags two things: its stage-by-stage yield and pipeline cost are
**not published**, and its Docker build scripts still rely on semi-manual
dependency-pin searching — the un-automated bottleneck the whole lineage works
around.

The methodological cost is that a description written from the diff **encodes
the shape of the implementation**, which is a subtler form of the leakage that
sealing git history is meant to prevent.

### Family E — Remove implementation, keep the contract

**Commit0** deletes function bodies while retaining signatures and tests, so the
task is to reconstruct behaviour from the interface and the test suite. The
corpus rates this "a cheap capsule class" worth adopting.

**Rejected in BenchMe's own review**: SWE-Playground (generates whole projects
from scratch — 28 projects, 704 trajectories — no customer relevance) and
SWE-World (16.6K tasks across 3,763 repos with **no Docker at all**, replacing
container execution with learned transition and reward models — its fidelity
against real execution is unpublished, and a reward model that can be gamed is a
reward-hacking surface).

---

## 4. Environment reconstruction — the hard part nobody solved

Building a working environment for an arbitrary repository at an arbitrary
historical commit is the field's hardest open problem, and the numbers are
blunt.

- **EnvBench**: the best LLM-agent approach configures **6.69% of Python
  repositories and 29.47% of JVM repositories**.
- **ExecutionAgent**: 33 of 50 projects (**66%**), at **74 minutes and $0.16 per
  project**.
- **SWE-Factory**: environment setup succeeds on **49.8–57.2%** of issues.
- **Multi-SWE-bench**: 1,632 valid instances from 2,456 candidates (66%) — but
  with **68 expert human annotators**.

For scale of the operational burden: SWE-bench's own recommended local
evaluation footprint is **120 GB storage, 16 GB RAM and eight cores**.

**Storage**: SWE-Next reduced 30.8 TB to **639 GB — a 48× saving** — by mapping
commits to `repo_{year}Q{quarter}` and reusing one dependency environment per
quarter, instead of building an image per commit.

---

## 5. Mechanical techniques worth knowing

Three specific tricks recur, each solving a real recurring failure.

**The exit-code sentinel** (SWE-Factory). Rather than writing a log parser per
test framework — which breaks constantly — append a command that emits
`EXIT_CODE=<value>` and parse that. Measured at **100% accuracy across 2,085
test logs**. Removes an entire category of maintenance.

**The `error2pass` check** (SWE-Factory). Some tests fail before the patch not
because the bug exists, but because of an import error, a collection error or a
syntax error. These look exactly like valid fail-to-pass pairs and are not.
Including them deflates measured capability and inflates apparent task validity.
The fix is to assert the pre-patch failure is an **assertion** failure.

**Repo-quarter environment profiles** (SWE-Next). See §4 — the 48× storage
reduction that makes local-first evaluation feasible at all.

---

## 6. How the oracle is built and hardened

The oracle is whatever decides "solved". Public benchmarks mostly use the F2P
tests as-is. The 2026 literature is a catalogue of why that is insufficient and
what to add.

| Method | What it does | Headline finding |
|---|---|---|
| **STING** (2604.01518) | Mutation testing on the benchmark's own tests — 32 operator rules across 7 categories, plus LLM-generated semantic mutants | 77.0% of instances admit a surviving wrong patch. Augmentation moved line coverage 40.8% → 51.6% and assertions 2.31 → 5.18 per test |
| **PatchDiff** (2503.15223) | Differential testing between the agent patch and the reference | 7.8% of "correct" patches fail the full suite; 46.8% of behavioural divergences are legitimate alternatives |
| **UTBoost** (2506.09289) | LLM test augmentation, then re-score the leaderboard | 40.9% of Lite and 24.4% of Verified submissions affected; 18 and 11 rank changes |
| **BenchJack** (2605.12673) | Red-teams the harness itself | Near-perfect scores on 9 of 10 benchmarks without solving any task; 219 flaws in 8 classes |
| **SpecBench** (2605.21384) | Measures reward hacking as visible-minus-hidden pass-rate gap | The 90th-percentile gap grows about 27 points per 10× increase in code size |
| **DeepSWE benchmark** (2607.07946) | Hand-written verifiers that accept *any* implementation of the requested behaviour | **1.4% disagreement with independent evaluators, against 32.4% for a competitor benchmark** — 113 tasks, 91 repos, 5 languages |

**STING's anti-overfitting gate** is worth naming separately: after
strengthening tests, it applies **12 behaviour-preserving transformations** to
check the suite has not become sensitive to implementation shape rather than
behaviour.

### The six controls a task should carry

From the dossier's lifecycle stage 7, the minimum set:

1. **Base negative** — the target oracle fails before the fix.
2. **Reference positive** — a known-good patch passes everything.
3. **Regression** — unrelated behaviour passes before and after.
4. **No-op / near-miss** — the verifier rejects superficial compliance.
5. **Alternate-solution** — a *different* correct implementation also passes.
6. **Adversarial verifier probe** — attempts to modify tests, spoof output, or
   bypass scoring all fail.

The corpus notes that **the last two are uncommon in published benchmarks and
increasingly important**.

---

## 7. Where LLMs are used, and where they are not

This is the question the council needs answered precisely, so here is the
division as the literature actually practises it.

**Decided by execution only — no model in the loop anywhere:**

- whether the tests failed before and passed after;
- whether previously passing tests still pass;
- whether a mutant survived the suite;
- whether an alternate implementation passes;
- whether a candidate patch is correct.

**Generated by a model, then checked by execution:**

- the task description, when no usable issue text exists (R2E-Gym);
- semantic mutants that operator rules cannot produce (STING);
- augmented test assertions (UTBoost);
- environment build scripts (SWE-Factory's four-agent builder, ExecutionAgent);
- injected bugs (SWE-smith).

**Judged by a model, and contested:**

- code-review quality, maintainability, scope — things execution cannot see.

The contested case has evidence on both sides. **EvilGenie** compared three
reward-hack detectors and found held-out unit tests gave only *minimal*
improvement over alternatives, while an LLM judge was highly effective on
unambiguous cases (arXiv 2511.21654). Against that, Databricks' published
practice explicitly **refuses the LLM judge** for correctness, on the grounds
that it "rewards sounding right over being right".

BenchMe's own doctrine currently sits with Databricks — execution primary,
judge only for what execution cannot see — but the methodology review records
EvilGenie as a live counter-example rather than a settled matter.

---

## 8. Contamination — what is actually known

**You cannot prove a closed model did not train on a task.** The corpus is
firm that the honest labels are "high exposure risk" or "fresh relative to the
documented cutoff", never "uncontaminated".

What *can* be controlled is runtime retrieval, and the measured numbers are
above in §2: 57% web lookup, 9% git-history mining, 8.0 points recovered by the
strongest model when future history is reachable.

A fresh unpublished task on a public repository removes the exact historical
answer but **not** the model's familiarity with the repository, its APIs, its
architecture and its idioms. The dossier's finding 7 states this explicitly:
fresh tasks on public repos are "meaningfully better, not contamination-free".

---

## 9. What the field has not resolved

Four genuine open conflicts, all relevant to any design decision we make.

**Strict versus weak cannot be fixed by the same method.** Hardening tests to
kill mutants makes them stricter, which increases false rejection of valid
alternatives — manufacturing precisely the defect OpenAI deprecated SWE-bench
Verified for. The only published mitigation is to never harden without running
the alternate-solution control afterwards.

**Mutation score may not measure what we want.** An ISSTA 2026 replicability
study (arXiv 2607.22880) finds coverage and mutation scores give reliable
cross-model signal in the *regression* setting — where code is assumed correct —
but are **not reliable indicators when the goal is exposing defects in buggy
code**. Capsule hardening sits between the two cases.

**Whether the LLM judge belongs anywhere.** See §7.

**How many runs are enough.** One trajectory is a case study, not a ranking. The
corpus records single-run pass@1 ranging **2.2–6.0 points across ten identical
runs**, variance persisting at temperature 0, and **36 runs needed to detect a
1-point difference at 80% power** (9 runs for 2 points, 1–2 runs for 5 points).

---

## 10. What nobody publishes

Recorded as gaps rather than facts, because the absence is itself decision-relevant.

- **R2E-Gym's stage-by-stage yield and pipeline cost.**
- **SWE-World's fidelity** against real Docker execution — the one number that
  would justify or kill learned environments.
- **SWE-Hub (Baidu)** publishes a full production architecture with zero yields,
  task counts or costs.
- **Human curation cost per task**, almost everywhere. Multi-SWE-bench discloses
  68 annotators; SWE-smith discloses ~7 minutes per repository. Most disclose
  nothing, which makes the economics of curation impossible to compare.
- **Vendor pricing** across the private-benchmark category — all demo-gated.

---

## 11. The numbers in one place

| Figure | Value | Source |
|---|---|---|
| Honest yield, raw commit pairs → valid tasks | **2.2%** (2,308 / 102,582) | SWE-Next |
| Candidates lost to unchanged test behaviour | **74.5%** | SWE-Next |
| Yield from issues with automated environment build | 33.5–40.1% | SWE-Factory |
| Cost per mined instance | $0.024–0.045 | SWE-Factory |
| Bug-injection yield / cost | 33.8–96.9% / $2.32 per 1,000 | SWE-smith |
| Instances admitting a surviving wrong patch | **77.0%** | STING |
| Audited problems with flawed tests | ≥59.4% (35.5% narrow) | OpenAI |
| "Correct" patches failing the full suite | 7.8% | PatchDiff |
| Behavioural divergences that are valid alternatives | 46.8% | PatchDiff |
| Benchmarks scored near-perfectly without solving anything | 9 of 10 | BenchJack |
| Python repos auto-configured by best agent | 6.69% | EnvBench |
| Exit-code sentinel accuracy | 100% over 2,085 logs | SWE-Factory |
| Storage saving from repo-quarter profiles | 48× (639 GB vs 30.8 TB) | SWE-Next |
| Implementation-agnostic verifier disagreement | 1.4% vs 32.4% | DeepSWE |
| Successful runs that looked up the fix online | 57% | Cursor audit |
| Score movement from repairing 28 of 89 tasks | +12.1 points | Terminal-Bench 2.1 |
| Runs needed to detect +1 point at 80% power | 36 | arXiv 2602.07150 |
