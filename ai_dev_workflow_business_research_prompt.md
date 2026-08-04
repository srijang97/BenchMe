# Open-Ended Deep Research Prompt: AI Developer Workflow Intelligence / Repo Evals / Routing / Verification Business Opportunity

## Role

You are a world-class AI developer-tools researcher, DevEx strategist, software engineering productivity analyst, AI infrastructure researcher, coding-agent evaluator, enterprise procurement analyst, and startup strategist.

You are being asked to investigate a potential business idea from scratch. Do **not** assume the initial thesis is correct. Treat it as a hypothesis to test, refine, reject, or transform.

Your job is to deeply research the market, existing technology, customer pain, competitive landscape, technical feasibility, product wedges, execution paths, and optimal MVPs. You should end with your own strongest version of the idea, or explain why the idea should not be pursued.

---

## Background: Initial Idea Being Explored

Software development appears to be shifting from simple autocomplete and chat-based coding assistance toward more complex AI-assisted and AI-agentic workflows:

- coding agents
- background agents
- subagents
- AI PR review
- codebase Q&A
- automated test generation
- CI repair
- issue-to-PR workflows
- multi-tool AI development stacks
- open/local model usage
- model routing
- usage-based AI billing
- engineering leadership trying to measure AI ROI
- security, governance, and verification pressure

The rough initial idea is a product family around helping engineering teams answer questions like:

> Which AI coding tools and models actually work on our repos, for our workflows, at acceptable cost and risk?

Possible product directions include:

1. **Repo-specific AI coding benchmarks**
   - Benchmark Cursor, Claude Code, Codex, GitHub Copilot, Cline, Roo, Aider, OpenHands, OpenCode, PR review tools, and model variants on real repo-specific tasks.

2. **AI dev-tool procurement intelligence**
   - Help teams decide which tools to buy, who should get which tools, and which workflows each tool/model is best for.

3. **AI coding workflow observability**
   - Track AI usage, spend, success, review burden, retries, tool/model performance, and cost per accepted/verified change.

4. **PR evidence / verification packs**
   - For AI-generated PRs, show what changed, what the agent read, what tests ran, what risk remains, what human review is required, and whether the output should be trusted.

5. **Cost-aware model routing / policy generation**
   - Route low-risk or simple coding-agent substeps to cheaper/open/local models and reserve frontier models for high-risk or difficult tasks.

6. **AI development control plane**
   - A broader layer around policy, governance, model allowlists, agent permissions, audit logs, sandboxing, cost controls, and workflow evaluation.

One current internal hypothesis is:

> The strongest wedge may not be another AI IDE, another generic LLM gateway, or a generic model router. It may be an evidence/calibration layer for AI development: repo-specific benchmarking + procurement recommendations + workflow observability + verification evidence, with routing later.

However, you should challenge this. Generic routing players, IDEs, PR review tools, and LLM observability platforms may already be solving enough of the problem. The optimal business may be different from the initial formulation.

---

## Key Research Mindset

Be skeptical, specific, and evidence-driven.

Do not write a generic report saying “AI coding is growing.” The question is whether there is a real, differentiated, venture-worthy or bootstrappable product opportunity.

You should investigate:

- What exact customer pain exists?
- Who has it strongly enough to pay?
- What existing products already solve it?
- Which parts are crowded?
- Which parts are under-owned?
- What should the first MVP be?
- How could it be built technically?
- What would make this idea fail?
- What is the best possible version of the idea if we forget our current assumptions?

Every major claim should include citations, source quality, and confidence level.

Use current sources. Prioritize material from 2024–2026, but include older foundational sources where useful.

---

## Core Questions To Answer

### 1. Is the problem real?

Research whether engineering teams currently struggle with:

