# 0. Executive Summary

> **AI Developer Workflow Intelligence: Repo Evals / Routing / Verification — Business Opportunity Research**
> Research date: July 2026 · Method: ~90 web searches across five parallel workstreams + direct analysis · Full report index: [README](./README.md)

---

## The verdict in one paragraph

**Build it — but as a calibration/evidence company, not a benchmarking tool, and move fast because the category formed in the last 12 months.** The pain is real, quantified, and newly budgeted (90% adoption vs 20% measurement, 2026 billing shocks, EU AI Act deadlines). Public benchmarks collapsed as decision inputs in 2025–26 (contamination, reward hacking, saturation), and per-repo tool rankings genuinely differ (30–60% variance). Generic routing cannot substitute — it's per-prompt classification without outcome data, and the routing research itself now says coding needs execution-verified, trajectory-level feedback. The white space is specific and verifiable: **no shipping product joins token-level spend, task-level capability, and git/PR/CI outcomes.** Enter through paid procurement audits + a local-first benchmark CLI; expand to continuous calibration, verification evidence, and gateway-consumed routing policy. Direct competitors exist (Sigmabench, Stet, RepoGauge) — the differentiator is local-first trust + continuous mode + the outcome join, and the window is an estimated 12–18 months.

## The 20 highest-signal findings

**The problem is real and budgeted**

1. **Adoption saturated, measurement absent:** 90% of teams use AI coding tools; only 20% measure impact with engineering metrics (Jellyfish). Trust *fell* to 29% as usage rose (Stack Overflow, 49k devs). *[Hard data]*
2. **Perception and reality diverge by ~40 points:** METR's RCT found experienced devs 19% *slower* with AI on mature repos while believing they were 20% faster. Objective, repo-level measurement therefore has real economic value. *[Hard data — the single most load-bearing fact]*
3. **Real gains are modest and conditional:** median PR throughput +7.8% across 400+ companies (DX); individual output +98% with zero org-level DORA gain and +91% review time (Faros). DORA 2025: AI amplifies existing engineering quality — verifiable repos win. *[Hard data]*
4. **2026 made AI spend a CFO problem:** every major vendor had a billing scandal (Cursor apology/refunds → Anthropic class action → Replit $1k weeks → Copilot day-one credit exhaustion, $180 surprise bills). Procurement projections of 2–3× TCO. The ROI question moved into budget cycles. *[Hard data]*
5. **Multi-tool sprawl is the norm:** 70% of engineers run 2–4 AI tools; Cursor's spend share fell 41%→26% in 11 months (Ramp) — standardization keeps failing, making "which tool, where" a *recurring* purchase decision, not a one-off. *[Hard/medium]*
6. **Review is the binding constraint:** ~7 min to generate a PR vs ~84 min to review it; curl killed its bug bounty; 31% of PRs merge with no review. Products that triage reviewer attention attack the actual bottleneck. *[Medium]*

**Existing solutions don't answer the question**

