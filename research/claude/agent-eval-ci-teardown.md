# Private Repo Benchmarking & Model Intelligence — Teardown, Verdict, and Rebuild

*Prepared 4 August 2026. Evidence-led. Every load-bearing claim is sourced in the appendix.*

---

## Part I — The verdict, first

There is real gold here, but it is roughly **20% of the idea as you framed it**, and it is not the part you sounded most excited about.

**What is gold:** the measurement layer. Specifically, the machinery that turns a private repository into hermetic, oracle-hardened, execution-verifiable tasks, and then runs configurations against them with enough statistical power to make a defensible decision. That machinery is genuinely hard, the research literature says so with numbers, and the most sophisticated engineering organisations on earth are currently each building a worse version of it in-house and finding non-obvious, materially valuable results when they do.

**What is dead:** routing, procurement intelligence, and "model intelligence" as a saleable output. All three are either commoditised to free, structurally owned by parties with better distribution, or empirically broken for agentic coding specifically. Attaching them to the pitch makes you sound like a cost-optimisation play in a market whose own buyers say capability beats cost.

**The reframe that makes this fundable:**

> This is not a benchmark company. It is **CI for the agents that write your code**. The product is a private, continuously-running, execution-verified regression suite that gates changes to your agent stack the same way unit tests gate changes to your code. The durable asset is the task-and-oracle factory underneath it — which has a second, possibly larger buyer in the frontier labs.

Benchmarks are reports. Reports are bought once, by a consultant, for a five-figure sum. CI is infrastructure. Infrastructure is bought forever, by a platform team, out of a budget line that already exists.

**Confidence:** high on the teardown (the negative evidence is unusually clean), moderate on the rebuild (the wedge is defensible but the "internal build" risk is real and only killable by demo).

---

## Part II — What is dead, and the evidence that kills it

### II.1 Routing is not a business, and it is empirically broken for agentic coding

Two independent lines of evidence, either of which is sufficient.

**Commercially, the layer is commoditised to zero.** Cloudflare AI Gateway gives routing, caching and rate limiting away free. Vercel AI Gateway explicitly charges "no markups." AWS Bedrock Intelligent Prompt Routing and Azure AI Foundry's model router are bundled platform primitives. LiteLLM is open source. Portkey processes 500B tokens/day and raised a $15M Series A — scale without monetisation, and its own investor describes the enterprise gateway as "available for free to drive adoption." Unify AI, a YC company founded explicitly to do benchmark-driven model arbitration, has pivoted entirely off routing into no-code agent workflows. Not Diamond, three years in, has ~$2.3M disclosed and a single-digit headcount, and has narrowed to "router for coding agents" — a general router retreating into a niche is not a growth signal.

The one apparent exception proves the rule. OpenRouter is real: ~$50M annualised as of March 2026, 100T tokens/month, $1.3B valuation led by CapitalG. But it is a ~5% take on commodity tokens at 26× revenue, and its own traffic mix is eating it: Chinese open models went 2% → 45% of traffic in a year, while **Anthropic captures 46% of platform revenue on 12% of tokens**. The premium slice that pays the bills is the slice Anthropic is actively disintermediating with direct enterprise contracts. The more successful the router, the faster it commoditises the thing it resells.

**Technically, routing does not transfer from QA to agentic coding.** RouteLLM's famous "85% cost reduction at 95% of GPT-4 quality" was measured on MT-Bench, MMLU and GSM8K — single-turn QA and maths. The 2026 paper that actually tested this on code (CodeRouterBench / ACRouter, arXiv 2606.22902) found that **static routers collapse on out-of-distribution agentic tasks**, and that even the authors' own SOTA dynamic router reaches 62.50% against a 75.89% oracle on multi-turn agentic programming. That is a router capturing ~82% of available headroom, on the researchers' own benchmark, in their own paper.

There are three structural reasons this is not a tuning problem:

1. **The routable unit is wrong.** In agentic coding the atom is a trajectory of 30–200 turns, not a prompt. Difficulty is not knowable at turn 1 — IBM Research's practitioner critique makes exactly this point: "summarize this contract" silently becomes retrieval plus tool use plus multi-round refinement.
2. **Mid-trajectory switching destroys the economics.** Prompt-cache reads are where the real cost savings live; swapping models invalidates the cache and re-pays full input cost on a context that may be 100k+ tokens. IBM's field example: Claude Sonnet ended up costing *half* of GPT-4.1 in a real deployment despite a higher headline rate, purely from cache-read dynamics that list-price routers cannot see.
3. **Cheaper models can cost more.** SWE-Effi (arXiv 2509.09853) documents the "token snowball": SWE-Agent + GPT-4o-mini scored 10% raw resolve rate but 5.1% cost-adjusted effectiveness, because failed runs burned 8.8M tokens and 658s versus 1.8M tokens for successes. Industry data corroborates: token unit prices fell 67% and 73% of companies still blew their AI budget.

And the labs are absorbing it anyway. GPT-5 shipped an internal mixture-of-models router. Claude has a model picker. Gemini has dynamic thinking budgets. Latent Space's read is the correct one: the dollar-per-intelligence frontier *is* a routing problem, which is exactly why the labs will not let a third party own it.

**Cut routing entirely.** Not "third party at start." Cut it. It converts every gateway, cloud and lab into a competitor, in exchange for a feature people give away.

### II.2 Procurement intelligence is too small a line, owned by the wrong buyer

Direct licensing is **$228–$720 per developer per year**; fully loaded TCO around **$660+**. For a 5,000-engineer enterprise that is $1.1–3.6M in licences. The entire Gartner-sized AI code-assistant market was ~$3.0–3.5B in 2025. Nobody staffs a procurement-intelligence function against that.