- choosing between AI coding tools
- measuring AI coding productivity
- validating AI-generated code
- AI PR review noise
- AI tool sprawl
- usage-based AI coding costs
- premium request / credit exhaustion
- shadow usage of unapproved tools
- open/local model experimentation
- routing between frontier and cheaper models
- lack of repo-specific evidence
- difficulty trusting public benchmarks
- difficulty governing AI agents
- AI-generated security or reliability risks
- repeated repo scanning / context waste
- agent failures, loops, hallucinations, wrong edits, bad tests
- lack of cost-per-outcome metrics

For each pain, determine:

- who feels it
- how severe it is
- whether it is budgeted
- whether it is frequent
- whether existing tools solve it
- whether teams would pay to solve it
- whether it is a temporary pain or durable category

Segment by:

- solo developers
- power users
- AI-native startups
- normal SaaS startups
- software agencies
- enterprise platform / DevEx teams
- regulated companies
- security-conscious product teams
- open-source maintainers
- consulting / systems integrator teams
- QA / test engineering teams
- data / ML engineering teams

---

### 2. What is the current AI development workflow reality?

Map how developers and teams currently use AI tools.

Cover at least:

- GitHub Copilot
- Cursor
- Claude Code
- OpenAI Codex / Codex CLI / ChatGPT Codex
- GitHub Copilot coding agent / Copilot CLI / Copilot Chat
- Windsurf / Codeium
- JetBrains AI Assistant / Junie
- Sourcegraph Cody / Amp
- Zed AI
- Continue
- Cline
- Roo Code
- Aider
- OpenCode
- OpenHands
- SWE-agent
- Goose
- Tabby
- Devin
- Factory
- Replit Agent
- Qodo
- Greptile
- CodeRabbit
- Graphite Reviewer
- Cursor Bugbot
- GitHub Copilot Code Review
- GitLab Duo
- Amazon Q Developer
- Sonar / Snyk / CodeQL / Semgrep AI features

For each, determine:

- adoption pattern
- individual vs team/enterprise usage
- main workflows
- pricing model
- usage limits / overage
- model flexibility
- open/local model support
- agentic capabilities
- repo context capabilities
- PR / CI integration
- governance features
- telemetry / analytics
- strengths
- weaknesses
- customer complaints
- enterprise readiness
- likely buyer

Pay special attention to teams using multiple tools simultaneously, e.g.:

- Cursor + Claude Code + ChatGPT
- Copilot + Claude Code
- Cursor + Codex
- Cline/Roo/Aider with OpenRouter or local models
- Copilot as sanctioned tool but Cursor/Claude as shadow tools
- PR review tools layered on top of coding agents
- internal model gateways with developer tools pointed at them

---

### 3. Is generic routing enough?

A key strategic objection is:

> Generic model routing may be sufficient to optimize cost and quality. Teams may not need repo-specific benchmarking.

Research this deeply.

Investigate:

- Not Diamond
- OpenRouter routers
- LiteLLM routing/fallback
- Portkey
- Helicone
- Orq.ai
- Cloudflare AI Gateway
- Vercel AI Gateway
- Langfuse / LangSmith / Braintrust / Promptfoo eval-routing workflows
- internal enterprise gateways
- custom model routers
- prompt-level vs workflow-level routing
- agentic routing research
- model router benchmarks
- dynamic routing for coding agents
- cost-aware routing
- quality/cost/latency trade-off routing
- trace-based routing
- custom routers trained on domain data

Answer:

- What exactly do generic routers solve today?
- Are generic routers already expanding into coding-agent-specific routing?
- Can routers learn enough from live traces without upfront repo benchmarks?
- What labels or eval data do routers need?
- Are prompt-level router metrics sufficient for coding tasks?
- Does coding require trajectory-level / repo-level / test-level feedback?
- Can routing alone optimize for accepted PRs, test passes, review burden, security risk, and human time?
- Is repo-specific benchmarking a separate product, or just a feature of a router?
- Could Not Diamond, OpenRouter, LiteLLM, or similar players naturally own this entire space?
- Could a startup build on top of them rather than compete with them?

Be fair. If generic routing is enough, say so. If routing needs evaluation data, explain what data and why.

---

### 4. Are public benchmarks insufficient?