7. **Public benchmarks died as decision inputs:** OpenAI deprecated SWE-bench Verified ("reflects training-time exposure"); 57% of "successful" agent resolutions were web lookups of the real fix (Cursor audit); weak tests overturned 24–41% of leaderboard rankings (UTBoost). Buyers rank benchmarks fifth among criteria. *[Hard data]*
8. **Repo variance is the procurement question:** agent performance varies 30–60% across similar codebases and tool *orderings* change per repo (Sigmabench; corroborated by OpenHands Index harness-model interactions). "There is no best agent, only the best agent for your codebase." *[Hard, vendor-interested but corroborated]*
9. **Generic routing is per-prompt classification:** every commercial router (incl. OpenRouter's Not Diamond-powered auto-router) classifies single requests; the largest router deliberately *avoids* mid-trajectory re-routing to preserve caches. 2026 academic consensus (TwinRouterBench, Agent-as-a-Router): coding needs step-level, execution-verified routing — i.e., benchmark-shaped data nobody ships. *[Hard]*
10. **Routing intelligence hasn't monetized:** all pure-routing startups combined raised <$45M vs OpenRouter's $165M+ for traffic/governance. The market pays for distribution and control, not routing brains. Partner with gateways; don't become one. *[Hard]*
11. **The join is unowned:** gateways see tokens but no merges; DX/Jellyfish see merges but no tokens; benchmark startups see offline capability but no live traffic. "Cost per verified merged change, by task type, by tool" is computable by no shipping product. *[Hard absence-of-evidence, 15+ searches]*
12. **LLM observability ≠ this market:** Braintrust et al. evaluate AI apps you *build*, not AI tools you *buy*; the category consolidated hard in 2025–26 (Humanloop→Anthropic, Langfuse→ClickHouse, Promptfoo→OpenAI, Portkey→Palo Alto). *[Hard]*

**The technology works and the supply side cooperates**

13. **Task mining is feasible with known hard parts:** SWE-smith/RepoLaunch prove automated benchmark generation from repos; the bottleneck is environment setup (~7% Python / ~29% JVM auto-setup success on tricky repos) — sell an assess step, price the messy tail. Oracle quality and git-history leakage require hardening (Cursor's single-commit + egress-deny harness is the reference design). *[Hard]*
14. **50–200 mined tasks + hardened harness + 4–12 weeks of pilot telemetry = a defensible procurement decision** (converged practitioner guidance; Booking.com and Shopify are the named patterns). That stack is exactly the product. *[Medium-high]*
15. **Open models are production-real:** >45% of OpenRouter tokens are Chinese-origin; 242k paying GLM Coding Plan devs (HKEX filing); the compliance line moved from "Chinese model?" to "Chinese endpoint?"; frontier gap now ~3–10 SWE-bench points at 5–25× lower token cost. The heterogeneous fleet that makes calibration valuable is already here. *[Hard]*
16. **Coding became the gateway killer workload:** 11%→>50% of OpenRouter traffic in 18 months; sub-agent delegation (cheap worker + frontier orchestrator) is platform-productized with ~40–85% claimed savings — evidence products can verify what vendors only claim. *[Hard/medium]*

**The business case**

17. **Money is 10:1 misallocated relative to stated pain:** ~$7–8B generation market (Cursor $4B ARR, Claude Code $2.5B+) vs ~$3–6B combined measurement/verification — while every survey says output can't be trusted or measured. Investors are pricing the convergence: DX→Atlassian $1B, CodeRabbit $40M ARR, Braintrust at $800M, LMArena at $1.7B on $30M revenue (~57× for *neutral measurement*). *[Hard/medium]*
18. **The buyer is identified:** VP Eng/CTO with CFO sponsorship (platform/devtools budget) for procurement evidence — highest confidence; AppSec/GRC budgets for verification evidence, accelerating into EU AI Act (Aug 2026) and CRA (Sept 2026). Trigger events: surprise bills, renewals, model releases, incidents. *[High confidence]*
19. **Direct competition arrived in the last year:** Sigmabench (SaaS repo benchmarking, SOC2), Stet (local eval on your subscriptions, AGENTS.md A/B testing), RepoGauge/codeprobe (OSS local-first). Category validated; land-grab phase; differentiation = local-first + continuous + outcome join + neutrality. *[Hard]*
20. **Size:** realistic SAM ≈ 50k orgs with 50+ engineers; $20–60k blended ACV → bootstrap-viable at $3–10M ARR without the data flywheel, venture-scale only if the calibration dataset compounds into the policy/evidence layer. Timing is right: budgets are forming now, no winner yet. *[Medium]*

## What to do (condensed)

| Horizon | Action | Detail |
|---|---|---|
| Next 30 days | Validation sprint: 20 interviews, 2 public agent-teardowns, **10 paid-audit offers ($5–15k) with pre-registered kill thresholds** | [§10.1](./10_validation_and_build_plans.md) |
| Weeks 4–8 | Local-first benchmark CLI v1: Python+TS, Claude Code/Codex/Aider, hardened harness (history isolation, egress deny), assess→mine→run→report | [§10.3](./10_validation_and_build_plans.md) |
| Months 3–6 | Continuous re-benchmark subscription ($500–2k/repo/mo), cloud history, PR-side outcome capture, 2 design partners | [§10.4](./10_validation_and_build_plans.md) |
| Months 6–12 | Evidence packs (AppSec/AI-Act framing) + routing-policy artifacts consumed by LiteLLM/Portkey/Not Diamond | [§9](./09_strategic_synthesis.md) |
| Avoid | Bakeoff orchestrators (commoditized), standalone observability (squeezed), gateways/IDEs/PR-commenters (owned), control-plane-first (everything at once) | [§7](./07_mvp_options_scorecard.md) |

**Falsification to watch:** paid-audit conversion 0/10; mining yield <10 tasks on typical repos; per-repo rankings turning out stable across repos; DX/GitHub shipping the capability-outcome join natively. Any of these should trigger the pivot paths in [§9.2](./09_strategic_synthesis.md).
