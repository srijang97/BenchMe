# Deep research prompt: coding-model and coding-agent benchmarks

## Role and mandate

Act as a senior research lead with expertise in software-engineering benchmarks, automated program repair, LLM and agent evaluation, experimental design, statistics, AI coding tools, benchmark security, engineering productivity, and enterprise AI procurement.

Produce an independent, skeptical, deeply sourced research dossier on the current coding-benchmark ecosystem. Do not merely catalogue leaderboards or validate our startup thesis. Determine how benchmarks actually work, what their scores genuinely measure, how they are built and operated, how the industry uses and perceives them, where they fail, how they are evolving, and what those findings imply for a possible product around private-repository AI coding evaluation.

Use deep-research capabilities aggressively. Explore a large and varied source base, inspect benchmark repositories and evaluator code where possible, follow citation trails, compare conflicting claims, and include a serious academic literature review. Do not stop after reading benchmark homepages, abstracts, and vendor announcements.

## Project context

We are exploring a project currently called **BenchMe**. Its provisional thesis is that engineering teams need evidence about which combination of model, coding-agent harness, context strategy, tools, budget, environment, and verification policy works for their own repositories and task classes.

The hypothesized product is a local-first calibration and evidence layer for AI-assisted software engineering. Possible capabilities include:

- private-repository task capsules;
- native and controlled model-agent comparisons;
- procurement and standardization evidence;
- cost per verified task or accepted change;
- verification and PR evidence;
- task-level policy recommendations;
- continuous re-calibration as models and harnesses change;
- eventually, evidence-backed routing or governance policies.

This is background, not a conclusion. Be willing to find that public benchmarks are sufficient, private-repo calibration is unnecessary or unscalable, incumbents already own the opportunity, buyers will not pay, or another product is superior.

Our first small experiment used a pinned public Python repository with a newly authored, unpublished feature task. We held the Codex harness constant and varied three models. A first run was invalid because the environment was accidentally read-only. A later task version passed all hidden tests, but human review found a backward-compatibility flaw the oracle missed. Clarifying the specification and adding a regression oracle changed the same model's behavior.

This experience suggests—but does not prove—that:

- infrastructure failure must be separated from agent failure;
- the evaluated unit is the complete model-harness-context-tools-budget-environment-verifier configuration;
- a green test result may not mean production-acceptable engineering;
- prompts, reference implementations, hidden tests, harness settings, and graders must be versioned;
- human compatibility and scope review may remain necessary;
- a fresh unpublished task on public code reduces direct answer memorization without eliminating repository familiarity.

Test these propositions against external evidence.

## Controlling research questions

The primary question is:

> **How should coding-model and coding-agent benchmarks be designed, operated, interpreted, and governed so their results provide valid, reproducible, decision-useful evidence about real software-engineering performance—and which important needs remain unsolved by today's public benchmarks, leaderboards, evaluation platforms, and vendor-internal systems?**

The product question is:

> **Does a defensible opportunity exist for a private-repository calibration and evidence layer? If so, what exact problem, buyer, methodology, workflow, product boundary, and MVP should it target?**

## Research stance and key distinctions

Maintain these distinctions throughout:

1. Model capability versus model-harness system performance.
2. Inference harness versus evaluation/grading harness.
3. Native-product evaluation versus normalized controlled evaluation.
4. Public benchmark performance versus private-repository transfer.
5. Functional test success versus production-acceptable engineering.
6. Token/API cost versus total cost per accepted, verified change.
7. Task validity versus benchmark reliability versus leaderboard governance.
8. Maintainer-verified fact, research result, vendor claim, inference, and community anecdote.
9. Frozen, live, rolling, private-test, and customer-private benchmark designs.
10. Benchmark optimization versus genuine generalization.

Never casually report “Model X scores Y” when the evidence actually concerns Model X inside a particular agent, prompt, tool set, retry policy, and budget.

## Scope and landscape discovery

Focus on benchmarks for code generation, code editing, repository understanding, issue-to-patch repair, terminal engineering agents, long-horizon software work, model-harness comparisons, testing, review, and verification. Include adjacent computer-use, data-science, or research-agent benchmarks only when they teach something transferable.

Start from, but do not limit research to, the following candidate families. Verify exact names, versions, maintainers, dates, active status, and methodology. Discover important omissions.

### Function, algorithm, and library coding

