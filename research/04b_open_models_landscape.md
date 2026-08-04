# 4b. Open & Alternative Models in Developer Workflows

> Part of the [AI Dev Workflow Intelligence research report](./README.md).
> Question: is open/cheap/local/Chinese-origin model adoption real enough to support a routing/governance/eval business?

---

## 4b.1 Adoption is real, at production scale (high confidence)

The hobbyist framing is two years stale:

- **Chinese-origin models crossed ~45% of OpenRouter token volume by Q2 2026** (from <2% a year earlier); programming is >50% of all OpenRouter traffic; DeepSeek doubled its token share 9%→18% Jan–Jun 2026 driven by *agentic* workloads ([OpenRouter blog](https://openrouter.ai/blog/insights/deepseek-v4-adoption/), [Wing VC analysis](https://www.wing.vc/content/chinas-open-weight-takeover), [arXiv 100T-token study](https://arxiv.org/html/2601.10088v1)) **[HARD/MED]**
- **People pay:** Zhipu's HKEX filing discloses **242,000+ paying GLM Coding Plan developers**, 15× token growth in six months, and a **30% price increase into demand** (Feb 2026) — inelastic professional demand, not hobbyists **[HARD]**. Kimi tiers start at $19/mo; the famous $3/mo GLM promo is gone, killed by demand.
- **US infrastructure monetizes the weights:** Together ~$1B ARR, Fireworks ~$800M, Baseten ~$600M (reported, directional) **[ANEC/MED]**; Cerebras' investor release announces enterprise Kimi K2.6 trials at ~1,000 tok/s **[HARD]**; Microsoft reportedly exploring Azure-hosted DeepSeek V4 for Copilot Cowork (Axios) **[MED]**. Qwen passed 1B cumulative Hugging Face downloads, overtaking Llama (now <1% of routed volume).
- Anthropic keeps ~12–15% of tokens but a far larger **dollar** share: the market has split into a **premium-dollar lane and a commodity-token lane** — exactly the spread a routing/eval business arbitrages.

## 4b.2 The compliance line moved (high confidence)

The question is no longer "Chinese model?" but "Chinese *endpoint*?":

- **Hosted Chinese APIs are radioactive for regulated work**: DeepSeek's hosted service banned on government devices in 6+ countries and 17 US states; no BAA/FedRAMP/SOC2 **[MED]**.
- **The same weights on Fireworks/Together/Bedrock/your VPC are increasingly the *low-friction* path** ("the procurement inversion"): static safetensors don't phone home; data residency evaporates. Mistral occupies the parallel EU-sovereignty niche with named on-prem logos (Abanca, SNCF 4,000 devs, Capgemini 1,500+) **[HARD]**.
- Governance/eval implication: enterprises now need *model provenance policy* (origin vs endpoint vs deployment), which is a policy-artifact product surface — and per-model capability evidence to justify each lane.

## 4b.3 What still breaks (high confidence, maintainer-documented)

- **Tool-call format fragility**: GLM emitting tool calls inside `<think>` blocks (Cline #5843); one default (`parallel_tool_calls: true`) breaking GLM across all OpenAI-compatible endpoints with infinite read loops (Roo #11071); Ollama-served models rejected or looping on tool-format mismatches (Cline #11263) **[HARD]**.
- **Edit-format failures**: maintainers state plainly that GLM/Qwen "struggle with the SEARCH/REPLACE block format… causing the change to fail silently" (Cline #8040). Aider's leaderboard quantifies convergence: DeepSeek V3.2 now posts 97.3% well-formed edits at ~$1.30 per full benchmark run (vs ~$146 for some frontier runs) — edit discipline has mostly converged at the top; **long-horizon judgment and failure recovery haven't**.
- Every open model × harness × endpoint combination has its own dialect; Chinese labs' response is to ship **model + Anthropic-compatible endpoint + own CLI as a bundle** (Qwen Code, ~18k stars). Failure modes are *harness-specific* — which is precisely why repo/harness-level evaluation beats model-level leaderboards.

## 4b.4 The gap, in numbers

| Model | SWE-bench Verified | Price ($/M in/out) | Note |
|---|---|---|---|
| Claude Opus 4.6 | 80.9 | 5.00 / 25.00-class | Dollar-share leader |
| **MiniMax M2.5** | 80.2 (self-reported, Claude Code scaffold) | 0.30 / 1.20 | **[MED, self-reported]** |
| **GLM-5** | 77.8 | 1.00 / 3.20 | Beats Gemini 3 Pro (76.2) **[MED]** |
| Claude Sonnet 4.6 | ~77 | 3.00 / 15.00 | |
| **Qwen3-Coder-Next** | 70.6 | runs on a 64GB Mac (80B/3B-active) | **[HARD, lab report]** |
| DeepSeek V4 | ~68–74 (variant-dependent) | 0.27 / 1.10 | |

The frontier lag is now **~3–10 points and 3–6 months** (from 12+ months in 2024), closing fastest on exactly the agentic-coding benchmarks (RL on execution environments scales — Qwen ran 20k parallel environments), slowest on long-horizon reliability. Cost deltas: **5–25× per token, ~3–8× realized per task** (cheaper models take more turns), ~5–10× on subscriptions **[MED-HIGH]**.

## 4b.5 Local inference: real niche, not the main event (medium-high confidence)

Ollama is the #1 "agent orchestration" tool at 51% among agent-building developers (Stack Overflow 2025) **[HARD]**, and workstation-class models are now genuinely capable (Qwen3-Coder-Next at 70.6 Verified on a Mac; gpt-oss-20b in 16GB). But long agentic sessions still hurt locally (tool-calling gaps, KV-cache invalidation); the honest pattern is *local for routine/private work, cloud for hard tasks*. The commercially significant "local" is **server-side self-hosting in the VPC** (vLLM/SGLang, Mistral on-prem deals) — the compliance story, not the laptop story.

## 4b.6 Sub-agent economics are productized (medium-high confidence)

OpenRouter shipped `openrouter:subagent` as a platform primitive (frontier orchestrator delegates ~5–8 of 20 tool calls to cheap workers); planner/executor telemetry shows ~57% per-build savings switching the executor tier; routing surveys claim 50–70% of requests can drop a tier at 90–95% retained quality **[MED, vendor-skewed]**. Independent team-level verification of *realized* savings is thin — which is itself an opening for an evidence product.

## 4b.7 Answer to the section question

**Yes — open-model adoption is strong enough to support a routing/governance/eval business, but the business is the governance/eval layer, not the routing.** The heterogeneous fleet is now the norm (premium lane + commodity lane + compliance lanes); the price/quality frontier is real and moves monthly; the failure modes are harness-specific and empirically discoverable — all of which makes *repo-and-harness-specific evidence* the scarce input. Pure routing is commoditizing at the gateway layer ([Section 3](./03_routing_vs_benchmarking.md)); what enterprises lack is trustworthy, current answers to "which lane for which task on our code." Confidence: high on viability, medium on the pace of frontier-gap closure.
