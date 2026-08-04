# Economics, Productivity, Subsidy, and Open Models

## 1. The core argument we analyzed

A common buyer argument is:

> “$200–$300 per developer per month is tiny relative to a $100k–$200k developer salary. If AI improves productivity meaningfully, the spend is obviously worth it.”

This argument is mathematically right — but strategically incomplete.

## 2. Break-even math

If annual salary is:
- $100k–$200k
and AI spend is:
- $2.4k–$3.6k per year

then the break-even productivity uplift is only about:
- 1.2%–3.6%

So on pure finance, AI spend is often easy to justify.

## 3. Why the argument is incomplete

The key issue is **net productivity**, not gross output.

Net productivity depends on:
- verification effort
- review burden
- rework/debugging
- hallucinated changes
- security review
- tool overlap
- CI/runtime cost
- context drift
- human coordination

So the real question is:

> Are the gains real after verification and workflow friction?

## 4. What public evidence says on productivity

### Positive evidence
- Microsoft 2023 Copilot controlled study: 55.8% faster on a benchmark task
- Microsoft 2025 field experiments: 26.08% more completed tasks
- Surveys often show strong self-reported gains

### Cautionary evidence
- METR 2025: experienced open-source developers were 19% slower on familiar real tasks
- DORA 2025: AI can improve throughput but may reduce delivery stability if systems are weak
- Sonar 2026: AI code share high, trust low, review burden high

## 5. Pricing evolution

The market has shifted from:
- cheap flat subscription story

toward:
- seat + premium requests
- seat + AI credits
- seat + extra usage
- token-based agent pricing
- PR review billing
- API/BYOK layers

Examples:
- GitHub Copilot AI Credits and usage-based billing
- Cursor guaranteed API usage + bonus usage
- Anthropic extra usage at API rates
- OpenAI Codex token-based pricing
- Windsurf quotas + API-priced overage

## 6. Subsidy analysis

We cannot know exact per-plan margins, but public evidence supports three subsidy forms:

### Investor subsidy
Large AI companies still operate with massive funding and ongoing cash burn / capex expectations.

### Cloud/platform subsidy
Hyperscalers are spending extraordinary sums on AI infrastructure that is not yet fully amortized.

### Cross-subsidy from light users
Heavy users are increasingly being metered because cheap flat plans are not enough to cover high-intensity agentic usage.

## 7. Why spend may not fall even if token prices fall

Per-token costs are falling, but:
- usage expands
- workflows become more agentic
- more of the SDLC becomes metered
- verification costs rise
- review tools add extra layers of spend

So total spend per heavy user may stay flat or rise even while unit cost falls.

## 8. Open/open-weight model crossover

### Already attractive today
Open/cheap models are already economically attractive for:
- repo exploration
- summarization
- docs
- PR descriptions
- some first-pass tests
- some first-pass review

### Likely attractive over the next 12–24 months
- CI repair
- low-risk edits
- stronger test-generation
- bounded bug fixes
- more helper/subagent tasks

### Still likely frontier-dominated longer
- architecture
- ambiguous debugging
- high-risk changes
- final review
- security-sensitive work

## 9. Strategic implication for our product

The lesson is:

- Do not lead with “AI is too expensive.”
- Lead with “prove where premium AI is worth it and where cheaper/open models are safe.”

That makes these products stronger:
1. repo benchmark
2. procurement audit
3. workflow observability
4. PR evidence / verification
5. routing later

## 10. Bottom line

The right pitch is not:
> “We reduce token costs.”

The stronger pitch is:
> “We show which AI stack is worth paying for on your repos, where verification is killing ROI, and where cheap/open models can safely replace expensive workflows.”
