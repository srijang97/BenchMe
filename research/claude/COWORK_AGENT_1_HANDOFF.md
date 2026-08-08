# CoWork Agent 1 — Session Handoff

**Agent**: `cowork agent 1` · **Model**: `claude-opus-5` · **Date**: 2026-08-08
**Purpose**: complete transfer of context, decisions and build queue to the next agent
(expected: Claude Code, starting implementation).

> **Read order for a new agent**: `docs/AGENTS_LOG.md` → this file → `docs/PROJECT_KNOWLEDGE_BASE.md`
> → `docs/DEMO_01_CODEX_ITS_DANGEROUS.md` → `research/claude/benchmark_methodology_report.html`.
> Do **not** start by reading `research/00`–`11`; that corpus is superseded in several places and
> its caution list is long. Use it for competitor names and the task taxonomy only.

---

## 0. The 60-second version

The project has excellent **doctrine** and almost no **evidence**. Three research passes have
produced conviction without a single external data point. The binding constraint is not strategy,
it is that `demo/` contains one hand-authored capsule, one adapter, and n=1 trials.

The thesis survives contact with the 2026 literature and got stronger in one specific way:
**harness rankings are not transitive across task suites** (OpenClaw ranks 1st of 5 on
Claw-SWE-Bench and last of 6 on Harness-Bench). If a harness ranking does not transfer between two
*public* benchmarks, no public benchmark can tell a team what to run on their repository. That is
the product thesis, now third-party evidenced rather than asserted.

The cost objection that appeared fatal is not fatal — prior estimates were ~10–20× too high because
they ignored prompt caching.

**Next action is code, not documents.** Build queue in §9.

---

## 1. What this project is

**Positioning**: verification / CI for the agent stack. A private, execution-verified,
mutation-hardened regression suite that runs inside the customer's existing CI and gates changes to
their agent configuration.

Never call it benchmarking externally. The word choice determines the budget line: benchmarking
bills against a discretionary research budget, CI bills against developer platform infrastructure
that already exists.

**The scored unit** is the full configuration tuple, never the model:

```
f(task, repo state, model, harness, prompt, context, tools, permissions,
  budget, environment, verifier, trial)
```

The immutable run manifest hash is the join key. This is already correct in
`PROJECT_KNOWLEDGE_BASE.md` and should not be changed.

---

## 2. Dead — do not build, do not pitch

| Item | Why |
|---|---|
| **Routing, in every form** | Commoditised to free (Cloudflare, Vercel, Bedrock, LiteLLM). Unify AI pivoted off it; Not Diamond retreated to a niche on $2.3 M; all pure-routing startups combined raised <$45 M. Empirically broken for agentic coding: ACRouter hits 62.50% against a 75.89% oracle. Includes "policy artifacts via LiteLLM/Portkey" — that is still routing. |
| **Procurement intelligence** | Wrong buyer. 78% of FinOps-for-AI reports to CTO/CIO, 8% to CFO. Cheque too small. |
| **Public leaderboard as a product** | LMArena raised $150 M; Artificial Analysis is free. Viable as a *marketing channel* only, and only after the private product works. |
| **Compliance / EU AI Act positioning** | High-risk obligations deferred to Dec 2027; coding assistants likely outside Annex III. |
| **Standalone observability dashboard** | Owned by DX / Jellyfish / Faros. |
| **Bake-off orchestrator** (worktree, best-of-n) | Commoditised in real time by Cursor, Conductor, Emdash, Claude Squad. |
| **Control plane** | 3–5 year story, not a build target. |
| **Learned surrogate environments** (SWE-World style) | Fidelity vs real execution unpublished. A gameable reward model is a reward-hacking surface — unacceptable in a product whose whole claim is verification. |
| **Bug injection for the decision set** | Fine for volume, wrong for decisions. DeepSWE reported SWE-smith data gave "limited improvement" for RL; SWE-Playground reports poor out-of-domain transfer. |

---

## 3. The wedge decision

**Chosen: the verified wedge — agent config regression on execution-verified tasks.**
**Rejected: the judged wedge — AI code-review quality (DashBench replica).**