- HumanEval and HumanEval+;
- MBPP and MBPP+;
- APPS;
- CodeContests;
- MultiPL-E;
- DS-1000;
- BigCodeBench;
- LiveCodeBench and later variants;
- CRUXEval;
- SciCode and domain-specific coding suites.

### Codebase, completion, and retrieval

- RepoBench;
- CrossCodeEval;
- long-context, repository-context, code-search, localization, and dependency-understanding benchmarks.

### Editing, repair, and repository agents

- the full SWE-bench ecosystem: Original, Lite, Verified, Multilingual, Multimodal, Live, Pro, harder, rolling, or current successor variants;
- SWE-bench-Live, SWE-rebench, and other freshness-oriented derivatives;
- SWE-Lancer;
- SWE-agent and mini-SWE-agent evaluation programs;
- Aider's original and Polyglot benchmarks;
- GitBug-Java and Defects4J-derived evaluations;
- Commit0;
- OpenHands evaluation suites and indexes;
- emerging feature-implementation and issue-to-PR benchmarks.

### Terminal and long-horizon agents

- Terminal-Bench 1.x and 2.x;
- Harbor and Terminus;
- CORE-Bench;
- RE-Bench;
- AgentBench;
- OSWorld where methodologically relevant;
- MLAgentBench, ScienceAgentBench, and other engineering-agent suites;
- multi-agent software-development benchmarks.

### Harness and configuration effects

- Harness-Bench;
- Claw-SWE-Bench;
- controlled comparisons of SWE-agent, mini-SWE-agent, OpenHands, Aider, Codex, Claude Code, Cursor, Copilot, and other harnesses;
- studies ablating context management, tools, edit protocols, retries, test loops, memory, and subagents.

### Commercial and private evaluation

- Scale or other commercial SWE-bench variants;
- Sigmabench, Stet, Factory agent-readiness work, and newer direct competitors;
- evaluations published by major model labs and coding-tool vendors;
- METR and other independent productivity or autonomy evaluations;
- documented private evaluation practices inside engineering organizations.

Prioritize roughly 15–25 benchmarks for systematic comparison and select approximately 8–12 for full deep dives.

## Workstream 1: Create a rigorous taxonomy

Develop a taxonomy based on the construct being measured, not benchmark branding. Distinguish:

- function synthesis;
- algorithmic and competitive coding;
- library and data-science coding;
- code completion, retrieval, and localization;
- edit-format compliance and patch generation;
- bug repair from issues;
- repository-level features and migrations;
- test generation and CI repair;
- code review and defect detection;
- terminal/environment manipulation;
- long-horizon engineering;
- model-only evaluation in a fixed harness;
- native coding-product evaluation;
- harness ablations;
- offline task benchmarks versus live engineering outcome measurement.

For each category, explain what it can and cannot measure, its likely real-world transfer, and assumptions required to treat success as engineering capability.

## Workstream 2: Reverse-engineer benchmark mechanics

For every benchmark selected for detailed treatment, build a benchmark card covering all of the following.

### Identity and intended construct

- Name, version, owner, maintainers, funding or commercial ties.
- First release, major revisions, and current activity.
- Stated purpose, target user, and intended construct.
- What it appears to measure in practice.

### Task provenance and construction

- Source: synthetic problems, exercises, GitHub issues, PRs, commits, customer repos, or human-authored scenarios.
- Inclusion/exclusion criteria and sampling procedure.
- Languages, frameworks, repositories, domains, task types, and difficulty distribution.
- Time range and model-training-cutoff considerations.
- Whether issues, fixes, tests, comments, and repository history were already public.
- Human authoring, LLM generation, filtering, deduplication, and manual validation.
- Representativeness of real engineering work.

### Validation and positive controls

- Whether an oracle, gold patch, reference implementation, or expected artifact exists.
- Whether it is a historical developer patch, evaluator-authored solution, generated solution, or specification only.
- Negative control: what fails before the solution.
- Positive control: what passes after it.
- Human solvability review and inter-rater procedure.
- Broken-task detection, quarantine, correction, and retirement.

### Agent input and environment

- Exact information shown to the agent.
- Base repository state and available history.
- Dependencies, services, fixtures, credentials, and container image.
- Internet, package registry, web search, issue tracker, and Git-history access.
- Shell, file, search, browser, IDE, MCP, LSP, test, and patch tools.
- Visible versus hidden files and tests.
- Security and isolation model.