Worse, the buyer is wrong. 78% of FinOps-for-AI teams report to CTO/CIO and only 8% to CFO. Vendr, Tropic, Sastrify and Spendflo have all bolted "AI" onto their messaging and **none** publish model-level pricing intelligence or quality comparisons. "Procurement intelligence for AI models" is not an underserved category; it is an unvalidated one, and the reason is that the cheque is too small and the person holding it is an engineer who wants a better answer, not a better price.

### II.3 "Model intelligence" as a published output competes with free and with $150M

LMArena raised $150M at $1.7B (Jan 2026) and reportedly hit $100M ARR. Artificial Analysis is free. Epoch AI is a nonprofit. Scale has forked and commercialised the field's flagship benchmark as SWE-bench Pro with a private held-out set. Meanwhile the public benchmark itself is decaying: OpenAI formally deprecated SWE-bench Verified, disclosing that **≥59.4% of audited problems have flawed tests** and that frontier models can reproduce the ground-truth human patch verbatim.

A public leaderboard is a viable *marketing channel* — Artificial Analysis proves the distribution works. It is not a product.

### II.4 The honest counter-argument you must survive

The most sophisticated buyer I found built it themselves. Capital One's DevEx organisation — owning tooling for 14,000 engineers — runs its own evaluation loop with weekly usage reviews and monthly surveys, and deprecated a previously-championed AI tool on the strength of its own telemetry. DoorDash's DashBench is **105 test cases**. That is a two-engineer, six-week build, not a moat.

And the closest existing analogue to your idea, Vals AI, sells private benchmarks into legal/finance/healthcare and is estimated at roughly **$1.3M revenue with 12 people**. Meanwhile Thoughtworks — a firm with an SEO page implying an LLM-evaluation practice — does not actually sell evaluation as a discrete service line. No consultancy publishes a rate card for it.

Read plainly: **the enterprise-custom-benchmark motion, as currently sold, is thin.** Any version of this idea that is "we will build you a benchmark" is a $2M consultancy. You need a reason it is infrastructure instead. Part IV is that reason.

---

## Part III — The gold: one insight, well evidenced

**The unit of capability is not the model. It is the `(model × harness × config × codebase)` tuple, it is unstable over ~6-week horizons, and no public artefact can tell you its value for your repository.**

This is not a slogan; it is the consensus of the 2026 literature, and the numbers are larger than most people assume.

**Harness effects rival or exceed model effects.** Claw-SWE-Bench (arXiv 2606.12344) crossed 5 harnesses × 9 models. Varying the model with harness fixed produced a 29.4pp spread. Varying the *harness* with the model fixed produced a **27.4pp swing on Qwen-3.6-flash** (66.0% vs 38.6%) and 12.5pp on GLM-5.1. Harness-Bench (arXiv 2605.27922), 5,194 trajectories, concludes capability must be reported at the model-harness pair level and never for a model alone. Databricks measured the same thing on their own monorepo: **>2× cost difference for the same model across harnesses**, driven by one harness feeding ~3× less context per turn.

**Public benchmarks are structurally unable to answer the question.** Beyond contamination, the oracles are weak. STING (arXiv 2604.01518) applied mutation testing to SWE-bench Verified and found **77% of instances admit at least one wrong patch that still passes the tests**; re-evaluating the top ten repair agents against hardened suites dropped resolve rates by **4.2–9.0pp**. PatchDiff (ICSE 2026) found 7.8% of "correct" patches fail the full developer suite, inflating reported rates ~6.2pp. You are not measuring correctness; you are measuring test-gaming.

**Single-run numbers are noise.** The reliability work (arXiv 2602.16666, HAL) reports Claude Opus 4.5 at 77.3% accuracy but **0.74 outcome consistency** — roughly one in four "solved" tasks is not solved on an identical rerun. Anthropic's own "Adding Error Bars to Evals" has been out since 2024 and HAL remains the only major leaderboard systematically reporting confidence intervals.

**And when companies do measure privately, they find things they would not have guessed.** Two clean examples, both from primary sources:

| Org | What they built | What measurement changed |
|---|---|---|
| DoorDash (DashBench) | 105 cases mined from ~1,000 candidate PRs (reverted, hotfixed, benign, noisy); severity-weighted scoring (critical 4×, high 2×, med 1×, low 0.5×); triangulated engineer annotation + historical findings + calibrated LLM judge | Their **production config was not optimal**. Kimi K2.6 + Fable 5 hit 65.2% weighted recall at $3.81/PR vs production's 53.6% at $3.91/PR — **+11.6pp recall at lower cost**. Also: "Human feedback was valuable but frequently wrong." |
| Databricks | Real merged PRs from their multi-million-line, 10+ language monorepo; filtered for recency, human authorship, test coverage, self-containment; descriptions rewritten to strip solution hints; **git history sealed** so agents cannot recover the fix; graded on held-out tests, explicitly **no LLM judge** ("rewards sounding right over being right") | Open-weight **GLM 5.2 statistically tied with Opus 4.8 at $1.28/task vs $1.94** — a 34% variable-cost reduction at quality parity. Also: "Token costs are often a poor indicator of overall task costs." |

Meta independently built REAP/ProdCodeBench (arXiv 2604.01527) specifically to test how well public benchmarks predict production agent performance. Three of the most capable engineering organisations in the world, converging independently on the same missing artefact, each extracting a double-digit-percent finding from it.

That convergence is your signal. The question is whether the thing they each built is a product or a sprint. Part IV argues it is a product for exactly three reasons, all of which are things internal builds skip.