Reasoning, so the next agent can re-litigate if new evidence arrives:

- The code-review wedge is faster to value (no environment construction, free historical labels from
  reverts/hotfixes, and essentially no AI reviewer knows its own false-negative rate).
- **But it is LLM-judged**, which contradicts the project's own doctrine and removes the one thing
  that differentiates it from Sigmabench and Stet.
- It also defers building the hermetic task corpus, which is the durable asset and the only thing
  that keeps the RL-environment adjacency open.
- `demo/` is already execution-verified. Abandoning that to chase a wedge DoorDash published for
  free is a bad trade.

**Positioning nuance that matters**: sell config regression as a **guardrail**, not an optimiser.
You can reliably detect a harness swap or model change (18–27 pp effects). You cannot reliably
detect a 2 pp prompt improvement without ~9 repeats per task, which no customer will fund weekly.
"Did we break anything" sells; "did we improve" does not survive the statistics.

---

## 4. Target segment — reranked

Ranked by (unmeasured variance) ÷ (access friction). This is a change from all prior research,
which targeted the enterprise monorepo.

| Rank | Segment | Why |
|---|---|---|
| **1** | **Cost-aware / gateway-instrumented orgs** (OpenRouter, LiteLLM, opencode, custom harness) | Already accept the premise — no education needed. **They have a gateway, so the spend↔outcome join key already exists**, which removes the objection that most coding spend bypasses gateways. Highest unmeasured variance: harness sensitivity is 27.4 pp on weak models vs 10.3 pp on strong ones, so the orgs routing to cheap models are exactly the ones where harness choice matters most and are least likely to have measured it. Their gateway shows cost per *token* falling while cost per *solved task* may be rising — structurally invisible to them. |
| **2** | **Harness / agent-tool vendors** (Cline, opencode, Roo, Aider, Factory, Augment) | Ship weekly and cannot tell if a release helped. The longitudinal study is damning: 35 sequential Qwen Code CLI releases, fixed model, 50 tasks → no significant resolve-rate gain, and later releases nearly *doubled* token and tool use. Acute pain, real budget, no security review, sales cycle is a DM. Caveats: dents neutrality if public; they are also future competitors. |
| **3** | **Regulated / on-prem** (Mistral on-prem: Abanca, SNCF 4,000 devs, Capgemini 1,500+) | Constrained to open weights, so harness and config are the *only* levers — exactly what is measured and exactly what no public benchmark covers. **Quantisation is a completely unmeasured axis** (GPTQ / AWQ / FP8 / BF16 × vLLM / TGI / SGLang) and it changes tool-call formatting fidelity, worth up to 54 pp. Highest ACV, slowest cycle. Also a publishable paper. |
| **4** | Enterprise monorepo (500–2,000 eng) | Was the target in all prior research. Worst access friction: security review, environment construction, procurement. Same pain, more obstacles. |
| 5 | Migration / modernisation projects | Best adjacent expansion. **The oracle is free and perfect**: behavioural equivalence against the legacy system via differential testing. Big budgets, high risk, agent-heavy. Not in any prior research. |
| — | Tab-completion-only orgs | **Do not build for them.** Different problem: model × context-assembly × latency budget, where p95 latency dominates correctness. Funnel only — the session-log diagnostic works on them today, and they will make their first agent-config decision within 12 months. |

**Other adjacencies worth remembering**: infrastructure-as-code (`terraform plan` diff is a free
deterministic oracle; 76% of devs won't let AI touch deployment), agent-generated tests (oracle =
mutation score of the generated tests — same machinery, elegant recursion), AppSec (different and
larger budget; Apiiro 10× findings, Veracode flat at 55% secure).

---

## 5. Cost model — findings

Full model at `research/claude/cost_model/costmodel.py`. Rates verified 2026-08-04. Re-run with
`python3 costmodel.py`; update the `RATES` dict when prices move.

**Anchored on real telemetry** from `demo/runs/20260709T224810Z/` — this is why it is trustworthy.

### The correction