### Inference harness

- Fixed, recommended, pluggable, or unrestricted harness.
- System prompt, task prompt, agent loop, edit protocol, planning, recovery, and compaction.
- Model-specific prompts, templates, tool adapters, or parameters.
- Repo maps, RAG, embeddings, semantic search, AST/dependency graphs, or curated context.
- Test-feedback loops, reflection, retries, verifier feedback, subagents, voting, ensembles, or human intervention.
- Token, context, turn, tool-call, wall-clock, compute, and monetary budgets.
- Temperature, seeds, caching, determinism, and trial count.
- Whether a submission is one trajectory, pass@k, best-of-n, ensemble, or arbitrary system.

### Output and evaluator

- Expected output: function, file, patch, repository state, terminal state, review, or other artifact.
- How output is transferred into grading.
- Clean evaluation container versus same mutable environment.
- Hidden/visible tests, full suites, static checks, artifact graders, rubrics, LLM judges, and human review.
- Treatment of regressions, flakiness, timeouts, partial credit, invalid patches, environment failures, and grader failures.
- Whether candidates can modify or exploit tests and evaluator state.
- Whether maintainability, scope, security, architectural fit, and review burden are considered beyond tests.

### Metrics and statistics

- Primary and secondary metrics.
- Resolve rate, pass@1, pass@k, partial reward, Elo, cost, latency, steps, tokens, and review effort.
- Macro/micro averaging and task weighting.
- Number of trials and nondeterminism treatment.
- Confidence intervals, bootstrap methods, paired comparisons, significance, and ranking stability.
- Missing runs, rate limits, crashes, and censored timeouts.
- Whether small leaderboard differences are statistically meaningful.

### Operation and governance

- Who runs inference and evaluation: maintainer, vendor, submitter, cloud service, or auditor.
- Self-reported versus independently reproduced scores.
- Requirements for code, prompts, metadata, traces, logs, costs, and exact model IDs.
- Public/private test access, quotas, and anti-overfitting controls.
- Review, audit, dispute, correction, and takedown procedures.
- Versioning and comparability across releases.
- Reproducibility of tasks, images, configs, patches, logs, and trajectories.
- Licensing, repository-owner, security, and redistribution concerns.

### Use and reception

- Research, training/RL/RFT, agent development, marketing, procurement, investment, policy, or regression uses.
- How labs and coding vendors cite the result.
- Independent reproductions and vendor-score discrepancies.
- Maintainer, researcher, developer, and enterprise perception.
- Saturation, contamination concern, and current trust level.

## Workstream 3: Explain the complete benchmark lifecycle

Describe how modern coding benchmarks are created and operated:

```text
task discovery
-> task packaging
-> environment reconstruction
-> oracle/reference validation
-> negative and positive controls
-> inference
-> artifact capture
-> isolated evaluation
-> aggregation and statistical analysis
-> submission audit
-> leaderboard publication
-> maintenance, correction, and retirement
```

Identify strong and weak stages today. Compare function benchmarks, SWE-style repository benchmarks, terminal benchmarks, live/rolling benchmarks, and private customer evals.

## Workstream 4: Analyze model-harness confounding

Treat the harness as a first-class experimental variable. Find controlled evidence for the effects of:

- system/task prompts and repo instructions;
- file discovery, repo maps, RAG, semantic search, and dependency graphs;
- edit formats and patch application;
- tool definitions and function-calling protocols;
- shell/test access and verifier feedback;
- compaction, summarization, and memory;
- planning, retries, reflection, and recovery;
- subagents, parallelism, voting, and best-of-n;
- web access, issue lookup, and Git history;
- token, time, tool-call, and financial budgets;
- model-specific optimization.

Find studies holding the model fixed while changing the harness and vice versa. Quantify credible effects. Determine when a leaderboard should label an entry as a model, model-agent pair, harness configuration, complete system, or product.

Assess whether a “neutral harness” is coherent. Explain the trade-off between equal treatment and equitable model-specific adaptation when models require different chat templates, tool schemas, or edit protocols.

## Workstream 5: Conduct a structured academic literature review

Review approximately 2018 to the present, emphasizing 2023–2026. Search arXiv, OpenReview, ACL Anthology, ACM/IEEE sources where accessible, Google Scholar or Semantic Scholar, conference proceedings, and citations from influential papers.