---

## Part IV — The rebuilt product

### IV.1 Positioning

**Agent Evaluation CI.** A private, continuously-running, execution-verified regression suite for your AI coding stack, deployed inside your own CI, that answers: *did the thing we just changed make our agents better or worse on our code?*

Call it CI, never benchmarking. The word choice is worth a 5× price difference because it determines the budget line: benchmarking bills against a discretionary research budget; CI bills against developer platform infrastructure, which already exists and is much larger.

### IV.2 The trigger events — why it recurs

A procurement bake-off is a one-off. This is not, because the configuration surface changes constantly:

| Trigger | Frequency (2026) | Currently measured by anyone? |
|---|---|---|
| New frontier or open-weight model release | every 4–8 weeks, 6+ vendors | Public benchmarks only — wrong repo, contaminated |
| Agent harness / CLI version bump (Claude Code, Codex, Cursor, OpenHands) | weekly | **No** |
| Your own `CLAUDE.md` / `AGENTS.md` / skills / MCP tool changes | continuously, by many hands | **No — this is the big one** |
| Context/retrieval config, sub-agent topology, tool permissions | continuously | **No** |
| Your codebase drifting under the agent | continuously | **No** |

The third row is the highest-frequency, most under-served, and strategically most important trigger. Every engineering org on earth is currently editing agent instruction files **blind** — shipping configuration changes to a system that writes production code, with no test. That is an absurd state of affairs and it will not persist.

It also **de-risks the entire thesis from the consolidation scenario.** If Anthropic's coding share (already 54% per Menlo and rising) goes to 90% and multi-model dies, the "which model" question dies with it — but the "did our config change help" question does not. Design for that from day one.

### IV.3 The wedge — start where no container is needed

Do not start with "benchmark every model on your monorepo." That is heavy, slow to value, and shaped exactly like a services engagement. Rank the wedges by time-to-first-value:

**Wedge A — AI code review quality (start here).** Replicate and productise DashBench. The economics are uniquely favourable:

- **No environment construction at all.** You score review outputs against a diff. You never build, install or run the customer's code. The single hardest technical bottleneck in the field (see Part V.2) is bypassed entirely at the wedge stage.
- **Labels are free and historical.** Reverted commits, hotfixes following a merge, incident-linked PRs, and prior human review findings are all sitting in the customer's git and incident history. You can mine thousands of labelled cases where DoorDash mined 105.
- **Universal, painful, and unmeasured.** Every enterprise now runs an AI reviewer — Copilot, CodeRabbit, Greptile, Graphite, Cursor Bugbot — and essentially none of them know their **false-negative rate**, which is the only number that matters and the only one production telemetry cannot produce. DoorDash's stated motivation is precisely this: "acceptance rate, thumbs-up feedback, or a single aggregate score can make a reviewer look useful while hiding where it fails."
- **Time to first insight: days.** Read-only git access, no VPC deployment, no build integration.

**Wedge B — Agent config regression on the customer's CI (expand).** Heavier, needs build integration, but this is where the recurring platform contract lives.

**Wedge C — Full model bake-off.** This looks most like your original idea and is the *worst* wedge: one-off, services-shaped, competes with free. Sell it as an output of A+B, never as the entry point.

### IV.4 Buyer

Platform Engineering / Developer Experience lead — the Capital One pattern. Economic buyer: VP Engineering or Head of Platform. Champion: the one engineer who has been asked "is Cursor actually worth it?" and cannot answer. Not procurement. Not the CFO. Not the CISO (though security review is a gate you must pass, see V.5).

---

## Part V — Technical architecture

The three things below are precisely what a six-week internal build skips, and skipping them produces **confidently wrong answers that are invisible to the team that built it**. That invisibility is your entire commercial argument. Your demo is not "we can benchmark" — it is *"here is the decision your internal bake-off got wrong, and here is why you could not have known."*

### V.1 Task mining

Source: the customer's git history. Candidate filters, in order of importance:

1. **Human-authored only.** Exclude bot and AI-generated commits. Databricks does this explicitly and it is non-negotiable — training on agent output to evaluate agents is circular.
2. **Touches test files**, yielding a fail-to-pass candidate set (the SWE-bench construction primitive: tests that fail at commit N−1 and pass at N, plus pass-to-pass regression guards).
3. **Self-contained** — bounded file count, no cross-service coordination.
4. **Recent** — reflects current practice, and postdates model training cutoffs, which gives you contamination resistance for free (the SWE-bench-Live insight, applied privately).
5. **Description rewritten** to strip solution hints — the original PR body usually describes the fix.
6. **Git history sealed at eval time** so the agent cannot recover the patch from version control. Databricks flags this as a real exploit they had to close.

Expected yield, from the literature: SWE-Factory reports **33–40% valid instances** from raw issues at $0.024–0.045 each; Multi-SWE-bench got 66% but with 68 expert human annotators. Budget for a **30–50% survival rate before oracle hardening**, and a lower number after.

### V.2 Environment construction — the bottleneck, and the unlock