The teardown's §VIII estimated $6–12 k per sweep and $300–600 k/yr of compute for one customer, and
concluded "that is not a SaaS gross margin, that is a hosting business." **That is the worst case
presented as the base case.** It priced all input tokens at list rate.

In an agentic loop each turn resends the accumulated conversation, so ~85% of billed input tokens
are cache reads at ~10% of list price. Caching is a **3.4× lever**.

| Scenario | Cost |
|---|---|
| Nightly smoke — 20 tasks × 1 config × k=1 | **$9** |
| Weekly config A/B — 60 × 2 × k=3 | **$227** |
| Pilot bake-off — 30 × 4 × k=5 | **$292** |
| Release gate + sequential stopping — 200 × 6 × k=5 | **$2,433** |
| Full release gate — 200 × 6 × k=5 | **$4,865** |
| **Enterprise customer, all-in, per year** | **~$93,000** |
| Worst case (no caching, heavy harness, hard tasks) | $110 k/gate, $879 k/yr |

Cache sensitivity on the full sweep: 0% → $16,645 · 50% → $9,716 · **85% → $4,865** · 92% → $3,895.

### Findings that change decisions

1. **Cheap models are a false economy for eval workloads.** Claude Haiku 4.5 costs **$2.15 per
   solved task**, more than GPT-5.6 Sol at $2.10, because it burns 2.1× the tokens and solves 33% vs
   60%. Measured directly in `demo/`: `gpt-5.4-mini` used 2.12× the input and 2.88× the output of
   `gpt-5.4` on the identical task. Run the eval fleet on Sonnet / GPT-5.4 / DeepSeek-class, not
   Haiku / mini-class.
2. **Non-API compute is ~2% of total** (~$0.017/trajectory; $100 against $4,865 on the big sweep).
   So "run in the customer's cloud" is *not* about container savings — it is about the **API spend
   landing on their existing model contracts and volume discounts**. Frame it that way.
3. **Build-side cost is trivial: ~$91** to mine and mutation-harden a complete 200-task suite
   (mining $26, LLM semantic mutants $17, mutant test execution $48). The expensive part is
   *running* the suite, not *building* it. The durable asset is nearly free to create.
4. **Harness choice is a 4× cost lever** — $0.58 to $2.31 per solved task for the same model across
   harnesses. Larger than the Sonnet-to-Opus gap. Your first customer finding will probably be about
   their harness, not their model.

**Validation**: modelled figures run 1.5–2× above Databricks' published $1.28–1.94/task, so treat
outputs as an upper bound. Cross-checks in `results.json` → `D2_databricks_check`.

**Biggest remaining assumption**: the 85% cache hit rate is *assumed, not measured*. Both Codex and
Claude Code report cached input tokens in their JSONL traces. One afternoon of work replaces it with
a measurement. **This is build task #5.**

---

## 6. Statistics — what is defensible

The doctrine in `PROJECT_KNOWLEDGE_BASE.md` (paired design, McNemar, hierarchical logit, 15–30 tasks
× 3–5 trials) is **correct and now evidenced**. The evidence did not exist when it was written.

**arXiv 2602.07150** — 60,000 trajectories, 10 runs × 6 configs × 500 tasks × 2 temperatures:

| Finding | Value |
|---|---|
| Single-run pass@1 range across 10 runs | **2.2–6.0 pp** |
| Typical σ | ±1.0–1.8 pp |
| Variance at temperature 0 | **persists** — one config was *worse* at T=0 |
| Median first-token divergence | position 5 (0.5% into the trajectory) |
| Runs to detect +1 pp at 80% power | **36** |
| Runs to detect +2 pp | **~9** |
| Runs to detect +5 pp | 1–2 |
| pass@5 vs pass^5 gap | 14.4–37 pp |

**Practical rules**
- MDE for a paired design ≈ `sqrt(7.84 × p_d / n)` with `p_d ≈ 0.30`, `n = tasks × k`.
  30 tasks × k=5 → **≈ 12.5 pp**. 200 × k=5 → ≈ 5 pp.
- **Print the MDE on every report.** Anything below it is reported as `indistinguishable`, never as
  a ranking. This is a feature: it stops customers churning their stack on noise.
