All searches are done â€” 14 distinct queries covering token rankings, coding plans, benchmarks, failure modes, security, local inference, and routing economics. Here is the report.

---

# Open-Weight / Chinese-Origin Model Adoption in Real Software Development Workflows (as of July 2026)

**Evidence quality labels used throughout:** **[A]** = primary source (lab reports, exchange filings, investor releases, official docs, GitHub issues), **[B]** = reputable secondary (arXiv studies, Stanford HAI, Axios, official leaderboards), **[C]** = credible blog/aggregator (SEO-adjacent, directionally useful, verify before quoting). Confidence ratings on conclusions: High / Medium / Low.

---

## 1. Are open models used in REAL teams, or mostly hobbyists?

**Answer: Real production usage at massive and rapidly growing scale â€” this is no longer a hobbyist story. Confidence: High.**

The strongest single dataset is OpenRouter's routed traffic, now studied academically. A 2026 arXiv paper analyzing ~100T tokens of OpenRouter traffic ([arxiv.org/html/2601.10088v1](https://arxiv.org/html/2601.10088v1)) **[B]** found DeepSeek was the largest open-source contributor at 14.37T tokens in the study window, followed by Qwen (5.59T), Llama (3.96T), Mistral (2.92T), OpenAI's gpt-oss (1.65T), MiniMax (1.26T), Z.ai (1.18T), and Moonshot (0.92T). Crucially for the "real work" question: Qwen's traffic is **40â€“60% programming tokens** â€” an almost inverted profile from DeepSeek's chat/roleplay-heavy mix. Programming is now **>50% of all OpenRouter traffic**, up from ~11% at the start of 2025 ([wing.vc/content/chinas-open-weight-takeover](https://www.wing.vc/content/chinas-open-weight-takeover)) **[B]**.

Scale and share numbers, triangulated across sources:

- Chinese-origin models crossed **45% of OpenRouter token volume** by Q2 2026, up from under 2% a year earlier; by origin-based measures as high as ~56â€“61% ([wing.vc](https://www.wing.vc/content/chinas-open-weight-takeover)) **[B]**. The router itself grew ~4x YoY (roughly 5Tâ†’20T+ tokens/week April 2025â†’April 2026), so open models took share of a quadrupling market.
- OpenRouter's own blog reports DeepSeek roughly **doubled token share from 9% to 18%** between January and June 2026, driven overwhelmingly by *agentic* workloads â€” V4-Flash was 70% of DeepSeek's agentic token flow a month after release ([openrouter.ai/blog/insights/deepseek-v4-adoption](https://openrouter.ai/blog/insights/deepseek-v4-adoption/)) **[A]**.
- Anthropic holds ~12â€“15% of tokens but a much larger **dollar** share â€” the market has split into a premium-dollar lane and a commodity-token lane ([digitalapplied.com OpenRouter June 2026 roundup](https://www.digitalapplied.com/blog/openrouter-new-models-june-2026-roundup-pricing-rankings)) **[C]**.

Direct revenue signals â€” the best "real teams pay money" evidence:

- **Zhipu/Z.ai (now HKEX-listed)** disclosed in its annual report that the GLM Coding Plan exceeded **242,000 paying developers**, token usage grew **15x in six months**, and the company **raised prices 30% and removed first-purchase discounts in February 2026** because demand outstripped compute supply ([HKEX filing](https://www.hkexnews.hk/listedco/listconews/sehk/2026/0419/2026041900085.pdf); [cntechpost.com](https://cntechpost.com/2026/03/31/zhipu-loss-widens-rd-spending/)) **[A]**. A vendor that can raise prices 30% into growth is serving inelastic professional demand, not hobbyists. Its follow-on "Claw Plan" hit 400,000 subscribers within 20 days of March 2026 launch **[A]**.
- **US inference providers hosting these weights are printing money:** Together AI ~$1B ARR, Fireworks ~$800M ARR (10T+ tokens/day), Baseten ~$600M ARR ([rywalker.com/research/ai-inference-platforms](https://rywalker.com/research/ai-inference-platforms)) **[C â€” figures are "reportedly," treat as directional]**. All three prominently front-page DeepSeek V4, Kimi K2.6/K2.7 Code, and GLM 5.x ([fireworks.ai](https://fireworks.ai/), [baseten.co](https://baseten.co/)) **[A]** â€” you don't headline models nobody's enterprise customers buy.
- **Cerebras' Q1 FY2026 investor release** (a NASDAQ-listed company post-IPO) announced enterprise customer trials of **Kimi K2.6 at ~1,000 tokens/sec** â€” "the first trillion-parameter model served on Cerebras" ([investors.cerebras.ai](https://investors.cerebras.ai/news-releases/news-release-details/cerebras-systems-announces-strong-first-quarter-2026-results)) **[A]**.
- **Microsoft** was reported by Axios to be exploring a "secured" Azure-hosted version of DeepSeek V4 to power Copilot Cowork ([axios.com](https://www.axios.com/2026/06/22/open-source-ai-china-cost-risk-glm-deepseek)) **[B]**. If Microsoft can't hold a closed-American-only line, few can.
- **Qwen ecosystem gravity:** Qwen passed **1 billion cumulative Hugging Face downloads**, overtaking Llama, with 200k+ Qwen-tagged models and ~40% of all new LLM derivatives on the Hub being Qwen-based ([wing.vc](https://www.wing.vc/content/chinas-open-weight-takeover)) **[B]**. Meta's Llama, meanwhile, has fallen **below 1% of routed OpenRouter volume** â€” effectively displaced as the open-weight standard-bearer.

Caveat: OpenRouter is a biased sample (indie devs, AI-tool startups, agent platforms over-represented; big-enterprise direct API traffic invisible). But the paying-subscriber counts, US provider ARR, and Cerebras/Microsoft signals cover exactly the enterprise blind spot, and they point the same direction.

---

## 2. Shadow vs official usage; Chinese-hosted APIs vs Chinese-origin weights on Western infra

**Answer: Shadow usage is rampant generally; the compliance world has bifurcated sharply â€” Chinese-hosted APIs are radioactive for regulated work, while Chinese-origin *weights* on US/EU infra have become a mainstream, sometimes even *preferred*, procurement path. Confidence: High on the bifurcation, Medium on shadow-usage specifics for coding.**

Shadow AI numbers (general, not coding-specific): **67â€“80% of employees use AI tools without approval**; only ~18% of orgs have enforced AI security policies (Salesforce Workforce AI Survey 2026 via [redteampartner.com](https://redteampartner.com/blog/shadow-ai-enterprise-risk/)) **[C]**; Gartner-sourced reporting says 68% use unauthorized AI tools, up from 41% in 2023 ([jdsupra.com](https://www.jdsupra.com/legalnews/the-shadow-ai-crisis-your-employees-are-5858601/)) **[B]**; a Freshworks survey of 1,000 IT leaders found 92% claim full AI visibility while 71% admit unapproved use is common ([freshworks.com](https://www.freshworks.com/theworks/employee-experience/shadow-ai-survey-results/)) **[B]**. In software specifically, Grip Security's figure that **91% of AI tools in orgs are unmanaged** and Stack Overflow's 84% AI adoption imply most coding-tool adoption happens below procurement's radar ([ecs-org.eu/Codacy](https://ecs-org.eu/unmanaged-ai-tool-usage-in-software-development-poses-an-emerging-governance-risk-codacy-addresses-the-visibility-gap-through-source-code-analysis/)) **[B]**. A developer pointing Claude Code at `api.z.ai/api/anthropic` with a $10/month personal GLM key is the canonical 2026 shadow-usage pattern â€” trivially easy (one env var: `ANTHROPIC_BASE_URL`) and invisible to network monitoring that only watches for chatgpt.com.

The hosted-API side is legally toxic: DeepSeek's hosted service is banned on government devices in Australia, Taiwan, Italy, Czech Republic, Netherlands, and **17 US states**; H.R. 1121 ("No DeepSeek on Government Devices Act") is advancing with bipartisan support; DeepSeek has no HIPAA BAA, FedRAMP, SOC 2, or PCI documentation ([beyondscale.tech CISO guide](https://beyondscale.tech/blog/deepseek-enterprise-security-ciso-guide)) **[B]**.

But the *weights* are procurement-distinct from the *service*. One analysis dubs this "the procurement inversion": with DeepSeek V4-Pro shipped MIT-licensed (1.6T params, 49B active, native 1M context) while top US frontier access got tangled in informal government gating, "the path of least compliance frictionâ€¦ is a Beijing-trained model running on Western GPUs in a Western VPC" ([dodatathings.dev](https://dodatathings.dev/blog/the-procurement-inversion)) **[C â€” provocative framing, but the underlying facts check out]**. Static safetensors don't phone home; data residency issues evaporate; residual risks (jailbreak susceptibility, censorship-trained behaviors, CoT exploits) persist regardless of hosting and need serving-layer mitigation **[B]**. Stanford HAI treats worldwide dependence on Chinese open weights as a first-order policy phenomenon ([hai.stanford.edu](https://hai.stanford.edu/policy/beyond-deepseek-chinas-diverse-open-weight-ai-ecosystem-and-its-policy-implications)) **[B]**. Fireworks, Together, Baseten, Groq, Cerebras, Bedrock, and Vertex all serve these weights from US infra â€” this laundering-of-origin-through-infrastructure is now the default enterprise consumption mode. Mistral occupies the parallel EU-sovereignty niche: Devstral 2 (Apache 2.0), Codestral, and Mistral Code deployed on-prem at Abanca (banking), SNCF (4,000 developers), and Capgemini (1,500+ developers) ([mistral.ai/news/mistral-code](https://mistral.ai/news/mistral-code/)) **[A]** â€” named enterprise logos being the key evidence grade here.

---

## 3. What breaks in agentic coding with open models

**Answer: Tool-call format mismatches and search/replace edit failures are the dominant, well-documented failure modes; they're improving but remain the single biggest quality gap vs Claude. Confidence: High â€” this is directly documented in maintainer-acknowledged GitHub issues.**

Concrete, primary-source failure evidence:

- **Cline #5843 "GLM 4.5 support is fragile"** **[A]**: GLM emits tool calls inside `<think>` reasoning blocks where the parser can't see them; raw XML tool calls leak into output; Cline had to ship a GLM-specific prompt variant ("Invoke tools only in assistant messages; they will not execute if placed inside reasoning blocks") and merged PR #8147 to skip reasoning display for GLM entirely ([github.com/cline/cline/issues/5843](https://github.com/cline/cline/issues/5843)).
- **Cline #8040** **[A]**: maintainers state plainly that "GLM-4.6 and Qwen-coder models can struggle with the SEARCH/REPLACE block formatâ€¦ the SEARCH block doesn't exactly match file content (often whitespace/indentation), causing the change to fail silently," with umbrella issue #4384 tracking the class ([github.com/cline/cline/issues/8040](https://github.com/cline/cline/issues/8040)). Their advice includes "try a frontier model for comparison" â€” an implicit admission of the reliability tier gap.
- **Roo Code #11071** **[A]**: a one-line default change (`parallel_tool_calls: true`) broke GLM-4.5 across LM Studio and all OpenAI-compatible endpoints, producing infinite file-read loops ([github.com/RooCodeInc/Roo-Code/issues/11071](https://github.com/RooCodeInc/Roo-Code/issues/11071)). This illustrates the structural fragility: every open model Ã— harness Ã— endpoint combination has its own tool-call dialect, and defaults tuned for OpenAI/Anthropic silently break others.
- **Cline #11263** **[A]**: Ollama-served models either get rejected (HTTP 400 when the model lacks tool support in GGUF metadata) or loop forever (model returns JSON tool calls, harness expects XML) ([github.com/cline/cline/issues/11263](https://github.com/cline/cline/issues/11263)).

The Qwen3-Coder-Next technical report **[A]** confirms labs see this too: agent CLIs (Qwen-Code, Trae, OpenCode, Cline, KiloCode) each use "distinct tool-calling and MCP interaction formats," posing "a significant challenge for a single model to generalize" ([arxiv.org/pdf/2603.00729](https://www.arxiv.org/pdf/2603.00729)). Alibaba's response â€” training a custom function-call format and shipping their own CLI (Qwen Code, forked from Gemini CLI, ~18k GitHub stars by March 2026) â€” is the pattern: Chinese labs now ship *harness + Anthropic-compatible endpoint + model* as a bundle to control the failure surface.

Aider's leaderboard quantifies edit-format discipline: open models historically lagged badly on "percent well-formed edits" (Qwen2.5-Coder-32B managed only 71.6% well-formed vs Claude's 100% back in Dec 2024, [aider.chat](https://aider.chat/2024/12/21/polyglot.html) **[A]**), but by late 2025 DeepSeek V3.2-Exp posted **74.2% polyglot with 97.3% well-formed edits at ~$1.30 per full benchmark run** â€” vs ~$146 for some frontier runs ([leaderboard.steel.dev/leaderboards/aider](https://leaderboard.steel.dev/leaderboards/aider/), [llm-stats.com](https://llm-stats.com/benchmarks/aider-polyglot)) **[B]**. Edit discipline has largely converged for the top open models; where they still lose is long-horizon agentic judgment and recovery from failures. Latency is now often an open-model *advantage* when served on specialty silicon (Kimi K2.6 at ~1,000 tok/s on Cerebras **[A]**; gpt-oss-120b ~500 tok/s on Groq **[C]**).

---

## 4. Cost deltas

**Answer: 5â€“25x cheaper per token; subscription plans undercut Claude Max by 2â€“10x at list, though the famous "$3/month GLM plan" is gone â€” killed by demand. Confidence: High on prices, Medium on per-task equivalence.**

Per-million-token API prices (verify live, but consistently sourced):

| Model | Input / Output ($/M) | Source grade |
|---|---|---|
| Claude Sonnet 4.6 | $3.00 / $15.00 | [B] ([nxcode.io](https://www.nxcode.io/resources/news/kimi-code-2026-plans-pricing-developer-guide)) |
| GPT-5.4 | $2.50â€“10 / $10â€“30 | [B] (same) |
| Kimi K2.5/K2.6 | $0.60 / $2.50 (75% cache discount) | [B] |
| Kimi K2.7 Code | $0.95 / $4.00 ($0.19 cache hit) | [B] ([apidog.com](https://apidog.com/blog/kimi-k2-7-code-api/)) |
| DeepSeek V4 | $0.27 / $1.10 | [B] |
| MiniMax M2/M3 | $0.30 / $1.20 | [A] ([MiniMax GitHub](https://github.com/MiniMax-AI/MiniMax-M2)) |
| GLM-5 | $1.00 / $3.20 | [B] ([techloy.com](https://www.techloy.com/chinas-zhipu-ai-launches-glm-5-with-30-price-increase-as-stock-jumps-34/)) |
| gpt-oss-120b (Groq) | $0.15 / $0.60 | [C] |

Subscriptions: GLM Coding Plan launched in 2025 at a promotional **$3/month**; that price was removed February 11, 2026, and Lite now runs ~$10â€“18/month (quarterly billing), Pro ~$72, Max ~$160, with ~30% annual discounts ([docs.z.ai/devpack/overview](https://docs.z.ai/devpack/overview) **[A]**; [vibecoding.app](https://vibecoding.app/blog/zhipu-ai-glm-pricing-2026) **[C]**). Kimi's Moderato tier is **$19/month** with Kimi Code credits; tiers scale to $199 ([kimi.com pricing](https://www.kimi.com/resources/kimi-k2-6-pricing)) **[A]**. Compare Claude Pro $20 / Max 5x $100 / Max 20x $200 **[B]**. So the cheap-plan-vs-Claude-Max delta is now roughly **$10â€“18 vs $100â€“200** (5â€“10x), not the 30â€“60x of the 2025 promo era. The catch on GLM: top models (GLM-5.2) burn quota at 2â€“3x, and plans hard-stop rather than overflow-bill ([digitalapplied.com value analysis](https://www.digitalapplied.com/blog/glm-coding-plan-worth-it-2026-value-analysis)) **[C]**. MiniMax's framing for M2.5: **$1/hour of continuous 100 tok/s generation** ([MiniMax M2.5 README](https://github.com/MiniMax-AI/MiniMax-M2.5/blob/main/README.md)) **[A]**. Per-task caution: cheaper models often take more turns and emit more reasoning tokens, so realized per-task savings are typically 3â€“8x rather than the headline 10â€“25x per-token spread â€” and Zhipu's 30% price hike plus the promo removal shows open-model pricing is rising toward value, not racing to zero.

---

## 5. Local inference: real usage or hobby?

**Answer: A real and normalized minority practice for chat/autocomplete and privacy-constrained work; still genuinely marginal for heavy *agentic* coding. Confidence: Medium-High.**

The strongest survey datum: Stack Overflow 2025 (49k+ respondents) found **Ollama is the #1 "agent orchestration" tool at 51.1%** among developers building agents â€” ahead of LangChain (33%) ([survey.stackoverflow.co/2025/AI](https://survey.stackoverflow.co/2025/AI)) **[A]**. Qwen3-Coder-Next accumulated **1.4M Ollama downloads** within months ([chatforest.com](https://chatforest.com/builders-log/qwen3-coder-next-open-weight-coding-agent-swebench-builder-guide/)) **[C]**; gpt-oss-20b has ~7.3M HF downloads with deployment "concentrated among self-hosting enterprise developers" ([presenc.ai tracker](https://presenc.ai/research/gpt-oss-adoption-tracker-2026)) **[C]**.

What's changed the calculus is that genuinely capable coding models now fit on workstations: Qwen3-Coder-Next is 80B-total/3B-active and runs on a 64GB Mac or single high-end GPU at **70.6% SWE-bench Verified** **[A]**; gpt-oss-120b fits one 80GB GPU, gpt-oss-20b in 16GB ([openai.com](https://openai.com/index/introducing-gpt-oss/)) **[A]**; Devstral Small (24B, Apache 2.0) runs on an RTX 4090 or 32GB Mac ([mistral.ai/news/devstral](https://mistral.ai/news/devstral/)) **[A]**. Benchmarks on an M4 Pro show ~102 tok/s for Qwen3-Coder-30B via MLX ([asiai.dev](https://asiai.dev/ollama-vs-lmstudio/)) **[C]**.

But practitioner writeups converge on the same friction for agentic loops: Ollama's tool-calling gaps and KV-cache invalidation make long agent sessions painful, pushing serious local users to MLX-native servers (omlx, vllm-mlx) with persistent prefix caching and Anthropic-API compatibility ([stochasticsandbox.com](https://stochasticsandbox.com/posts/the-stack-apple-silicon-local-agents-2026-03-28/), [kunalganglani.com](https://www.kunalganglani.com/blog/local-agentic-coding-workflow-2026)) **[C]**. The honest pattern: local for routine/private work, cloud API for hard tasks. Server-side self-hosting on vLLM/SGLang is a different, unambiguously real market â€” that's what Baseten's self-hosted tier, Mistral's on-prem deals, and the whole "weights in your VPC" compliance story run on **[A/B]**.

---

## 6. Is adoption strong enough to support a routing/governance/eval business? Where is the gap closing fastest?

**Answer: Yes â€” the infrastructure layer is already monetizing at unicorn-to-decacorn scale, and heterogeneous model fleets are the norm the business depends on. The gap is closing fastest on agentic coding benchmarks via Kimi, GLM-5, MiniMax M2.5/M3, and Qwen. Confidence: High on business viability, Medium on specific benchmark numbers.**

Market validation: OpenRouter routes **25T tokens/week across 400+ models** at a ~$1.3B valuation with a 5â€“5.5% fee ([rywalker.com](https://rywalker.com/research/ai-inference-platforms)) **[C]**; Vercel AI Gateway claims 200k+ teams; LiteLLM monetizes enterprise governance (SSO, RBAC, audit logs, per-team budgets) atop a free proxy; TrueFoundry, Portkey, Helicone fill the governance/guardrails/observability slots ([openrouter.ai/blog](https://openrouter.ai/blog/insights/openrouter-vs-litellm/), [techsy.io](https://techsy.io/en/blog/best-llm-gateway-tools)) **[A/C]**. The economics only exist *because* open models created a real quality-cost frontier worth routing across â€” a 5% gateway fee on $1M spend is $50k/year, which is why enterprises graduate to self-hosted LiteLLM, and why the durable business is governance/evals rather than pure routing ([apiscout.dev](https://apiscout.dev/guides/openrouter-vs-litellm-2026)) **[C]**. Research is racing here too: RouteLLM, MasRouter (ACL 2025), Router-R1 (NeurIPS 2025) ([zylos.ai routing survey](https://zylos.ai/research/2026-03-02-ai-agent-model-routing/)) **[B]**.

The frontier-vs-open gap, in numbers (SWE-bench Verified unless noted; cross-lab comparisons are noisy â€” treat Â±3pts):

- Late 2025 snapshot **[A]** (MiniMax's controlled harness): MiniMax-M2 69.4, Kimi K2-0905 69.2, GLM-4.6 68.0, DeepSeek-V3.2 67.8 vs Claude Sonnet 4.5 77.2, GPT-5 74.9. Terminal-Bench: M2 46.3, Kimi 44.5, GLM-4.6 40.5 vs Sonnet 4.5 ~50 ([github.com/MiniMax-AI/MiniMax-M2](https://github.com/MiniMax-AI/MiniMax-M2)).
- 2026: **GLM-5 at 77.8** SWE-bench Verified, beating Gemini 3 Pro (76.2) and approaching Claude Opus 4.6 (80.9) ([techloy.com](https://www.techloy.com/chinas-zhipu-ai-launches-glm-5-with-30-price-increase-as-stock-jumps-34/)) **[B]**; **MiniMax M2.5 at 80.2** (self-reported, Claude Code scaffold) ([MiniMax M2.5 README](https://github.com/MiniMax-AI/MiniMax-M2.5/blob/main/README.md)) **[A, self-reported]**; **MiniMax M3 at 59.0 SWE-bench Pro**, ahead of GPT-5.5 (58.6) though behind Claude Opus 4.7 (64.3), with Terminal-Bench 2.1 at 66.0 ([opsmatters.com](https://www.opsmatters.com/posts/minimax-m2-vs-m3-whats-actually-different-and-which-one-should-you-use)) **[C]**; Qwen3-Coder-Next 70.6 from an 80B/3B-active model **[A]**; Mistral Medium 3.5 at 77.6 **[C]**.

The lag is now roughly **3â€“6 months and ~3â€“10 points** on agentic coding, down from 12+ months in 2024. The gap is closing fastest exactly on SWE-bench/Terminal-Bench-style agentic work (where RL on execution environments scales â€” Qwen ran 20,000 parallel environments **[A]**) and slowest on long-horizon reliability, recovery behavior, and polish, which is where Claude retains its dollar-share moat.

---

## 7. Sub-agent economics: real pattern or theory?

**Answer: Real, productized, and platform-supported â€” no longer just theory. Confidence: Medium-High.**

The clearest proof it's a real demand pattern: **OpenRouter shipped `openrouter:subagent` as a first-class platform tool** â€” the orchestrating frontier model delegates summarization, extraction, boilerplate, and reformatting to a cheap worker (their worked example: Claude Opus 4.8 at $5/M input orchestrating GLM 5.2 at $1.40/M; "in a complex agentic workflow with 20 tool calls, maybe 5â€“8 are subagent delegations") ([openrouter.ai/blog/announcements/subagent-server-tool](https://openrouter.ai/blog/announcements/subagent-server-tool/)) **[A]**. Platforms build features for observed traffic, not hypotheticals.

Quantified patterns: a planner/executor benchmark on 40 real app builds found a typical build consumes ~4M planner tokens (frontier) and ~10M executor tokens; switching the executor from Opus-class to Haiku-class saved **57% per build** ([morphllm.com/multi-agent-model-routing](https://www.morphllm.com/multi-agent-model-routing)) **[C]**. Routing surveys claim 50â€“70% of enterprise requests can be handled by the cheapest tier, for 40â€“85% cost reduction at 90â€“95% retained quality ([zylos.ai](https://zylos.ai/research/2026-05-06-ai-agent-multi-model-orchestration-runtime-selection)) **[B/C]**. Kimi's Agent Swarm (up to 300 parallel subagents) sells this architecture as a consumer feature **[A]**, and community guidance explicitly recommends hybrid Claude-Code-frontend/Kimi-backend setups for routine vs complex work ([nxcode.io](https://www.nxcode.io/resources/news/kimi-code-2026-plans-pricing-developer-guide)) **[C]**. Honest caveat: the cleanest quantifications come from vendors selling routing; independent team-level telemetry confirming realized (not projected) savings is still thin.

---

## 8. Conclusions (confidence-rated)

1. **Open/Chinese-origin models are in real production coding workflows at enormous scale** â€” >45% of OpenRouter tokens, >50% of traffic being programming, 242k paying GLM Coding Plan developers, $600Mâ€“$1B ARR at the US providers serving these weights, Microsoft evaluating DeepSeek for Copilot. The hobbyist framing is two years stale. **Confidence: High.**
2. **The compliance line has moved from "Chinese model?" to "Chinese *endpoint*?"** Hosted Chinese APIs are banned or unapprovable in regulated contexts; the same weights on Fireworks/Bedrock/your VPC are increasingly the *low*-friction path. **Confidence: High.**
3. **Tool-calling and search/replace edit reliability remain the top operational failure modes**, extensively documented in Cline/Roo issue trackers, though top open models now post 94â€“97% well-formed edit rates on Aider. Expect harness-specific tuning (dedicated providers, custom prompt variants, lab-shipped CLIs) to stay necessary. **Confidence: High.**
4. **Cost advantage is 5â€“25x per token, ~5â€“10x on subscriptions, but shrinking**: Zhipu killed the $3 promo and raised prices 30% into demand; realized per-task savings are lower than per-token headlines. **Confidence: High on prices, Medium on per-task.**
5. **Local inference is real for chat/autocomplete/privacy niches (Ollama at 51% among agent-builders) but still a poor fit for long agentic sessions**; server-side self-hosting of open weights is the commercially significant "local." **Confidence: Medium-High.**
6. **A routing/governance/eval business is viable today** â€” OpenRouter/LiteLLM/Portkey prove the category â€” but pure routing commoditizes; the defensible layer is governance, evals, and compliance attestation over heterogeneous fleets. The frontier-open gap is closing fastest on SWE-bench/Terminal-Bench agentic coding (GLM-5 77.8, MiniMax M2.5 self-reporting 80.2, vs Opus ~81), slowest on long-horizon reliability. **Confidence: High on viability, Medium on gap trajectory.**
7. **Sub-agent economics (cheap worker + frontier orchestrator) is a real, platform-productized pattern** with vendor-measured savings of 40â€“85%, though independent verification of realized team-level savings is limited. **Confidence: Medium-High.**

**Methodological note:** the highest-grade evidence here is Zhipu's HKEX filing, OpenRouter's own blog and the arXiv 100T-token study, Cerebras' investor release, lab technical reports, and maintainer-acknowledged GitHub issues. Several 2026-dated aggregator blogs (digitalapplied, rywalker, opsmatters, various pricing guides) are directionally consistent with each other but SEO-flavored â€” figures from them (provider ARR, exact tier prices, some benchmark claims) should be re-verified against primary sources before being used in anything decision-critical.

I've gathered substantial research across 14 searches and now I'm organizing this into a comprehensive 2500+ word report with inline citations and confidence assessments. The structure will cover an executive summary, then dive into whether real development teams are actually using these models versus hobbyists, examining the business signals from OpenRouter, GLM's developer base, Zhipu's revenue, and major provider metrics, followed by sections on shadow adoption versus official deployment, security and compliance implications, and what breaks when these models are used for agentic coding tasks.

I'll continue with cost comparisons across different deployment scenarios, local inference viability, the emerging market for routing and governance tools, the frontier-versus-open model gap, and sub-agent economics. Each section will include evidence quality labels distinguishing between strong primary sources, medium-tier reputable secondary sources, and weaker blog-based claims, with a note about SEO-driven content. The final deliverable will be a dense, evidence-backed report of roughly 3000 words with confidence-rated conclusions and a summary of key findings.