This is the hardest problem in the field and the numbers are grim. **EnvBench found the best LLM-agent approach configures only 6.69% of Python repos and 29.47% of JVM repos.** ExecutionAgent manages 66% across 14 languages but at 74 minutes and $0.16 per project. There is no commercial product that reliably auto-containerises an arbitrary repository — I looked hard, and the honest answer is that every capable system (Repo2Run, ExecutionAgent, SWE-Factory's SWE-Builder) is a research prototype topping out at 30–66% on unseen repos.

**The unlock: you do not have to solve this.** Your customer already has a working build. They have a CI system that checks out arbitrary commits, installs dependencies and runs tests, thousands of times a day, hermetically. Your job is not environment *synthesis*; it is environment *reuse* — snapshot the customer's existing CI container image at commit N−1 and run inside it.

This flips the field's hardest open research problem into an integration problem against Buildkite / GitHub Actions / Jenkins / Bazel. It is the single most important architectural decision in the company, and it is why an enterprise product can work where a general-purpose "point it at any GitHub URL" product cannot. Keep LLM-driven environment synthesis (SWE-Factory-style, ~$0.03/instance) only as a fallback for repos without usable CI.

### V.3 Oracle hardening — your defensible differentiator

If you mine tasks from PRs and use their accompanying tests as the oracle, **you inherit SWE-bench's disease**: 77% of instances admitting a passing wrong patch. You would be certifying agents that game weak tests, and shipping that to a customer as "verified" is worse than useless.

The fix exists in the literature and nobody ships it:

- **Mutation testing on the fail-to-pass set.** Generate wrong-patch variants (operator-based mutation rules plus LLM-based semantic mutation, per STING). Any task where a mutant survives the test suite is a weak task — discard it or strengthen it.
- **Differential testing** against the ground-truth patch (PatchDiff) to separate "wrong" from "valid alternative implementation" — 46.8% of divergences were similar-but-divergent implementations, and treating those as failures is its own measurement error.
- **Assertion augmentation.** STING reported line coverage 40.8% → 51.6% and 2.4× more assertions than the developer-written tests.

Report *oracle strength* as a first-class per-task metric on your config cards. No one else does. It is the thing that makes your number more trustworthy than the customer's own, and it is legible to a sceptical staff engineer in one slide.

### V.4 Execution and adapters

Sandboxed trajectory execution in the customer's own cloud (their Kubernetes, or Modal/E2B/Daytona if they prefer managed). Adapter layer over harnesses (Claude Code, Codex CLI, Cursor CLI, OpenHands, mini-SWE-agent, Aider, plus the customer's bespoke internal scaffolds — that last one matters most and is where DX-style telemetry vendors cannot follow) and over models (frontier APIs plus open-weight endpoints across Together/Fireworks/Baseten/Groq/Nebius, or self-hosted).

Grading: **execution-based primary, always.** Follow Databricks and refuse the LLM judge for correctness. Use a calibrated LLM judge only for non-executable dimensions — code review findings, adherence to internal conventions — and calibrate it against human annotation the way DashBench did, with disagreements resolved manually and fed back. The 2026 literature on LLM-as-judge reliability for SE tasks is not encouraging (arXiv 2604.16790 on judge bias; 2606.29920 on rubric verification), so treat judged metrics as secondary and label them as such.

### V.5 Data boundary — architecture, not a roadmap item

Nothing leaves the customer's perimeter but metrics. Tasks, source, trajectories, patches: all stay in their VPC. You receive scalar results and failure taxonomies. This is non-negotiable from day one, not an enterprise-tier upsell — because your buyer's security review is the gate that kills seed-stage vendors, and "we run inside your existing CI" is the only answer that passes it easily.

Convenient side effect: your eval compute lands on the customer's existing committed cloud spend rather than your COGS. See Part VIII — this is worth more than it sounds.

---

## Part VI — Statistical design, in detail

This is where internal builds fail invisibly, and where a rigorous product wins arguments. Concretely: a team runs each config once over 60 tasks, sees 62% vs 58%, and switches models. Given measured outcome consistency of ~0.74, that difference is indistinguishable from noise, and they have just committed a quarter of platform work to a coin flip.

**Design.** Paired, same tasks across all configs, k repeats per (task, config) cell.

**Model.** Fit a hierarchical / mixed-effects logistic model rather than comparing raw pass rates:

$$\text{logit}\,P(y_{ijk}=1) = \mu + \alpha_i + \beta_j + \varepsilon_{ijk}, \qquad \alpha_i \sim \mathcal{N}(0,\sigma^2_{\text{task}})$$

where $\alpha_i$ is a random effect for task $i$ and $\beta_j$ a fixed effect for config $j$. Task difficulty variance $\sigma^2_{\text{task}}$ dominates in practice, and partialling it out buys far more power than adding tasks. Naive pass-rate comparison throws this away.

**Repeats.** Per-task per-config success is Bernoulli with high stochasticity (outcome consistency 0.70–0.85, sub-metrics as low as 0.41). The variance of a cell mean falls as $\sigma^2/k$. **k = 3 minimum, k = 5 for release-gating decisions.** Anything at k = 1 is decoration.

**Power.** For a paired binary comparison, McNemar's test on discordant pairs: with discordance rate $p_d$ and target difference $\delta$,

$$n \approx \frac{(z_{\alpha/2}+z_\beta)^2 \, p_d}{\delta^2}$$

At $p_d \approx 0.30$, $\delta = 0.05$, 80% power: **n ≈ 940 task-observations** — reachable as ~200 tasks × k=5, not as 60 tasks × k=1. State your minimum detectable effect on every report. A customer who learns their suite can only detect ≥12pp differences has learned something valuable about every decision they made last quarter.

**Metrics to report, in priority order:**