- 12.5 pp is *adequate* — the effects that matter (27 pp harness swings, 34% cost deltas, 11.6 pp
  recall gains) are all detectable at 30 tasks. What is not detectable is two frontier models 3 pp
  apart, where "indistinguishable, choose on price" is the correct answer anyway.
- This **dissolves the yield contradiction** in the earlier research. You do not need 200 capsules
  per repo. You need honesty about what 30 buys.
- Report **pass^k alongside pass@k**. The gap is the reliability number and nobody publishes it.
- Report **cost per *solved* task**, median and p95 — not mean. Failed runs burn 4–5× the tokens of
  successes (SWE-Effi: 8.8 M vs 1.8 M).
- Multiple comparisons: 8 configs pairwise = 28 tests; ~1.4 spurious winners at p<0.05. Correct
  (Holm) or publish ranked intervals instead of declaring winners.

---

## 7. Methodology — adopt / adapt / reject

Full analysis with sources: `research/claude/benchmark_methodology_report.html`.
The 2026-07-10 dossier is strong on doctrine and missed three literatures: the RL
environment-synthesis lineage, the 2026 harness-control studies, and oracle red-teaming.

> **Naming collision, flagged by the founder**: there are two DeepSWEs.
> **DeepSWE-Preview** (Agentica + Together, Jul 2025) is a 32 B RL-trained *agent*.
> **DeepSWE the benchmark** (arXiv 2607.07946, Jul 2026) is a 113-task, 91-repo, 5-language
> evaluation with hand-written **implementation-agnostic verifiers** — 1.4% disagreement with
> independent evaluators vs 32.4% for a competitor. The second is the relevant one.

### Adopt now

| Technique | Source | Why |
|---|---|---|
| **Two-container grading boundary** | project doctrine | Agent runs in container A with no test access; extract only the patch; grade in fresh container B. Current setup keeps private tests "outside the git root", which the project's own docs concede is not a boundary. **Smallest change, largest correctness gain.** |
| **Mutation hardening** | STING, arXiv 2604.01518 | 32 operator-based rules across 7 categories + LLM semantic mutants + **12 behaviour-preserving transformations as an anti-overfitting gate**. 77.0% of SWE-bench Verified instances admit a surviving wrong patch. Coverage 40.8→51.6%, assertions 2.31→5.18/test. Killed 329 patches across 10 leading agents. |
| **Exit-code sentinel** | SWE-Factory, arXiv 2506.10954 | Append a command emitting `EXIT_CODE=<v>` instead of writing a log parser per test framework. **100% accuracy over 2,085 logs.** Deletes a whole class of adapter maintenance. |
| **error2pass check** | SWE-Factory | Assert the pre-patch failure is an *assertion* failure, not an import / collection / syntax error. These look like valid F2P pairs and are not. |
| **Differential testing** | PatchDiff, arXiv 2503.15223 (ICSE 26) | 7.8% of "correct" patches fail the full suite; 29.6% diverge behaviourally; **46.8% of divergences are legitimate alternative implementations.** Separates wrong from merely different. |
| **Repo-quarter env profiles** | SWE-Next, arXiv 2603.20691 | Reuse one dependency environment per `repo_{year}Q{quarter}` instead of per commit. **639 GB vs 30.8 TB naive — 48× reduction.** Makes local-first credible on a laptop. |
| **Implementation-agnostic verifiers** | DeepSWE benchmark, arXiv 2607.07946 | Verify behavioural contracts, not implementation shape. **`demo/tasks/fallback-salts/` already does this** with its 9-point contract. Say so publicly. |
| **BenchJack red-team loop** | arXiv 2605.12673 | 8 flaw classes; near-perfect scores on 9 of 10 benchmarks *without solving any task*; 219 flaws. Iterative hardening drove hackable ratio ~100% → <10%. Run to convergence, not once. |
| **SpecBench visible−hidden gap** | arXiv 2605.21384 | Reward-hacking proxy; 90th-percentile gap grows ~27 pp per 10× code size. Cheap and legible. |
| **mini-SWE-agent as control arm** | github.com/SWE-agent/mini-swe-agent | ~100 lines, bash only, >74% on SWE-bench Verified. Include in every harness grid as the scaffolding floor. |