Cover:

- code-generation evaluation;
- automated program repair and fault localization;
- repository-level evaluation;
- agent and long-horizon evaluation;
- test-based and execution-based grading;
- hidden-test quality and mutation testing;
- contamination, memorization, and data provenance;
- saturation, overfitting, and live benchmarks;
- reward hacking and grader exploitation;
- construct validity, ecological validity, reliability, and generalization;
- pass@k and stochastic-system statistics;
- model-harness interactions;
- cost-, latency-, and risk-aware evaluation;
- AI coding productivity studies;
- maintainability, security, and review burden of generated code.

Report search strategy, representative terms, inclusion/exclusion logic, key papers by theme, publication status, consensus, disagreements, limitations, and open questions. Do not treat every preprint as established fact.

## Workstream 6: Investigate contamination and benchmark gaming

Separate:

1. training contamination;
2. runtime retrieval through web, Git history, mirrors, issues, or package sources;
3. prompt/harness overfitting to frozen tasks;
4. benchmark-specific SFT/RL/RFT or synthetic training;
5. grader manipulation and test gaming;
6. hidden metadata, test, or gold-patch leakage.

Find concrete documented incidents, audits, issues, and experiments. Explain detection, impact, and mitigation. Compare chronological splits, rolling task streams, private tests, egress control, sealed history, canaries, overlap analysis, held-out repos, and post-cutoff tasks.

Answer specifically: how much does a new unpublished task on a famous public repository reduce contamination, what risks remain, and how should the result be labeled?

## Workstream 7: Collect revealing stories and controversies

Develop well-sourced case studies, potentially including:

- the creation and evolution of SWE-bench and Verified;
- human-validated subsets and gold-patch failures;
- saturation and moves to Live, Pro, Multilingual, Multimodal, harder, or rolling variants;
- agents retrieving known fixes instead of deriving them;
- score changes caused by web or Git-history access;
- evaluator vulnerabilities and test-overwrite exploits;
- broken environments or gold solutions;
- ranking changes caused by harness, edit format, budget, prompt, or retry policy;
- Aider's model-specific edit formats;
- Terminal-Bench validation and gaming;
- vendor scores versus independent reproduction;
- benchmarks abandoned or removed because of contamination;
- public benchmark progress failing to transfer to productivity or private code.

Trace stories to primary evidence. Separate verified incidents from allegations.

## Workstream 8: Understand industry usage and perception

Research frontier labs, open-model developers, IDE/coding-agent vendors, harness maintainers, academics, enterprise DevEx/platform/security/procurement teams, developers, investors, and analysts.

Determine whether benchmarks are used for:

- model selection;
- launch marketing;
- agent development and release regression;
- training and reward design;
- pricing and cost-performance claims;
- procurement;
- safety/governance approval;
- developer-productivity claims;
- internal release gates;
- routing and policy.

Use model cards, system cards, engineering blogs, maintainer posts, talks, podcasts, GitHub discussions, independent replications, Hacker News, Reddit, forums, and social media. Treat community sources as weak discovery signals unless corroborated. Identify what sophisticated practitioners trust, dismiss, or demand beyond scores.

## Workstream 9: Analyze economics and operational burden

For representative benchmarks, document or estimate:

- task count and runtime;
- API/token, CPU/GPU, container, storage, and CI costs;
- human authoring and validation effort;
- rerun costs from nondeterminism;
- image/dependency maintenance;
- independent reproduction cost;
- whether budgets are standardized or hidden;
- whether cached tokens, retries, subagents, and verifier calls count;
- how rankings change under cost per solved task.

Distinguish cost per call, task, solved task, and accepted/verified engineering change. Assess what can be collected across closed products such as Cursor, Copilot, Claude Code, and Codex.

## Workstream 10: Test transfer to real engineering

Evaluate evidence connecting public scores to:

- unseen and private repositories;
- developer productivity;
- accepted PRs and review effort;
- maintainability and architectural fit;
- security/correctness beyond tests;
- long-horizon reliability;
- different languages, frameworks, and repo maturity;
- real product experience.

Find cross-benchmark, cross-repo, cross-language, cross-harness, and live-workflow comparisons. Determine where rankings are stable or reverse. Specify evidence needed to show repo-specific calibration adds information beyond public benchmarks and generic routing.

