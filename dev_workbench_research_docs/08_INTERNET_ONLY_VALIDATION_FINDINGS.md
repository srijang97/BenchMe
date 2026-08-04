# Internet-Only Validation Findings

## 1. Highest-confidence conclusions

1. The market exists.
2. Multiple players are circling pieces of the problem.
3. No one clearly owns the full bundle of:
   - private repo benchmark
   - neutral multi-tool bakeoff
   - procurement recommendation
   - workflow observability
   - evidence / verification
   - later routing
4. Public pain is real around:
   - cost / limits
   - review noise
   - repeated repo scanning / context waste
   - model/provider confusion
   - weak governance
5. Public benchmarks are increasingly seen as insufficient for real procurement decisions.
6. Public repos are sufficient for a credible PoC.
7. The least crowded wedge is repo-specific benchmark + procurement + observability.

## 2. Competitor synthesis

### Closest direct examples
- codeprobe
- Sigmabench
- Factory Agent Readiness
- Sourcegraph CodeScaleBench
- OpenHands evaluation harness

### Strong adjacent categories
- PR review / validation: GitHub, Qodo, Greptile, CodeRabbit, Cursor Bugbot, etc.
- Gateways/routing/observability: LiteLLM, OpenRouter, Orq, Portkey, Helicone, Langfuse
- Public benchmarks: SWE-bench, OpenHands Index, Terminal-Bench, Aider Polyglot, CodeReviewBench

### Core insight
The category is not empty, but the full bundle is not clearly owned.

## 3. Why repo-specific evaluation is validated

Independent public sources argue that:
- public benchmark scores are increasingly inadequate,
- large-codebase and retrieval/context differences matter,
- repo readiness matters,
- agent performance varies by codebase and setup,
- task type matters (issue resolution vs review vs testing vs information gathering).

This validates repo-specific evaluation as a real problem category.

## 4. Public pain themes

### Very common themes
- expensive but valuable tools
- quota/usage pain
- noisy AI review
- repeated repo scanning and context waste
- weak budget enforcement / model confusion in open-agent stacks
- local/open model curiosity for low-risk tasks

### Strongest inference
Users do not want “more AI comments.”
They want:
- clearer tool choice
- less noise
- less waste
- better repo understanding
- more confidence in outputs

## 5. Pricing and subsidy trend

The market is clearly moving toward:
- seat + credits
- seat + premium requests
- seat + extra usage
- token-priced coding agents
- PR review billing
- budget controls

This means the economics of heavy AI usage are becoming more explicit, which strengthens observability, procurement rationalization, and routing.

## 6. Productivity / verification insight

Public evidence says:
- AI can create real gains
- gains are highly task-dependent
- verification burden is now one of the main bottlenecks
- broad “10x developer” claims are not well supported
- products that measure where AI actually helps are more credible than generic productivity claims

## 7. Public PoC feasibility

A useful public-repo PoC is feasible today using:
- benchmark-friendly Python repos
- selected JS/TS repos
- selected Go/Rust/Java repos
- app-like repos with decent CI and tests

A reasonable PoC does not require solving every private enterprise repo problem upfront.

## 8. Hiring signals

Public job posts show companies are already hiring around:
- AI developer productivity
- workflow standardization
- secure agent sandboxes
- AI tooling standardization
- Copilot/Cursor/Claude/Codex operationalization

This is strong evidence that the category is becoming operational, not just experimental.

## 9. Open model crossover

Cheap/open models are already attractive for:
- repo exploration
- summarization
- docs
- PR descriptions
- some test scaffolding
- some first-pass review

Frontier models are still favored for:
- architecture
- ambiguous debugging
- high-risk implementation
- final review
- security-sensitive changes

This supports a future routing layer, but only after repo-specific evidence exists.

## 10. Final wedge recommendation

Strongest first wedge:
1. repo-specific benchmark / benchmarkability audit
2. AI tool procurement audit
3. workflow observability
4. PR evidence / verification
5. routing later

Weakest first wedge:
- another IDE
- generic gateway
- generic PR review bot
- pure “cheaper model router” pitch

## 11. Bottom line

If we are pursuing this space, the most defensible starting story is:

> “We help teams benchmark AI dev tools on their own repos, decide what to buy, understand where the money and verification burden are going, and only then automate routing or governance.”

That is where the white space looks strongest from public internet evidence.