### Adopt at design-partner stage

- **Inspect AI agent bridge** (`sandbox_agent_bridge()`, proxy on `localhost:13131`) — intercepts
  the agent's native API calls and reroutes them, so you can point an **unmodified Claude Code at an
  arbitrary model**. Two families of harness standardisation exist and the dossier only considered
  one: container-boundary (Harbor, HAL, Claw's 5-method adapter) gives clean *harness*-axis control;
  API interception gives clean *model*-axis control. **A rigorous grid needs both.** Epoch AI already
  runs Claude Code and Codex this way via `inspect-swe`. Highest-value architectural change available.
- **Suite composition reporting** — task family × risk class × difficulty × oracle strength ×
  file-count distribution. Pre-empts the representativeness objection and turns it into a finding:
  *"your suite has 47 bug-fix capsules and zero migration capsules, so it cannot tell you anything
  about last quarter's work."*
- **The 2.2%-yield qualification test** — count candidate commit pairs before requesting access.

### Reject / defer

Learned surrogate environments; bug injection for the decision set; generated-from-scratch projects;
mutation score as a *headline* product metric (see §10).

---

## 8. Task mining architecture

Designed in-session. Principle: **automate the evidence, not the decision.** The human's job goes
from "construct a task" (hours) to "accept or reject a scored candidate" (seconds).

### The funnel — cheapest filter first

```
Stage 0  ENUMERATE            free, seconds
         git log walk. Human-authored only (exclude bot/AI commits — training on agent
         output to evaluate agents is circular). Touches test files. Bounded file count.
         Not a merge. Postdates model cutoffs.

Stage 1  STRUCTURAL SCORE     free, no execution        kills ~80%
         diff shape · test:source line ratio · path-based risk class (auth/**, payments/**,
         migrations/**, *.tf) · CODEOWNERS + bus factor · commit-message intent ·
         HISTORY SIGNALS: reverted? hotfixed within 48h? incident-linked?
         ^ highest-value label, free to compute, called "underexploited" in research/05

Stage 2  EXECUTION VALIDATION  compute-cheap             THE 2.2% GATE
         Run suite at N-1 and N. Keep only strict test improvement, zero regressions.
         Expected losses (SWE-Next): 74.5% unchanged test behaviour, 20.8% test-execution
         failure, 2.5% setup failure.
         NOTE: expensive in wall-clock, trivial in dollars. Run on everything clearing stage 1.

Stage 3  ORACLE STRENGTH       ~$0.01/candidate
         Operator-based mutants (free, AST) + LLM semantic mutants. Mutation survival rate
         becomes the primary ranking signal.

Stage 4  DISCRIMINATION SCREEN  ~$900 for 200 candidates  ← the good idea
         Run a cheap model and a frontier model on each survivor, k=2 each.
         Keep candidates where they DIFFER.
         Rationale: a task everything solves and a task nothing solves both contribute zero
         information. This is Stet's bimodality problem, solved empirically.
         CAVEAT: with outcome consistency ~0.74, "two models disagree" and "one model
         disagrees with itself" are confusable. k=2 minimum. Re-screen quarterly as
         models converge.

Stage 5  HUMAN TRIAGE QUEUE
         Three bands (below).
```

### Three-band triage with a calibrated threshold

- **Auto-accept** (above threshold) — taken without review
- **Triage band** (uncertain) — human reviews; **this is where calibration data comes from**
- **Auto-reject** — discarded, reason logged

**Calibrate, don't guess.** Hand-triage a sample, compare against the automated ranking, compute
agreement. That yields an empirical threshold and a defensible claim: *"auto-accept runs at 94%
agreement with expert review on your repository."* Same pattern DashBench used to calibrate its
judge. As agreement improves the triage band narrows and the system gets cheaper to operate — which
is what the ≤2-engineer-day onboarding gate needs.

**Sample the boundary, not the extremes.** Reviewing candidates the scorer is confident about
teaches nothing. Active-learning: maximum information sits near the decision boundary.

### Two hazards

1. **Ranking biases the corpus, and the bias is the falsification risk.** Score for "small diff,
   test-rich, clean flip" and you build a suite of small easy tasks — exactly the representativeness
   failure in the project's own kill criteria. **Stratify before you rank**: sample within
   task-family × risk-class × size-bucket, then rank *within* stratum. Never take the global top N.
   (Sigmabench does this: per-language × size cells, commits split across small/medium/large.)
2. **The founder is the wrong triager for a customer's repo.** Fine on public repos. On their
   payments service, their engineers' judgement beats his. **Design the queue for a stranger from
   day one** — legible to someone who knows the codebase but not the methodology. This is also the
   margin-preserving design: they curate, the software validates, you never see the code.

### UI scope

Build a **triage queue**, not a capsule editor. Diff left, F2P tests, oracle-strength score,
accept/reject/flag on keyboard shortcuts. ~3 days, not ~3 weeks. Attacks the ">1 engineer-day per
capsule" pivot criterion directly — the bottleneck is *rejecting*, not authoring.

**If editing is ever allowed**: it must re-run validation and mint a new version, never mutate in
place. A user who widens `allowed_change_globs` or softens a spec silently destroys the capsule
while it still looks fine. Demo 01 v1→v2 is this failure in miniature.

### Open-core split

Open source: capsule format, miner, validator, hardener, triage queue, adapter conformance tests,
local runner core, failure-taxonomy spec.
Commercial: config grid, statistics engine, cross-customer priors, reporting, continuous
recalibration.

Rationale: Prime Intellect's Environments Hub, HUD and `verifiers` are all *distribution* layers for
human-authored environments — **none of them generates or validates**. Mechanize ($9.1 M) and
Datacurve ($17.7 M) raised to build verified environments largely by hand. The capsule factory is
plausibly a stronger open-source artifact than the enterprise product is a company.

---

## 9. Build queue

Ordered. Each item has an acceptance criterion. Do not proceed past a failed gate.

| # | Task | Acceptance criterion |
|---|---|---|
| **1** | **Two-container grading boundary** | Agent container demonstrably cannot read hidden tests or the reference patch (preflight probe fails closed). Only the candidate diff crosses. Replay in a clean checkout reproduces the verdict. |
| **2** | **Mutation-hardening layer over `fallback-salts`** | Produces a mutation survival rate for the existing capsule. STING method: 32 operator rules + LLM semantic mutants + 12 behaviour-preserving transformations as the anti-overfitting gate. **This is the artifact that turns the v1 finding from anecdote into metric.** |
| **3** | **Second adapter — Claude Code** | Both adapters complete the same 10-task conformance suite (trivial edit, new file, run test, forced timeout, denied path, denied network, provider error, no-patch completion, malformed event stream, patch replay) without manual repair. |
| **4** | **Miner stages 0–2 + bare triage queue** | ≥8 valid capsules from one public repo at <1 engineer-day median curation. Report candidates enumerated, survived each stage, and rejection reasons. |
| **5** | **Cache-hit-rate instrumentation** | Parse `~/.claude/projects/**` and Codex JSONL for cached vs uncached input tokens. Replaces the largest assumption in the cost model. **One afternoon.** |
| **6** | **k=5 repeated trials** | First real variance number on an owned capsule. Compare against the published 2.2–6.0 pp range. |
| **7** | **The routing-counterfactual experiment** | 2–3 OSS repos, 30 mined tasks, cost-optimised config vs frontier config, k=5. Compute cost per *solved* task both ways. ~$150. **Either the inversion reproduces or the whole cost-aware wedge dies for $150.** |
| **8** | **Publish** | "How a green benchmark was wrong." Content already exists in `docs/DEMO_01_CODEX_ITS_DANGEROUS.md` §6. Not a model leaderboard — the methodology finding. |

Items 1–3 close the project's own stated technical gates. Item 7 is the highest
information-per-dollar experiment available and should not wait for 1–6 to be perfect.

---

## 10. Open questions and contested claims

**Unresolved, needs work**

1. **Is mutation survival a valid ranking signal here?** ISSTA 2026 (arXiv 2607.22880) finds
   coverage and mutation scores are reliable in the *regression* setting but **not** when the goal
   is exposing defects in buggy code. BenchMe's use sits between. Validate on own capsules before
   making it the headline number; report alongside alternate-solution acceptance, never alone.
2. **The "refuse the LLM judge" doctrine has a counter-example.** EvilGenie (arXiv 2511.21654)
   found held-out unit tests gave only *minimal* improvement over other reward-hack detectors, while
   an LLM judge was highly effective on unambiguous cases. Stet's Equivalence metric — an LLM judge —
   surfaces 50 pp gaps between models with *identical pass rates*. **Reposition rather than defend**:
   execution is primary for correctness; a grounded, calibrated judge is primary for what execution
   cannot see (scope, compatibility, maintainability, is-this-a-hack). Factory's report-grounding
   technique took judge variance 7% → 0.6% — that is the stabilisation mechanism.
3. **Strict vs weak tests cannot both be fixed by the same method.** OpenAI found ≥59.4% of audited
   SWE-bench problems have flawed tests — **35.5% narrow** (too strict, rejecting correct
   submissions). STING found **77% too weak**. Hardening to kill mutants makes tests *stricter*,
   which manufactures the exact defect OpenAI deprecated SWE-bench for. **Never harden without
   running the alternate-solution positive control afterwards.**
4. **Real yield and curation cost on a repo the author does not control.** Pivot criterion is <8
   valid tasks or >1 engineer-day per task. Currently n=1 capsule, hand-authored, own choice of repo.

**Unpublished numbers that would change decisions if found**

- R2E-Gym's stage-by-stage yield and pipeline cost (genuinely not published; its Docker build
  scripts still rely on semi-manual dependency-pin searching — the un-automated bottleneck).