Research whether public coding-agent benchmarks are enough for procurement and routing decisions.

Cover:

- SWE-bench
- SWE-bench Verified
- SWE-bench Multilingual / Pro if relevant
- Terminal-Bench
- OpenHands Index
- Aider benchmarks
- LiveCodeBench
- HumanEval / MBPP, but treat as weak for this product
- CodeReviewBench
- Sourcegraph CodeScaleBench
- private repo benchmarking vendors
- benchmark contamination concerns
- differences between benchmark success and real repo performance
- issue-to-patch vs review vs test generation vs repo Q&A
- long-context / large-repo evaluation
- tool-use and terminal-use benchmarks
- production-readiness benchmarks
- enterprise coding benchmarks

Answer:

- Do buyers trust public benchmarks?
- What do public benchmarks fail to measure?
- Are repo-specific evals genuinely needed?
- Which repo-specific tasks are benchmarkable?
- How hard is task generation?
- Can benchmark tasks be mined from git history, issues, PRs, tests, incidents, docs, or CI failures?
- What are the risks of overfitting, leakage, poor oracles, brittle tests, and unrealistic tasks?
- What level of benchmarking is enough to drive procurement?

---

### 5. Competitive landscape and white space

Map the market thoroughly.

Create competitor categories such as:

#### AI IDEs / coding assistants
- Cursor
- GitHub Copilot
- Windsurf
- JetBrains
- Zed
- Sourcegraph
- Replit
- Tabby
- Continue

#### Coding agents
- Claude Code
- Codex
- Copilot coding agent
- Devin
- Factory
- OpenHands
- OpenCode
- Aider
- Cline
- Roo
- SWE-agent
- Goose

#### PR review / code validation
- GitHub Copilot Code Review
- Cursor Bugbot
- Qodo
- Greptile
- CodeRabbit
- Graphite Reviewer
- GitLab Duo
- Amazon Q
- Sonar
- Snyk
- CodeAnt
- CodeQL / Semgrep / security tools

#### Gateways / routing / observability
- Not Diamond
- OpenRouter
- LiteLLM
- Portkey
- Helicone
- Orq.ai
- Cloudflare AI Gateway
- Vercel AI Gateway
- Langfuse
- LangSmith
- Braintrust
- Promptfoo
- Phoenix / Arize
- HoneyHive
- Humanloop
- Keywords AI

#### Benchmarking / eval / readiness
- codeprobe
- Sigmabench
- Factory Agent Readiness
- Sourcegraph CodeScaleBench
- OpenHands evaluation harness
- SWE-bench ecosystem
- Terminal-Bench
- Aider leaderboard
- internal eval platforms

For each relevant competitor, answer:

- What do they do?
- Who buys them?
- How mature are they?
- What are their core workflows?
- Do they support private repos?
- Do they execute tests?
- Do they mine tasks?
- Do they compare multiple tools?
- Do they compare multiple models?
- Do they produce procurement recommendations?
- Do they route models?
- Do they provide usage/cost analytics?
- Do they provide PR evidence?
- Do they support governance and audit?
- Are they likely to expand into this idea?
- What is their moat?
- What are their weaknesses?
- What is the wedge they leave open?

Produce a competitor matrix with columns:

```text
Company/Product
Category
Primary buyer
Main workflow
Repo-specific?
Private repo support?
Tool/model neutral?
Benchmarking?
Routing?
Observability?
PR verification/evidence?
Procurement recommendation?
Enterprise controls?
Pricing model
Maturity
Threat level
White-space left
Sources
```

---

### 6. Open and alternative models in developer workflows

Research whether teams are actually using non-default, cheaper, open-weight, local, or Chinese-origin models in software development workflows.

Models to include:

- Qwen / Qwen Coder / Qwen Code
- Kimi / Moonshot / Kimi K2
- GLM / Zhipu / Z.ai
- DeepSeek / DeepSeek Coder / DeepSeek R1 / V3
- Llama / Code Llama / Llama derivatives
- Mistral / Codestral / Devstral
- StarCoder / StarCoder2
- Gemma / CodeGemma
- Phi
- MiniMax
- other open-source/open-weight code models

