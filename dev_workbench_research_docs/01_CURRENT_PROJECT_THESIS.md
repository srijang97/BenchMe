# Current Project Thesis

## Working name

- Cost-Aware Agentic Dev Workbench
- AI Development Intelligence Platform
- Dev Agent Benchmarking / Procurement / Control Plane

## Core problem statement

Software development is moving from:
- autocomplete
- chat-based coding help
- code explanation

toward:
- coding agents
- subagents
- background agents
- AI PR review
- codebase Q&A
- workflow automation
- multi-tool AI stacks
- usage-based billing
- governance and verification pressure

The key emerging problem is **not** simply “developers need more AI.” It is:

> teams increasingly need to know which AI tools/models actually work on their repos, what they cost, how much verification they create, and where cheaper/open models can safely replace premium frontier usage.

## Strongest current product thesis

The strongest version of the idea is:

> A neutral layer for **repo-specific benchmarking, AI dev-tool procurement intelligence, workflow observability, verification evidence, and later task-aware routing/governance**.

This should sit **around** existing tools rather than try to replace Cursor, Copilot, Claude Code, or Codex.

## What the product should not be

Do **not** build:
- another AI IDE
- a generic LLM gateway only
- a generic model router only
- another standalone PR-review bot
- a local GPU appliance as the wedge

Those spaces are either crowded, harder to differentiate, or not the cleanest first buyer story.

## Product wedges we explored

### 1. Repo-specific AI benchmark
“Benchmark your own repo and workflows across tools/models/agents.”

Why strong:
- neutral
- buyer-relevant
- procurement-grade
- directly addresses trust
- repo-specific rather than benchmark-theater

### 2. AI coding procurement audit
“Which tools should we buy, for which developers, for which workflows?”

Why strong:
- immediate business value
- can start as a service
- naturally leads to benchmark product
- useful even before runtime routing exists

### 3. Workflow observability / AI dev analytics
“Where is our AI coding spend going, and what outcomes does it buy?”

Why strong:
- current tools are fragmented
- spend is increasingly metered
- leadership wants ROI and policy controls

### 4. PR evidence / verification pack
“For each AI-generated PR, show what changed, what was read, what was tested, what risk exists, and what still needs human review.”

Why strong:
- verification is a real pain
- more differentiated than generic AI PR comments
- helpful for regulated/security-sensitive teams

### 5. Cost-aware routing / control plane
“Use the cheapest safe model/tool for each workflow step, with escalation to frontier models.”

Why strong:
- potentially large savings in AI-native workflows
- logical long-term control layer

Why probably later:
- routing is hard to trust without repo-specific evaluation
- buyers need evidence before policy enforcement

## Why “cheaper tokens” is too weak as the initial pitch

For many teams, $200–$300 per developer per month is still a small fraction of salary.

So a weak pitch is:
> “We lower your AI bill.”

A stronger pitch is:
> “We tell you which AI stack is worth paying for on your repos, where verification is killing ROI, and where cheap/open models are safe.”

## Current product sequencing hypothesis

1. Repo benchmarkability audit
2. Private/public repo benchmark suite
3. AI dev-tool procurement recommendation
4. Workflow observability
5. PR evidence / verification
6. Routing / control plane
7. Enterprise governance layer

## Best first customers

### AI-native startups
Why:
- heavy multi-tool use
- high willingness to experiment
- real spend and verification pain
- shorter sales cycle

### Software agencies
Why:
- repeated client workflows
- margin sensitivity
- client trust / privacy concerns
- procurement simplification matters

### Platform / DevEx teams
Why:
- own standardization and tooling
- care about spend attribution and policy
- good enterprise expansion path

## Current strongest hypotheses

1. Public benchmarks are insufficient for real procurement decisions.
2. Repo-specific evaluation is a real and emerging category.
3. Verification debt is a stronger pain than raw token cost for many teams.
4. Advanced teams use multiple AI dev tools in parallel.
5. Open/cheap models are already attractive for some task classes, but routing must be evidence-based.
6. No one fully owns the combined category of private benchmark + procurement + observability + evidence + routing.

## Current weakest assumptions / things to keep testing

- How many teams will pay for benchmarking rather than just using vendor tools?
- How often do teams really run tool bakeoffs rather than picking based on vibe?
- How benchmarkable are realistic private repos?
- Whether PR evidence is a standalone product or only part of a broader suite.
- Whether routing is monetizable before a benchmark/audit product exists.