1. **pass^k** (all k runs succeed) — the metric that actually predicts autonomous production behaviour, and the one that exposes the reliability gap. Report alongside pass@1, never instead of it.
2. **Cost per *solved* task**, not cost per task — this is what surfaces the token-snowball effect, where failures cost 4–5× successes.
3. **Failure cost share** — what fraction of spend went to trajectories that solved nothing. SWE-Effi's central finding, and the number that most changes buyer behaviour.
4. **Oracle strength** — mutation survival rate on the underlying tasks.
5. **Wall-clock p50/p95** per trajectory — matters more than cost for developer-in-the-loop configs.
6. **Failure taxonomy** — env setup, wrong file, over-adaptation (27.3% of divergences per PatchDiff), test-gaming, context exhaustion, tool error, loop.

**Sequential testing.** Group-sequential or SPRT stopping to abandon clearly-inferior configs early. In eval workloads this typically cuts compute 40–60%, which is a direct COGS line, not a nicety.

---

## Part VII — Moat, competition, and what kills you

### VII.1 What is actually defensible

Be honest: the software is not the moat. Four things are, and only stacked:

1. **The per-customer task corpus and hardened graders.** Once your suite is the gate on their agent stack, ripping it out means re-deriving the corpus. Real switching cost, accrues monthly.
2. **Cross-customer priors, delivered without leaking data.** This is the strongest one. DoorDash learned one thing about one reviewer. You learn the shape of the answer across 200 codebases: which `(model × harness × config)` tuples work for Go monorepos with heavy mocking, for Python services with thin test coverage, for TypeScript frontends. No customer can build this and no lab has the access. Federated by construction — private tasks stay private, only the shape of the answer aggregates.
3. **Latency of coverage.** New model drops; your suite covers it in 24 hours; the internal build takes three weeks and does it once. At a 4–8 week model cadence, that gap is most of the value.
4. **Neutrality.** In a market where every vendor grades its own homework, where SEO farms publish mutually contradictory benchmark numbers, where OpenAI deprecated a benchmark it had itself endorsed, and where Scale sells eval services while owning the benchmark — an independent, methodologically legible party is scarce. A vendor's own evaluation is not admissible evidence in a bake-off against that vendor.

None of these is strong alone. Stacked with 18 months of head start they are enough for a Series A. Do not oversell it.

### VII.2 Competitive map

| Threat | What they have | Why you survive | Danger |
|---|---|---|---|
| **Coding-agent vendors** (Anthropic, Cursor, GitHub) | Distribution, the model, the harness, the account | Neutrality; a vendor cannot certify itself against a competitor | **Highest.** They only need "good enough" dashboards to defuse the pain. Cursor already bought Koala for enterprise rollout; GitHub holds the Gartner MQ three years running |
| **DX, Jellyfish, Swarmia, LinearB, Faros** | Own the "measure engineering" budget line; all shipped AI SKUs in 2025–26; real enterprise logos | **They measure what happened; only an eval measures what would have happened.** They read git and telemetry — correlational, no counterfactual, no execution | High. Closest budget-line collision. Most likely acquirer |
| **Braintrust ($80M B), LangSmith ($1.25B), Langfuse, Arize, Galileo** | Capital, eval primitives, developer mindshare | They evaluate *the AI product you build*; you evaluate *the AI that builds your product*. Different buyer (AI eng vs platform eng), different oracle (LLM judge vs execution), different corpus | Medium-high. Adjacent enough to expand in, and better capitalised than you will be |
| **Scale, Surge, Mercor, Snorkel, Handshake** | Enormous capital (Mercor in talks at $20B), expert labour, SWE-bench Pro | They sell to labs. Their enterprise motion is bespoke partnership, not product | Medium. But see Part IX — they are also your future customer or acquirer |
| **Vals AI** | The only genuine enterprise-custom-benchmark vendor found | ~$1.3M revenue, 12 people, focused on legal/finance/health | Low as a competitor. High as a **warning**: this motion has been tried and stayed small |

### VII.3 The five things that kill you, ranked

1. **Coding-agent vendors ship a "how is your agent doing on your repo" dashboard.** They have the distribution and every incentive. *Mitigation:* neutrality plus cross-vendor coverage. *Honest assessment:* this is a real risk you cannot fully eliminate; you can only be enough better and enough neutral that the dashboard does not close the deal.
2. **It is a six-week internal build.** DashBench is 105 cases. *Mitigation:* the parts they skip — oracle hardening, statistical power, environment reuse at scale, cross-harness normalisation, weekly release coverage — produce wrong answers that are invisible. *You must demonstrate this, not assert it.* Ship a free tool that takes a team's existing internal eval and shows them its minimum detectable effect and its mutation-survival rate. If those numbers are as bad as the literature predicts, that is your entire top of funnel.
3. **Data access.** Nobody hands a private monorepo to a seed-stage company. *Mitigation:* Part V.5, from day one.
4. **Consolidation to a single vendor.** Anthropic at 54% coding share and climbing. *Mitigation:* the config-regression use case (IV.2, row 3) is vendor-agnostic and survives.
5. **The market is services-shaped.** No consultancy publishes a rate card; Thoughtworks does not sell it as a line item; Vals stayed at ~$1.3M. *Mitigation and hard test:* if onboarding a customer costs more than **two days of your engineers' time**, you are a consultancy. Gate on it (Part X).

---

## Part VIII — Unit economics

**COGS is the thing most people get wrong here, and it is genuinely dangerous.**

Cost per agent trajectory, triangulated: HAL reports $67–367 for a full 500-task SWE-bench Verified run ($0.13–0.73/task); Databricks reports $1.28–1.94/task on a real large monorepo. Take **$1–2/task** for private enterprise repos.

A full sweep of 200 tasks × 6 configs × k=5 = **6,000 trajectories ≈ $6,000–12,000**. Weekly, that is $300–600k/year of compute for one large customer. That is not a SaaS gross margin; that is a hosting business.