Access patterns:

- direct provider APIs
- OpenRouter
- LiteLLM
- Together
- Fireworks
- DeepInfra
- Groq
- Cerebras
- Nebius
- SiliconFlow
- Novita
- Hugging Face
- Replicate
- Baseten
- Bedrock / Vertex / Azure marketplaces
- vLLM
- SGLang
- TGI
- Ollama
- LM Studio
- llama.cpp
- LocalAI
- local Apple Silicon / RTX workstations
- on-prem / private GPU clusters

Answer:

- Are these used in real teams or mostly by hobbyists?
- Are they used officially or through shadow usage?
- Which tasks are they trusted for?
- Which tasks remain frontier-model dominated?
- What breaks in agentic workflows?
- How do tool calling, JSON, context, latency, and edit reliability compare?
- What are the security/compliance concerns?
- How do companies distinguish Chinese hosted API vs Chinese-origin open weights run locally or through US/EU infrastructure?
- Is open-model adoption strong enough to support a routing/governance/eval business?

---

### 7. Task taxonomy and risk model

Create a task taxonomy for AI development workflows.

At minimum include:

#### Low-risk
- repo Q&A
- code explanation
- docs
- changelogs
- PR summaries
- issue summaries
- file discovery
- simple test ideas
- boilerplate

#### Medium-risk
- test generation
- small bug fixes
- CI triage
- dependency update suggestions
- small refactors
- first-pass PR review
- typed API changes
- internal tools
- migration planning

#### High-risk
- auth
- payments
- infra/IaC
- security review
- production data workflows
- migrations
- ambiguous debugging
- architecture decisions
- large refactors
- autonomous issue-to-PR
- final review before merge
- regulated/compliance-sensitive code

For each task, research:

- current AI usage
- model/tool suitability
- benchmarkability
- verification method
- risk level
- human review requirement
- cost sensitivity
- whether open/cheap models are viable
- whether frontier models are necessary
- whether routing could help
- whether PR evidence would help

Produce a heatmap:

```text
Rows: task types
Columns: tool/model categories
Cells: safe / maybe / unsafe / unknown
```

Tool/model categories should include:

- frontier model in premium coding agent
- frontier model in IDE assistant
- hosted open model via gateway
- local model
- self-hosted model
- PR review specialist
- generic chat assistant
- multi-agent/worktree bakeoff

---

### 8. Technical feasibility and architecture

Design possible ways to build the product.

Explore multiple technical architectures, including but not limited to:

#### A. Repo benchmark CLI
- local CLI connects to GitHub/GitLab
- mines repo tasks
- creates benchmark capsules
- runs agents/tools
- captures outputs
- runs tests
- reports quality/cost/latency

#### B. Service-assisted procurement audit
- humans plus software
- customer grants limited repo access
- run benchmark suite
- produce report
- later productize repeatable parts

#### C. GitHub app / PR evidence bot
- observes AI-generated PRs
- captures provenance if possible
- runs tests/static analysis
- summarizes risk
- produces evidence pack

#### D. AI workflow observability proxy
- integrate with LiteLLM/OpenRouter/Not Diamond/Portkey/Helicone
- collect model calls
- correlate with git/PR/CI outcomes
- report cost per accepted change

#### E. Agent evaluation harness
- run same tasks across Claude Code/Codex/Aider/OpenHands/Cline/Roo/OpenCode
- use git worktrees or containers
- compare outputs
- route or recommend

#### F. Routing policy generator
- use benchmark results to generate policy:
  - task type → allowed models/tools
  - repo path → allowed models/tools
  - risk class → verification requirements
  - budget → routing/escalation strategy

#### G. Full control plane
- model gateway
- sandboxed agent execution
- policy engine
- benchmark store
- observability
- PR evidence
- procurement dashboard

For each architecture, evaluate:

