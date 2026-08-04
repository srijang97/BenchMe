# 11. Appendices: Sources, Evidence Grading & Open Questions

> Part of the [AI Dev Workflow Intelligence research report](./README.md).

---

## A. Method

- **~90 distinct web searches** (July 5, 2026) across five parallel research workstreams: (1) tool/agent/PR-review landscape, (2) routing/gateways/observability, (3) benchmarking/evals, (4) open/local models, (5) buyer pain/market sizing — plus direct searches on community pain, shadow AI, repo-benchmarking vendors, worktree workflows, and verification tooling.
- Evidence grading used throughout: **[HARD]** primary sources (filings, RCTs, official docs/blogs, maintainer-acknowledged issues, SEC/HKEX documents) · **[MED]** credible surveys, funded-vendor research, multi-source secondary reporting · **[ANEC]** individual complaints, single blogs, SEO-adjacent aggregators.
- Known bias corrections applied: repo-variance numbers come partly from vendors selling repo evals (weighted down, direction corroborated by Epoch/METR/HAL); OpenRouter traffic over-represents indie/startup usage (corrected with enterprise filings/provider revenue); several 2026 comparison sites are content-farm-adjacent (flagged, not load-bearing).

## B. Key primary sources by section

| Topic | Highest-grade sources |
|---|---|
| Adoption/trust | [Stack Overflow 2025 survey](https://survey.stackoverflow.co/2025/ai) (49k n) · [DORA 2025](https://cloud.google.com/blog/products/ai-machine-learning/announcing-the-2025-dora-report) (~5k n) · [Atlassian DevEx 2025](https://www.atlassian.com/blog/developer/developer-experience-report-2025) |
| Productivity reality | [METR RCT](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/) · [DX AI ROI research](https://getdx.com/blog/ai-roi-engineering/) (400+ cos) · [Faros AI Productivity Paradox](https://www.faros.ai/blog/ai-software-engineering) |
| Billing pain | [TechCrunch on Cursor apology](https://techcrunch.com/2025/07/07/cursor-apologizes-for-unclear-pricing-changes-that-upset-users/) · [GitHub usage-based billing announcement](https://github.blog/news-insights/company-news/github-copilot-is-moving-to-usage-based-billing/) · [Visual Studio Magazine billing-shock report](https://visualstudiomagazine.com/articles/2026/06/04/copilot-billing-shock-hits-developers.aspx) · Anthropic class action (Yahoo Finance, Jun 2026) |
| Benchmark collapse | [SWE-Bench Illusion (ICSE 2026)](https://openreview.net/forum?id=ZJCyrBpgnW) · [Cursor reward-hacking audit](https://cursor.com/blog/reward-hacking-coding-benchmarks) · [Poolside audit](https://poolside.ai/blog/through-the-looking-glass) · [UTBoost (ACL 2025)](https://aclanthology.org/2025.acl-long.189/) · [SWE-bench Pro (Scale)](https://scale.com/blog/swe-bench-pro) · [Epoch AI review](https://epoch.ai/publications/what-skills-does-swe-bench-verified-evaluate) |
| Task mining | [SWE-smith](https://github.com/SWE-bench/SWE-Smith) · [SWE-bench-Live/RepoLaunch](https://arxiv.org/abs/2505.23419) · [EnvBench](https://arxiv.org/abs/2503.14443) (env-setup success rates) |
| Repo-specific eval vendors | [Sigmabench](https://sigmabench.com/) · [Stet](https://www.stet.sh/) · [RepoGauge](https://repogauge.org/) · [codeprobe](https://github.com/sjarmak/codeprobe) · [Factory Agent Readiness](https://factory.ai/news/agent-readiness) · [Sourcegraph CodeScaleBench](https://github.com/sourcegraph/CodeScaleBench/) |
| Routing/gateways | [OpenRouter Series B + State of AI](https://openrouter.ai/blog/announcements/series-b/) · [Not Diamond code-router docs](https://docs.notdiamond.ai/docs/pre-trained-router-code) · [TwinRouterBench](https://arxiv.org/html/2605.18859) · [Agent-as-a-Router](https://arxiv.org/html/2606.22902) · [RouteLLM](https://sky.cs.berkeley.edu/project/routellm/) · [Vercel AI Gateway](https://vercel.com/ai-gateway) · [Kong Claude Code governance guide](https://konghq.com/blog/engineering/claude-code-governance-with-an-ai-gateway) · [Uber GenAI Gateway](https://www.uber.com/us/en/blog/genai-gateway/) |
| Open models | [Zhipu HKEX filing](https://www.hkexnews.hk/listedco/listconews/sehk/2026/0419/2026041900085.pdf) (242k paying devs) · [OpenRouter DeepSeek adoption](https://openrouter.ai/blog/insights/deepseek-v4-adoption/) · [arXiv 100T-token study](https://arxiv.org/html/2601.10088v1) · [Cerebras Q1 FY2026 investor release](https://investors.cerebras.ai/) · Cline issues [#5843](https://github.com/cline/cline/issues/5843), [#8040](https://github.com/cline/cline/issues/8040), [#11263](https://github.com/cline/cline/issues/11263) · [Mistral Code enterprise deployments](https://mistral.ai/news/mistral-code/) |
| Quality/security strain | [GitClear 2025](https://www.gitclear.com/ai_assistant_code_quality_2025_research) (211M lines) · [Veracode GenAI security](https://www.veracode.com/blog/spring-2026-genai-code-security/) · Apiiro Fortune-50 telemetry (via [CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-generated-code-vulnerability-surge-2026/)) |
| Review burden / AI slop | [GitHub maintainers blog](https://github.blog/open-source/maintainers/welcome-to-the-eternal-september-of-open-source-heres-what-we-plan-to-do-for-maintainers/) · [arXiv AI-slop study](https://www.arxiv.org/pdf/2603.27249) · [LeadDev](https://leaddev.com/software-quality/open-source-has-a-big-ai-slop-problem) |
| Market/funding | [DX→Atlassian $1B](https://prefaceventures.medium.com/dx-to-be-acquired-by-atlassian-for-1b-3b4fd38102db) · [CodeRabbit Series B](https://techcrunch.com/2025/09/16/coderabbit-raises-60m-valuing-the-2-year-old-ai-code-review-startup-at-550m/) · [Qodo $70M](https://techcrunch.com/2026/03/30/qodo-bets-on-code-verification-as-ai-coding-scales-raises-70m/) · [Cursor→SpaceX SEC 8-K](https://www.sec.gov/Archives/edgar/data/1181412/000162828026043411/spaceexplorationtechnologi.htm) · [Anthropic Series G](https://www.anthropic.com/news/anthropic-raises-30-billion-series-g-funding-380-billion-post-money-valuation) · [SlashData developer census](https://www.slashdata.co/post/global-developer-population-trends-2025-how-many-developers-are-there) |
| Shadow AI | [PagerDuty Shadow AI Survey 2026](https://www.pagerduty.com/newsroom/shadow-ai-workplace-survey-2026/) · [CSA Shadow AI research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-shadow-ai-apps-enterprise-20260530-csa-sty/) · [IDC](https://www.idc.com/resource-center/blog/shadow-ai-how-stealth-productivity-is-strangling-enterprise-ai-adoption-and-creating-a-security-nightmare/) |

## C. Claims flagged for re-verification before external use

| Claim | Grade | Why flagged |
|---|---|---|
| Claude Code ~$8B ARR (May 2026) | ANEC | Analyst projection beyond Anthropic's disclosed $2.5B+; use the disclosed figure |
| Together/Fireworks/Baseten ARR figures | ANEC | "Reportedly" from aggregator; directionally consistent only |
| Continue.dev acquired by Cursor | ANEC | Single source, unconfirmed |
| Portkey→Palo Alto Networks | MED | Stated on Portkey's own site footer; terms unfound |
| MiniMax M2.5 = 80.2 SWE-bench Verified | MED | Self-reported, nonstandard scaffold |
| Cursor→SpaceX $60B | HARD but pending | SEC-verified announcement; deal not closed (Q3 2026 expected) |
| 2026 comparison-site benchmark numbers (web3aiblog, wetheflywheel, locoroo etc.) | ANEC | Content-farm-adjacent; never load-bearing in this report |

## D. Open questions (and how to resolve them)

1. **Will teams grant even local-CLI repo access at scale?** → resolved by the 10 paid-audit offers (30-day plan).
2. **Real mining yield on messy private repos** (the 7–29% env-setup number is from *hard* OSS repos; enterprise may be better or worse) → resolved by the first 3 audit engagements; instrument the assess step.
3. **Does per-repo ranking variance persist as frontier models improve?** If variance collapses, the calibration thesis weakens → monitor Sigmabench public data + own cross-repo results quarterly.
4. **What fraction of enterprise coding traffic is gateway-visible vs subscription-direct?** Determines outcome-join coverage → ask in every platform-lead interview; no public data exists.
5. **Will EU AI Act enforcement actually require AI-code evidence, or will general SDLC audit suffice?** → interview a compliance lawyer (discovery plan, expert target #9).
6. **Not Diamond's code router real-world performance** — no public benchmark; if it works well from thin data, routing-policy value shifts → track their early-access customers.
7. **Stet/Sigmabench traction** (revenue, logos) — private; watch hiring pages, case studies, and whether they move toward continuous subscriptions.

## E. Interview scripts

Full question banks (AI-native CTOs, platform/DevEx leaders, agencies, security/compliance) are in [§10.2](./10_validation_and_build_plans.md).