Three mitigations, in order of impact:

1. **Run in the customer's cloud.** Their committed spend, their existing budget line, your COGS approaches zero. This alone converts the business model. It also happens to be the same architecture the security review demands (V.5) — rare alignment, exploit it.
2. **Tier the suites.** Nightly smoke (20 tasks, k=1, ~$40) → weekly regression (60 tasks, k=3, ~$300) → release gate on model/harness change (200 tasks, k=5, ~$8,000). Full sweeps are event-driven, not scheduled.
3. **Sequential stopping.** 40–60% compute reduction on configs that are clearly losing.

**Pricing.** Platform fee, never per-seat. Anchor to the value found, not the compute consumed: a Databricks-shaped finding is 34% off a variable inference line; a DoorDash-shaped finding is +11.6pp on defect recall, which maps to incidents avoided. Indicative: **$60–150k/year for 500–2,000 engineers**, $250k+ above that, with the code-review wedge landing at $25–40k as a paid pilot. If you can only close it with four weeks of your engineers wrapped around it, you have priced a services engagement.

---

## Part IX — The adjacent business that may be bigger than the one you asked about

This is the part worth thinking hardest about.

Every task you mine with a hardened, execution-verified oracle **is an RL environment**. That is the scarcest input in frontier model training right now, and the money there dwarfs the enterprise eval market:

- Mercor in talks at a reported **$20B valuation** (July 2026) for expert eval/training labour.
- Snorkel raised **$100M** explicitly "to build better evaluators."
- Surge built EnterpriseBench/CoreCraft — simulated enterprise environments with 2,500+ entities and 23 tools — where frontier models solve only ~30%.
- Patronus raised **$50M** to pivot from evals into "digital world models" for agent training. That pivot is the tell: the smart money moved from *measuring* agents to *building environments to train them*.
- Most directly: **Scale's SWE-bench Pro includes a commercial set of 18 proprietary repositories under formal partnership agreements.** The labs are already doing bespoke deals for private-repo-derived verifiable tasks. There is demonstrated demand and no self-serve supply.

You would be building the factory that produces that input, and enterprises would be paying you to build it.

The obvious constraint: you cannot resell customers' proprietary code. Three legitimate routes:

- **Sell the machinery**, not the output — the task-and-oracle pipeline as licensed infrastructure to labs and to eval vendors.
- **Run the pipeline at scale on permissively-licensed OSS** — the identical machinery, with output you own outright. This is a pure margin business with your enterprise work as the R&D subsidy.
- **Revenue-share with customers** who opt in to contribute hardened, anonymised task sets — the Scale commercial-set model, but self-serve.

This reframes the company from "eval tool" to **verifiable environment factory**: one piece of machinery, two buyers, and the enterprise buyer pays you to build the asset the lab buyer wants. It is also the most plausible acquisition path — Scale, Surge, Mercor, Snorkel and Patronus are all structurally short exactly this capability.

Do not lead with it. Do build toward it. The architectural decisions in Part V (oracle hardening especially) are what keep the option open, and skipping them closes it permanently.

---

## Part X — 90-day validation plan, with kill gates

Structured as hypotheses to kill, promote or defer. Nothing is built before the hypothesis in front of it survives.

### Phase 0 — Falsify the pain (weeks 1–2, low effort)

**H0:** Platform/DevEx leads at 200–5,000-engineer orgs have recently made an agent-stack decision they do not trust.

Method: 15 structured interviews. Ask for artefacts, not opinions — "show me the spreadsheet from your last bake-off." Ask what they'd have to see to change a model or harness tomorrow.

**Gate:** ≥6 ran an ad-hoc bake-off in the last 6 months **and** ≥4 say they do not trust the result. **Kill if <3.** *This is a genuine kill gate — the Capital One and Vals AI evidence means it might not clear, and finding that out in week 2 is worth more than anything else in this plan.*

### Phase 1 — Prove measurement produces surprise (weeks 3–6, medium effort)

**H1:** A properly-constructed private code-review benchmark ranks configurations differently from vendor claims and from public benchmarks.

Method: replicate DashBench methodology on 3 large public repos with rich revert/hotfix history. Mine labelled cases from git alone. Score 6+ reviewer configs. Report severity-weighted recall/precision with error bars.

**Gates:**
- ≥100 labelled cases per repo in **<1 engineer-day** (automation gate)
- Your top-ranked config differs from the vendor-claimed ranking **or** from the public-benchmark ranking (**surprise gate — if measurement produces no surprise, there is no product; kill**)
- Minimum detectable effect ≤8pp within a $500 compute budget (power gate)

### Phase 2 — Prove it changes behaviour (weeks 7–10, high effort)

**H2:** A design partner will change a production decision because of your result.

Method: 3 design partners, code-review wedge, running in their environment. Read-only git.

**Gates:**
- ≥2 of 3 **change an actual production decision** — switch model, switch harness, or change agent config. *This is the only proof that matters. Usage without decision change is a demo, not a product.*
- Onboarding ≤**2 days of your engineering time** per customer (services-trap gate — fail this and the business is a consultancy)
- Task survival through mutation hardening ≥20% (oracle-economics gate — below this, yield kills the model)

### Phase 3 — Prove someone pays (weeks 11–13)

**H3:** This sells as product, not services.

**Gates:**
- ≥1 signed paid pilot **≥$25k with no services wrapper**
- Buyer is platform/DevEx, not procurement, not a one-off innovation budget
- Renewal logic is articulable by the buyer without prompting ("we'll run this every time X changes")

### Deferred, explicitly not in the first 90 days