- technical difficulty
- time to MVP
- dependency on closed tools
- repo access/security burden
- integration complexity
- ability to measure outcomes
- defensibility
- buyer urgency
- pricing potential
- competitive risk
- path to expansion

Answer practical build questions:

- How can we run Claude Code, Codex, Aider, Cline/Roo, OpenHands, OpenCode fairly?
- Can closed GUI tools be benchmarked or only their CLI/API equivalents?
- Can browser/editor automation be used, or is that brittle?
- How should benchmark capsules be represented?
- How can tasks be mined from git history?
- How can we classify risk by path, diff, ownership, or semantic domain?
- How do we measure review burden?
- How do we calculate cost per accepted change?
- How do we capture provenance from tools that do not expose it?
- How do we avoid sending customer code to unapproved models?
- Should the system be local-first, cloud, hybrid, or self-hosted?
- What should the data model look like?
- What are the minimum integrations needed?

---

### 9. MVP options

Evaluate potential first MVPs.

At minimum score these:

1. **Public repo benchmark demo**
   - benchmark multiple tools/models on public repos
   - produce public leaderboard and reports

2. **Private repo benchmarkability audit**
   - tell a team how benchmarkable their repo is and what tasks can be evaluated

3. **AI coding procurement audit**
   - service-led report: what tools/models should this team buy/use?

4. **PR evidence / verification GitHub app**
   - evidence pack for AI-generated PRs

5. **AI dev workflow observability dashboard**
   - correlate AI tool/model usage with PR/CI/review outcomes

6. **Open-model adoption and routing advisor**
   - identify which workflows can safely move to cheaper/open/local models

7. **Coding-agent routing policy generator**
   - generate policy using benchmark and trace data; integrate with Not Diamond/LiteLLM/OpenRouter

8. **Agent bakeoff harness**
   - run the same task across multiple agents/tools in worktrees and compare results

9. **Local-first benchmark CLI**
   - run evals inside customer environment without code leaving

10. **Agency-focused AI delivery QA product**
   - help software agencies prove AI-assisted work quality to clients

Score each on:

```text
Buyer urgency
Pain severity
Time-to-MVP
Technical feasibility
Data access difficulty
Trust/security burden
Differentiation
Competitive intensity
Pricing potential
Expansion path
Risk of being feature-not-company
```

Recommend:

- best MVP for a solo/founder-led 4–8 week prototype
- best MVP for a 3–6 month serious build
- best service-led wedge
- best enterprise wedge
- best agency wedge
- best open-source/community wedge
- best wedge to avoid

---

### 10. Business model and GTM

Research and propose possible business models:

- paid benchmark audit
- procurement consulting + SaaS
- per-repo benchmark subscription
- per-seat observability
- per-PR evidence pricing
- usage-based routing fee
- enterprise platform subscription
- self-hosted/on-prem enterprise license
- agency/client-reporting model
- open-source CLI + paid cloud reports
- marketplace / ecosystem partnerships
- partner with gateways rather than compete

For each, evaluate:

- who pays
- why they pay
- budget owner
- sales cycle
- ACV potential
- gross margin
- support burden
- trust/security barriers
- repeatability
- expansion potential
- likely objections

Research likely buyers:

- CTO
- VP Engineering
- Head of DevEx
- Platform engineering lead
- Engineering manager
- Security/AppSec lead
- Procurement / finance
- agency founder / delivery lead
- AI tooling lead
- Staff/principal engineer champion

Answer:

- Who is the first buyer?
- Who is the user?
- Who blocks the sale?
- What budget does it come from?
- What trigger event makes them buy?
- What ROI story is credible?
- What price point could be tested?

---

### 11. Customer discovery plan

Create a primary research plan.

Include:

- 20 best customer interview targets
- 10 best expert interview targets
- 10 best communities to mine
- 10 best companies to study
- 10 best job titles to contact
- 10 best LinkedIn search queries
- 10 best Reddit/HN/GitHub searches
- 10 best questions for AI-native startup CTOs
- 10 best questions for platform/DevEx leaders
- 10 best questions for software agencies
- 10 best questions for security/compliance stakeholders

