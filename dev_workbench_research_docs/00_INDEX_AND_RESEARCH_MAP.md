# Cost-Aware Agentic Dev Workbench — Research Handoff Index

## Purpose

This folder packages the major threads we explored in this chat into structured Markdown documents so they can be dropped into another chat as continuity material.

## Important note

A separate weather-market source-audit packet was accidentally uploaded in this conversation. It is **not relevant** to this project and should be ignored for all future work on the AI dev workbench idea.

## Suggested reading order

1. `01_CURRENT_PROJECT_THESIS.md`
2. `02_INFRASTRUCTURE_COMPETITORS_AND_WHITE_SPACE.md`
3. `03_REPO_BENCHMARKING_AND_POC_BLUEPRINT.md`
4. `05_DEVELOPER_AI_USAGE_AND_WORKFLOW_FINDINGS.md`
5. `06_ECONOMICS_PRODUCTIVITY_SUBSIDY_AND_OPEN_MODELS.md`
6. `08_INTERNET_ONLY_VALIDATION_FINDINGS.md`
7. `09_OPEN_QUESTIONS_AND_NEXT_STEPS.md`

Use `04_DEVELOPER_AI_USAGE_DEEP_RESEARCH_PROMPT.md` and `07_INTERNET_ONLY_VALIDATION_SPEC.md` when you want to continue research in another chat with a structured prompt.

## Current project state in one paragraph

The opportunity appears real, but the strongest wedge is **not** another AI IDE and **not** a generic LLM router. The best current formulation is a product family around **repo-specific benchmarking, AI dev-tool procurement intelligence, workflow observability, verification evidence, and later cost-aware routing/policy enforcement**. The initial customers most likely to care are **AI-native startups, software agencies, and platform/DevEx teams** using multiple AI coding tools and feeling pain around verification, tool sprawl, spend opacity, and trust.

## File map

| File | What it contains |
|---|---|
| `01_CURRENT_PROJECT_THESIS.md` | Core product thesis, why the wedge exists, and current strategic position |
| `02_INFRASTRUCTURE_COMPETITORS_AND_WHITE_SPACE.md` | LiteLLM / OpenRouter / Orq.ai analysis, PR-review competitors, benchmark players, and white space |
| `03_REPO_BENCHMARKING_AND_POC_BLUEPRINT.md` | Repo benchmarking concept, benchmarkability ladder, PoC design, public repo portfolio |
| `04_DEVELOPER_AI_USAGE_DEEP_RESEARCH_PROMPT.md` | The full deep research prompt on how developer teams use AI |
| `05_DEVELOPER_AI_USAGE_AND_WORKFLOW_FINDINGS.md` | Re-executed findings on adoption, tooling, spend, workflows, segments, and pain |
| `06_ECONOMICS_PRODUCTIVITY_SUBSIDY_AND_OPEN_MODELS.md` | Salary-vs-AI-cost analysis, productivity evidence, pricing evolution, subsidy and open-model crossover |
| `07_INTERNET_ONLY_VALIDATION_SPEC.md` | The internet-only validation research programme we designed |
| `08_INTERNET_ONLY_VALIDATION_FINDINGS.md` | Executed findings from the internet-only validation packs |
| `09_OPEN_QUESTIONS_AND_NEXT_STEPS.md` | Unresolved questions, strongest next research, and recommended sequence |

## Fast-start summary for another chat

If you only paste one block into a new chat, paste this:

> We are exploring a product family around repo-specific AI benchmarking, AI dev-tool procurement intelligence, workflow observability, PR evidence / verification, and later cost-aware routing. We do **not** want another IDE and we do **not** want to lead with “cheaper tokens.” The strongest current hypothesis is that advanced teams need a neutral way to measure which AI tools/models work on their repos, where their spend is going, how to verify AI-generated work, and only then how to route tasks to cheaper/open models safely.

## Current strongest conclusions

- AI coding is mainstream, but agentic development is still concentrated in more advanced teams.
- Verification debt is a stronger pain than raw token cost for many teams.
- Serious teams increasingly use multiple tools in parallel.
- Public benchmarks are helpful, but repo-specific evaluation is increasingly recognized as necessary.
- No one clearly owns the bundle of private repo benchmarking + procurement recommendation + observability + evidence + routing.
- The best first product is likely **benchmark + audit + observability**, not routing first.

## Current best candidate first customers

1. AI-native startups (roughly 5–50 engineers)
2. Software agencies
3. Platform / DevEx teams
4. Regulated or security-sensitive product teams
5. Semi-AI-native product teams

## Current best candidate first products

1. Repo-specific AI benchmark / benchmarkability audit
2. AI coding procurement audit
3. Workflow observability and cost-per-accepted-change analytics
4. PR evidence / verification pack
5. Routing / control plane later