Environment construction for repos without CI. Multi-model routing (dead — see II.1). Public leaderboard (marketing only, and only once the private product works). RL-environment/lab business (Part IX — architect for it, do not sell it). Compliance positioning: **weak lever, deprioritise** — the EU AI Act's high-risk obligations slipped to December 2027 under the Digital Omnibus, and coding assistants almost certainly fall outside Annex III anyway.

---

## Part XI — The pitch, in five sentences

Your engineering org ships configuration changes to the systems that write your production code — new models, new harness versions, new agent instructions — with no tests. Public benchmarks cannot help: they are contaminated, their oracles admit wrong answers 77% of the time, and they measure a different codebase than yours. The organisations that built this privately found their production configuration was not optimal — DoorDash found +11.6pp defect recall at lower cost, Databricks found an open model at quality parity for 34% less. We turn your repository into a hermetic, mutation-hardened, execution-verified regression suite that runs inside your own CI, and we gate every change to your agent stack against it. Telemetry tells you what happened; only an evaluation tells you what would have happened with a different configuration.

---

## Appendix — Evidence table

### Kills the routing thesis
| Claim | Source |
|---|---|
| Unify AI (YC W23) abandoned benchmark-driven routing, pivoted to no-code agents | [unify.ai](https://unify.ai) (live site, Aug 2026) |
| Cloudflare AI Gateway routing/caching/rate-limiting free | [developers.cloudflare.com](https://developers.cloudflare.com/ai-gateway/reference/pricing/) |
| Vercel AI Gateway "no markups", BYOK zero markup | [vercel.com/docs](https://vercel.com/docs/ai-gateway/pricing) |
| OpenRouter $50M ARR, ~5% take, $1.3B val, 26× P/S; Anthropic = 46% revenue on 12% tokens | [Sacra](https://sacra.com/c/openrouter/), [TechCrunch](https://techcrunch.com/2026/05/26/openrouter-more-than-doubles-valuation-to-1-3b-in-a-year/), [BigGo](https://finance.biggo.com/news/L3-yh54B6tLPsnrZE-bl) |
| Portkey: 500B tokens/day, $15M A, "enterprise gateway free to drive adoption" | [Yahoo Finance](https://finance.yahoo.com/news/portkey-raises-15m-series-scale-170000953.html) |
| Static routers collapse OOD on agentic coding; ACRouter 62.50% vs 75.89% oracle | [arXiv:2606.22902](https://arxiv.org/abs/2606.22902) |
| RouteLLM's 85%/95% claim measured on MT-Bench/MMLU/GSM8K only | [lmsys.org](https://www.lmsys.org/blog/2024-07-01-routellm/), [GitHub](https://github.com/lm-sys/routellm) |
| List-price routing misses cache-read economics; task difficulty unknowable a priori | [IBM Research / HuggingFace](https://huggingface.co/blog/ibm-research/model-routing-is-simple-until-it-isnt) |
| Labs internalise routing; "the frontier is ultimately a routing problem" | [latent.space](https://www.latent.space/p/gpt5-router) |

### Establishes the measurement problem
| Claim | Source |
|---|---|
| Harness swap = 27.4pp swing (Qwen-3.6-flash); model spread 29.4pp | [arXiv:2606.12344](https://arxiv.org/html/2606.12344v1) |
| Report capability at model-harness pair level, never model alone; 5,194 trajectories | [arXiv:2605.27922](https://arxiv.org/html/2605.27922v1) |
| 77% of SWE-bench Verified instances admit a surviving wrong patch; re-eval −4.2 to −9.0pp | [arXiv:2604.01518](https://arxiv.org/html/2604.01518) (STING) |
| 7.8% of "correct" patches fail full suite; ~6.2pp inflation; 27.3% over-adaptation | [arXiv:2503.15223](https://arxiv.org/abs/2503.15223) (PatchDiff, ICSE 2026) |
| OpenAI deprecates SWE-bench Verified: ≥59.4% flawed tests, verbatim ground-truth reproduction | [openai.com](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) |
| Outcome consistency 0.74 at 77.3% accuracy; pass@k vs pass^k | [arXiv:2602.16666](https://arxiv.org/abs/2602.16666), [HAL](https://hal.cs.princeton.edu/reliability/) |
| Token snowball: failures 8.8M tokens vs 1.8M for successes; 10% resolve → 5.1% effectiveness | [arXiv:2509.09853](https://arxiv.org/abs/2509.09853) (SWE-Effi) |
| Statistical uncertainty required in evals | [arXiv:2411.00640](https://arxiv.org/abs/2411.00640) (Miller, Anthropic) |
| No single architecture consistently SOTA across 80 submitted approaches | [arXiv:2506.17208](https://arxiv.org/html/2506.17208v2) |

### Establishes demand
| Claim | Source |
|---|---|
| DashBench: 105 cases from ~1,000 PRs; Kimi K2.6+Fable 5 65.2% recall @ $3.81 vs production 53.6% @ $3.91; "human feedback frequently wrong" | [DoorDash Engineering](https://careersatdoordash.com/blog/how-we-learned-to-trust-our-ai-code-reviewer-at-doordash/) |
| Databricks: git history sealed, no LLM judge, GLM 5.2 tied with Opus 4.8 at $1.28 vs $1.94; >2× cost variance across harnesses | [Databricks Blog](https://www.databricks.com/blog/benchmarking-coding-agents-databricks-multi-million-line-codebase) |
| Capital One DevEx owns tool evaluation for 14,000 engineers; deprecated a tool on telemetry | [The New Stack](https://thenewstack.io/capital-one-developer-enablement/) (Mar 2026) |
| Meta REAP/ProdCodeBench: do public benchmarks predict production performance? | [arXiv:2604.01527](https://arxiv.org/abs/2604.01527) |
| METR RCT: experienced OSS devs 19% slower with AI, believed 20% faster | [metr.org](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/), [arXiv:2507.09089](https://arxiv.org/abs/2507.09089) |
| DORA 2025: throughput up, delivery stability down, bugs +9% | [research.google](https://research.google/pubs/dora-2025-state-of-ai-assisted-software-development-report/) |
| GitClear: duplication +81% since 2023, refactoring 21%→3.8% | [gitclear.com](https://www.gitclear.com/the_ai_code_quality_maintainability_gap) |
| >75% of orgs use multiple models; ~1/3 deploy open-source models | LangChain State of Agent Engineering |
| Anthropic 54% enterprise coding share (from 42% in six months) | [Menlo Ventures](https://menlovc.com) 2025 State of GenAI in the Enterprise |

### Constrains the build
| Claim | Source |
|---|---|
| Best LLM env-setup configures 6.69% of Python repos, 29.47% JVM | [arXiv:2503.14443](https://arxiv.org/abs/2503.14443) (EnvBench) |
| ExecutionAgent: 33/50 projects (66%), $0.16 and 74 min each | [arXiv:2412.10133](https://arxiv.org/abs/2412.10133) |
| SWE-Factory: 33–40% yield, $0.024–0.045/instance, exit-code grading | [arXiv:2506.10954](https://arxiv.org/abs/2506.10954) |
| Multi-SWE-bench: 1,632 from 2,456 candidates (66%), 68 expert annotators | [arXiv:2504.02605](https://arxiv.org/abs/2504.02605) |
| Full SWE-bench Verified run $67–367 API cost | [HAL](https://hal.cs.princeton.edu/swebench) |
| No self-serve product auto-containerises arbitrary private repos (negative finding) | Research sweep, Aug 2026 |

### Sizes and locates the buyer
| Claim | Source |
|---|---|
| $228–720/dev/yr licensing; $660+ fully loaded; TCO overruns 30–40%; top teams 60–70% adoption | [getdx.com](https://getdx.com/blog/ai-coding-tools-implementation-cost/) |
| 78% of FinOps-for-AI report to CTO/CIO, 8% to CFO | FinOps Foundation ecosystem reporting, 2026 |
| FOCUS 1.4 adds AI token economics; "data normalization crisis" | [siliconangle.com](https://siliconangle.com/2026/06/08/ai-token-economics-focus-specification-updates-finopsx/) |
| EU AI Act high-risk obligations deferred Aug 2026 → Dec 2027 (Digital Omnibus) | [DLA Piper](https://knowledge.dlapiper.com/dlapiperknowledge/globalemploymentlatestdevelopments/2026/The-Digital-AI-Omnibus-Proposed-deferral-of-high-risk-AI-obligations-under-the-AI-Act), [Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/) |
| Vals AI ≈ $1.3M revenue, 12 people — the enterprise-custom-benchmark motion is thin | [getlatka.com](https://getlatka.com/companies/vals.ai/funding), [vals.ai](https://www.vals.ai/product) |
| Vendr/Tropic/Sastrify/Spendflo publish no model-level pricing or quality intelligence | Research sweep, Aug 2026 (negative finding) |

### The adjacent business
| Claim | Source |
|---|---|
| SWE-bench Pro commercial set: 18 proprietary repos under partnership; public/held-out/commercial splits | [arXiv:2509.16941](https://arxiv.org/abs/2509.16941), [scale.com](https://scale.com/blog/swe-bench-pro) |
| Mercor in talks at $20B valuation for expert eval/training labour | [Bloomberg](https://www.bloomberg.com/news/articles/2026-07-09/ai-training-startup-mercor-discusses-20-billion-valuation), [TechCrunch](https://techcrunch.com/2026/07/09/mercor-is-in-talks-for-a-20b-valuation/) |
| Snorkel $100M Series D "to build better evaluators" | [Forbes](https://www.forbes.com/sites/rashishrivastava/2025/05/29/snorkel-ai-raises-100-million-to-build-better-evaluators-for-ai-models/) |
| Patronus $50M B, pivot from evals to digital world models for agent training | [TechCrunch](https://techcrunch.com/2026/06/25/patronus-ai-lands-50m-to-build-digital-worlds-that-stress-test-ai-agents/) |
| Surge EnterpriseBench/CoreCraft: frontier models solve ~30% | [surgehq.ai](https://surgehq.ai/blog/enterprisebench-corecraft) |
| Humanloop team acquihired by Anthropic — eval-infra consolidation | [TechCrunch](https://techcrunch.com/2025/08/13/anthropic-nabs-humanloop-team-as-competition-for-enterprise-ai-talent-heats-up) |
| Braintrust $80M B at ~$800M; LangChain $125M at $1.25B; LMArena $150M at $1.7B | [braintrust.dev](https://www.braintrust.dev/blog/announcing-series-b), [langchain.com](https://www.langchain.com/blog/series-b), [arena.ai](https://arena.ai/blog/series-a) |

**A note on source quality.** A large share of 2026 search results for model benchmark numbers are programmatic-SEO content farms recycling vendor claims, and several publish mutually contradictory figures for the same model. Primary sources (arXiv, vendor engineering blogs, OpenAI/Anthropic/Databricks/DoorDash posts) are used for every load-bearing claim above. Treat any single-source benchmark percentage from an aggregator site as unverified. That this is the state of public model information is itself part of the argument for a trustworthy private measurement layer.