The plan should validate:

- whether the pain is real
- who pays
- which wedge resonates
- whether teams will grant repo access
- how they currently choose tools
- how they currently verify AI output
- whether they need routing
- whether they would pay for benchmarks/reports/evidence
- what MVP they would try

---

### 12. Market size and timing

Estimate the opportunity.

Do not overstate precision. Use ranges and assumptions.

Consider:

- number of professional developers
- number of AI-tool-using developers
- number of heavy AI-tool users
- number of AI-native startups
- number of software agencies
- number of enterprise DevEx/platform teams
- current spend on AI coding tools
- PR review tooling market
- LLM observability/eval market
- developer productivity platform market
- governance/security/compliance budgets
- open model adoption
- model routing market
- expected growth over 1, 3, and 5 years

Answer:

- Is this venture-scale?
- Is it better as a bootstrapped/professional-services-to-SaaS business?
- Is timing too early, too late, or right?
- Is the market likely to consolidate into existing platforms?
- Which incumbents could kill the wedge?
- Which incumbents might acquire or partner?

---

### 13. Strategic synthesis

At the end, produce your own view.

Do not simply validate the initial thesis.

Answer:

1. What is the strongest version of this business idea?
2. What is the weakest version?
3. What should definitely not be built?
4. Which customer segment should be targeted first?
5. Which MVP should be built first?
6. What should the product be called / positioned as?
7. What should the homepage headline be?
8. What is the key wedge?
9. What is the expansion path?
10. What are the top 10 risks?
11. What would falsify the idea?
12. What experiments should be run in the next 30 days?
13. What should be built in the next 4–8 weeks?
14. What should be built in the next 3–6 months?
15. What should be deferred until later?
16. Is this a standalone company, feature, consulting business, or infrastructure layer?
17. Should the company compete with Not Diamond/LiteLLM/OpenRouter, or integrate with them?
18. What is the optimal execution path for a solo technical founder?

---

## Required Research Method

Use a mix of:

- official docs
- pricing pages
- changelogs
- public roadmaps
- GitHub repos/issues/discussions
- benchmark papers and leaderboards
- academic/empirical studies
- engineering blogs
- company case studies
- Reddit/Hacker News/community evidence
- job postings
- customer reviews
- interviews/podcasts/conference talks
- VC theses and funding announcements
- open-source ecosystem signals

For each source, label evidence quality:

```text
Hard data
Medium-confidence signal
Weak/anecdotal signal
Speculation
```

For each major conclusion, provide confidence:

```text
High confidence
Medium confidence
Low confidence
Unknown / needs interview validation
```

Prioritize primary sources. For current product capabilities and pricing, use official docs/pages wherever possible.

---

## Suggested Search Areas

Use these as starting points, but do not be limited by them.

### Market and adoption
- AI coding tool adoption 2025 2026 developer survey
- Stack Overflow AI developer survey agents daily use
- JetBrains AI developer ecosystem coding agents
- GitHub Copilot usage-based billing AI credits
- Cursor pricing usage overage premium models
- Claude Code pricing enterprise usage
- Codex CLI pricing coding agent
- Sonar AI code trust survey
- DORA AI software delivery 2025
- METR AI productivity open source developers

### Generic routing and gateways
- Not Diamond coding agent router
- Not Diamond code router
- OpenRouter auto router Not Diamond
- LiteLLM routing fallback budgets
- model routing coding agents
- dynamic LLM routing agents cost quality
- agentic routing benchmark
- LLM router benchmark cost quality latency
- Portkey AI gateway routing
- Helicone routing observability
- Orq AI gateway routing evals

### Repo-specific benchmarking and evals
- repo specific coding agent benchmark
- private repo AI coding benchmark
- codebase benchmark AI agents
- codeprobe coding agent benchmark
- Sigmabench private codebase benchmark
- Factory agent readiness
- Sourcegraph CodeScaleBench
- OpenHands evaluation harness
- SWE-bench limitations enterprise
- Terminal-Bench coding agents
- Aider benchmark leaderboard