- SWE-World's fidelity vs real Docker execution.
- SWE-Hub (Baidu) publishes a full production architecture with zero yields, counts or costs.
- **No vendor in this space publishes list pricing.** Sigmabench, Stet, RepoGauge, Factory, Vals AI,
  Agent CI — all demo-gated. There is no competitor pricing anchor.

---

## 11. Competitive position — refreshed 2026-08-08

| Player | Oracle | Note |
|---|---|---|
| **Sigmabench** | **File-level Jaccard index vs golden diff** | Weakest oracle in the field — measures diff similarity, does not run tests. Its own methodology page says private repos are unsupported while the company page markets them. **Attack this directly.** |
| **Stet** | Human PR's tests as gate + LLM equivalence above it | Closest shape to this project. Sharp observation: PR tasks are **bimodal**, so pass rate alone does not discriminate. No pricing, founders or entity disclosed. |
| **RepoGauge** | Gold-patch validation + pass rate | Open source, single maintainer, hosted platform not shipped. Closest OSS competitor. Has a router-training stage. |
| **Proximal** | Researching **"fuzzy verifiers"** + reward-hack detection | **Most direct threat.** Founded 2026, ex-Prime Intellect / Cursor / Jane Street, ~25 people, seed led by Scribble Ventures. Same technical thesis, funded. |
| **Agent CI** | Bundled eval framework | Literally "CI for agents" — has the positioning and the name. Waitlist only, no entity or funding disclosed. |
| **Factory Agent Readiness** | **None — never runs an agent** | Scores whether a repo *supports* agents. Different category. Steal their report-grounding variance technique. |
| **Brokk** | Tests + build failures | 93 tasks, claims ">90% pass rate, coding is solved" — i.e. saturated and non-discriminative. Not a private-repo product. |
| **Sourcegraph CodeScaleBench** | Patch verification **+ answer.json artifact comparison** | Vendor A/B for their own MCP tools, but the two-mode oracle is novel — copy it for non-patch task families. |
| **Mechanize / Datacurve** | Execution verifiers | $9.1 M / $17.7 M. Selling to labs. The RL-environment adjacency, already funded. |
| **DX / Jellyfish / Faros / Swarmia / LinearB** | **None — no counterfactual** | Still telemetry-only as of Aug 2026. They measure what happened; only an eval measures what would have happened. **Watch DX's unspecified "Agent Ops Tools".** |
| ~~codeprobe~~ | — | **Could not be verified to exist.** Remove from the competitive set. |