## Workstream 11: Map competitors and white space

Map public benchmark operators, private-repo eval platforms, historical-replay/task-generation products, procurement audits, LLM observability, engineering intelligence, PR evidence, model routers/gateways, and agent-governance tools.

For each relevant company/project, capture buyer, use case, task generation, model/harness coverage, metrics, deployment/security, business model, traction evidence, differentiation, likely expansion path, and BenchMe overlap.

Do not assume “private repo benchmark” is sufficient. Evaluate narrower opportunities such as:

- benchmark readiness and capsule validation;
- independent evaluation operations and audit;
- continuous model-harness calibration;
- joining traces to PR/CI/review outcomes;
- verification evidence for AI-authored changes;
- cost per accepted change;
- contamination/security auditing;
- task/risk policy generation;
- evaluation data for routers;
- service-led procurement evidence;
- open-source evaluation infrastructure.

Also identify reasons no attractive company exists.

## Questions the report must answer

1. What are the major benchmark types, and what constructs do they measure?
2. What does a modern coding-agent task contain?
3. How are tasks discovered, validated, executed, graded, maintained, and retired?
4. What is a gold/reference/oracle solution, and when is it useful?
5. Which components are public, private, fixed, or submission-defined?
6. Who runs inference and who runs official evaluation?
7. When is a score about a model versus a full system?
8. How large are harness effects?
9. Which controls improve fairness, and which cripple native products?
10. How are prompts, tools, retries, budgets, network, history, and test feedback controlled?
11. What statistical treatment is appropriate for stochastic agents?
12. How common are broken, flaky, ambiguous, contaminated, saturated, or exploitable tasks?
13. What are the best-documented failures and controversies?
14. How are benchmarks evolving now?
15. How well do rankings transfer to private repos and engineering outcomes?
16. What do different industry actors use scores for?
17. What costs and operational burdens are omitted?
18. What evidence is missing for procurement, governance, security, and routing?
19. Which BenchMe beliefs should be retained, modified, deferred, discarded, or tested?
20. What is the best product interpretation, if any?
21. What should a credible MVP include and exclude?
22. What results would quickly falsify the opportunity?

## Required deliverable

Produce a comprehensive Markdown dossier with these sections.

### 1. Executive synthesis

- 15–25 most important findings.
- Direct answer to the controlling question.
- Confidence and evidence type for every major conclusion.
- What a technically intelligent founder must understand.

### 2. Taxonomy and lifecycle

- Benchmark taxonomy.
- Model/harness/system/workflow evaluation units.
- End-to-end benchmark lifecycle.
- Clear diagrams where useful.

### 3. Evolution timeline

Trace early synthesis benchmarks through repository agents, terminal benchmarks, live/rolling sets, harness-aware evaluation, and private outcome measurement. Mark methodological turning points and controversies.

### 4. Landscape matrix

Compare approximately 15–25 benchmarks using columns such as:

```text
name and version
owner and status
intended construct
task source and freshness
languages, repos, and task count
public/private components
oracle/reference method
inference harness policy
evaluation harness
tools, network, and history policy
budgets and trials
grader and metrics
cost reporting
submission governance
known limitations
industry use
confidence
```

### 5. Deep dives

Provide full benchmark cards for the 8–12 most important benchmark families. Include methodology, code-level observations, operation, economics, incidents, strengths, weaknesses, and appropriate uses.

### 6. Academic literature review

Include search approach, thematic synthesis, paper table, publication status, findings, limitations, consensus, disagreements, and open research questions.

### 7. Harness effects and fairness

Provide controlled evidence, model × harness analysis, native versus normalized evaluation framework, and honest labeling recommendations.

### 8. Contamination and benchmark security

Provide a threat model, incidents, mitigation comparison, residual risks, and recommendations for public-code/private-task evaluation.

### 9. Statistics and economics

Explain appropriate trial design, confidence, cost/efficiency metrics, ranking stability, and minimum reporting standards.

### 10. Industry view and usage

Compare stakeholder perspectives, actual score usage, marketing narratives, independent evidence, and enterprise requirements.

### 11. Competitive landscape and white space

Map crowded layers, under-owned problems, incumbent expansion, and build/partner/avoid choices.

### 12. Implications for BenchMe

Classify every major belief as:

```text
retain
modify
defer
discard
unknown / requires experiment
```

Recommend the optimal product, buyer, use case, evaluation tracks, minimum defensible method, open-source strategy, defensibility, integrations, and what not to build.

### 13. MVP methodology and technical specification

Translate research into:

- task-capsule schema;
- repository/environment manifest;
- model-harness configuration manifest;
- native, single-harness, normalized-context, and augmentation tracks;
- reference/oracle policy;
- isolation and leakage controls;
- trace/patch/test/static/human-review artifacts;
- failure taxonomy;
- statistical repetition policy;
- metrics and report;
- reproducibility and versioning;
- minimal CLI/data model;
- sequence for the next three public-repo demos;
- minimum evidence required before enterprise claims.

Include example schemas or pseudocode.

### 14. Falsification plan

Define fast tests and thresholds that would disprove repo-specific ranking value, buyer demand, scalable task creation, recurring calibration, outcome-join value, or acceptable deployment/telemetry.

### 15. Final recommendation

State pursue, reshape, pause, or abandon; optimal wedge; next 30 days; and top unresolved risks.

### 16. Source ledger and appendices

Include complete bibliography, direct links, source type/date, primary/secondary status, evidence supported, confidence, benchmark repos, paper table, glossary, unresolved questions, and unverified claims.

## Evidence standards

Aim for breadth without padding: approximately 80–150 genuinely useful unique sources if available. Prioritize:

- official benchmark repositories, task definitions, evaluator code, submission rules, and leaderboards;
- original papers and strong follow-ups;
- GitHub issues, PRs, commits, patches, traces, and evaluation artifacts;
- model/system cards and engineering reports;
- independent audits and reproductions;
- talks, interviews, and transcripts;
- credible industry analysis;
- clearly labeled community signals.

Citation rules:

- Cite every material factual claim with a direct link.
- Link the exact paper, code file, issue, leaderboard, or report—not search results.
- Put citations next to claims.
- Include dates where timing matters.
- Mark evidence current as of the research date.
- Show conflicts rather than silently selecting one source.
- Label vendor claims and self-reported scores.
- Do not infer model capability from a system score without naming the harness.
- Do not infer enterprise adoption from integration support.
- Avoid long quotations.
- Explicitly state when a claim is inaccessible or unverified.

Use an evidence grade:

- **High:** official artifacts, independent reproduction, or strongly validated research.
- **Medium:** official methodology/vendor data without reproduction, or credible preprint with limitations.
- **Low:** anecdote, unclear configuration, marketing, or unverified assertion.

Distinguish confidence in a source from confidence in the conclusion.

## Research process

1. Build the taxonomy before selecting deep dives.
2. Select benchmarks by influence and decision relevance, not familiarity.
3. Inspect papers, repositories, evaluator code, task data, metadata, traces, and issues.
4. Snowball citations backward and forward.
5. Search deliberately for criticism, failed reproduction, contamination, exploits, and abandoned designs.
6. Keep incompatible benchmark versions and splits separate.
7. Record model, harness, prompt/tools, budgets, and trials for every interpreted score.
8. Separate facts, inferences, and recommendations.
9. Use tables for systematic comparison and prose for causal reasoning.
10. Prefer uncertainty over false precision.

## Anti-bias requirements

- Do not optimize the conclusion to validate BenchMe.
- Steelman the case that public benchmarks plus generic telemetry are sufficient.
- Steelman the case that private-repo evaluation is too expensive, services-heavy, or copyable.
- Search for both stable and unstable cross-repo/model rankings.
- Consider tooling, service, open-source, evaluation-operations, compliance, data-infrastructure, and “no company” outcomes.
- Identify where our methodology is unnecessarily heavy.
- Do not recommend RAG, orchestration, observability, routing, or dashboards merely because they are technically interesting.

## Final quality bar

The dossier must leave us able to explain, without hand-waving:

- how important coding benchmarks work down to task and evaluator mechanics;
- what every major score does and does not mean;
- why model-harness combinations differ;
- how tasks and submissions are validated and policed;
- how contamination, saturation, economics, and variance alter conclusions;
- what sophisticated practitioners trust;
- how the field is changing;
- which real product opportunities remain;
- exactly how BenchMe's next MVP should be designed—or why it should not be built.

Be comprehensive, critical, technically precise, and willing to change the project direction.