### AI coding tools
- Cursor enterprise AI coding agent docs
- Claude Code enterprise docs
- Codex CLI custom provider docs
- GitHub Copilot BYOK custom models
- VS Code AI BYOK Ollama
- Cline OpenRouter Qwen DeepSeek
- Roo Code OpenRouter Ollama
- Aider OpenRouter Qwen DeepSeek
- OpenHands LLM support Qwen Kimi
- OpenCode model provider docs
- Continue custom models Qwen
- Zed AI local models
- JetBrains AI custom models
- Sourcegraph Cody self hosted LLMs

### Open/local models
- Qwen Code coding agent
- Qwen Coder OpenRouter coding
- Kimi K2 coding agent benchmark
- GLM coding agent benchmark
- DeepSeek coder agent workflow
- Mistral Devstral coding agent
- local LLM coding agent Ollama
- vLLM OpenAI compatible coding agent
- SGLang OpenAI compatible tool calling
- LM Studio coding agent OpenAI compatible

### PR review / verification
- AI PR review tools comparison
- GitHub Copilot Code Review pricing
- Cursor Bugbot review
- Qodo code review enterprise
- Greptile code review codebase graph
- CodeRabbit pricing
- Graphite AI reviewer
- Sonar AI code assurance
- Snyk AI code security review
- AI generated code verification evidence

### Community pain
- site:reddit.com Cursor usage limits expensive
- site:reddit.com Claude Code expensive coding
- site:reddit.com AI coding agent hallucination
- site:reddit.com Cline OpenRouter cost
- site:reddit.com Aider Qwen DeepSeek
- site:news.ycombinator.com AI coding agents cost
- site:github.com Cline OpenRouter issue
- site:github.com Aider OpenRouter issue
- site:github.com OpenHands model support issue
- site:github.com Continue local model issue

---

## Required Final Deliverables

Produce a founder-facing research report with the following sections:

1. **Executive summary**
   - 10–20 bullet points with the highest-signal conclusions.

2. **Market reality**
   - How AI development workflows are actually evolving.

3. **Customer pain analysis**
   - Ranked pain points, by segment and severity.

4. **Competitor landscape**
   - Category map and competitor matrix.

5. **Technology landscape**
   - Coding agents, gateways, evals, observability, PR review, open models, local/self-hosting.

6. **Routing vs benchmarking analysis**
   - Is generic routing enough? Where does repo-specific evidence matter?

7. **Benchmarking and evaluation feasibility**
   - What can be benchmarked, how, and with what limitations?

8. **Workflow and task taxonomy**
   - Safe/maybe/unsafe map for AI workflows.

9. **MVP options**
   - Scorecard and detailed recommendation.

10. **Technical architecture options**
    - Diagrams, components, integrations, data model, security model.

11. **GTM and business model**
    - First customer segment, buyer, pricing, sales motion, wedge.

12. **Optimal product thesis**
    - Your own best version of the idea, even if different from the initial one.

13. **30-day validation plan**
    - Research, interviews, prototype, landing page, demo, outreach.

14. **4–8 week build plan**
    - MVP implementation steps, technical scope, risks.

15. **3–6 month roadmap**
    - Productization path.

16. **Falsification criteria**
    - What findings would make this idea unattractive.

17. **Open questions**
    - What remains uncertain and how to resolve it.

18. **Appendices**
    - Source table, search log, evidence grading, interview scripts, competitor screenshots if useful.

---

## Output Style

Write like a senior analyst advising a founder before they spend months building.

Be direct. Be skeptical. Use tables and matrices. Mark confidence. Separate facts from inferences. Highlight contradictions. Avoid hype.

The final answer should help decide:

```text
Should we build this?
What exactly should we build first?
Who should we sell it to?
What should we avoid?
How do we validate it fastest?
```

Do not optimize for confirming the initial thesis. Optimize for discovering the best business opportunity in this broader problem space.