---

## 12. Constraints affecting prioritisation

- **Solo maintainer.** Any plan requiring parallel consulting, an OSS CLI across two ecosystems,
  SOC 2 and a GitHub App is a four-person plan. Cut ruthlessly.
- **~16-week window**, with industry re-entry running in parallel from about week 4.
- **The artifact serves both goals.** A working, execution-verified, mutation-hardened harness with
  a real published finding is simultaneously the MVP, the portfolio piece and the interview hook.
  This is why item #2 in the build queue matters more than its size suggests.
- **Do not raise now.** Solo, pre-traction, in a category with funded entrants — a raise is a 6–9
  month process funded by runway that does not exist. Revisit at month 6+ with design-partner
  evidence or not at all.
- **IP hazard, decide before signing anything**: joining an eval company (Braintrust, Snorkel,
  Scale, Galileo, Proximal) puts this squarely in their field of business and standard assignment
  clauses will likely swallow it. A **platform / DevEx team at a large engineering org** keeps the
  idea clear, makes the founder his own buyer, and gives inside validation. Get any clause reviewed.

---

## 13. Reference card — numbers worth memorising

```
ORACLE WEAKNESS
  77.0%   SWE-bench Verified instances admitting a surviving wrong patch     STING
  59.4%   audited SWE-bench problems with flawed tests (35.5% too narrow)    OpenAI
   7.8%   "correct" patches failing the full developer suite                 PatchDiff
  46.8%   behavioural divergences that are legitimate alternatives           PatchDiff
  9/10    benchmarks scored near-perfectly without solving any task          BenchJack
  28/89   Terminal-Bench 2.0 tasks patched in 2.1 → +12.1 pp on same config

HARNESS EFFECTS
  54.3pp  adapter/output-contract design, model+harness fixed                Claw-SWE
  29.4pp  model spread, harness fixed                                        Claw-SWE
  27.4pp  harness spread on a WEAK model (Qwen 3.6-flash)                    Claw-SWE
  10.3pp  harness spread on a STRONG model (GLM 5.1)                         Claw-SWE
  23.8pp  harness spread, model averaged out, 5194 trajectories              Harness-Bench
  ~2x     cost difference for one model across harnesses                     Databricks
  NON-TRANSITIVE: OpenClaw ranks 1st of 5 on one suite, last of 6 on another

NOISE FLOOR
  2.2-6.0pp  single-run pass@1 range across 10 runs                          arXiv 2602.07150
  36 / 9 / 1-2  runs needed to detect +1 / +2 / +5 pp at 80% power
  0.74    outcome consistency — 1 in 4 "solved" tasks fails on rerun
  variance PERSISTS at temperature 0

YIELD & ENVIRONMENT
   2.2%   valid instances from raw commit pairs (2,308 / 102,582)            SWE-Next
  74.5%   candidates lost to "unchanged test behaviour"                      SWE-Next
   48x    storage reduction from repo-quarter env profiles (639GB vs 30.8TB) SWE-Next
   6.69%  Python repos auto-configured by best LLM agent                     EnvBench
  33-40%  valid instances at $0.024-0.045 each                               SWE-Factory
   100%   exit-code sentinel accuracy over 2,085 test logs                   SWE-Factory

COST (this project's model, rates 2026-08-04)
    $9    nightly smoke  ·  $227 weekly config A/B  ·  $292 pilot bake-off
  $4,865  full release gate (200 x 6 x k=5)  ·  $2,433 with sequential stopping
   ~$93k  enterprise customer, per year, all-in
     $91  to mine + mutation-harden a complete 200-task suite
    3.4x  prompt caching lever  ·  4x harness cost lever  ·  ~2% infra share of COGS
  12.5pp  MDE at 30 tasks x k=5     5pp MDE at 200 tasks x k=5
```

---

*End of handoff. Append to `docs/AGENTS_LOG.md` when you finish your session.*
