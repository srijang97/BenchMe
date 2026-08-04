# BenchMe coding-benchmark research: executive decision brief

**Research date:** 2026-07-10  
**Full analysis:** `BENCHME_CODING_BENCHMARKS_RESEARCH_DOSSIER_2026-07-10.md`  
**Companions:** benchmark landscape, 123-source ledger, and implementation-ready MVP schema bundle

## Decision in one paragraph

**Pursue, but reshape the product around evaluation assurance and continuous calibration—not “private repo benchmarking” alone.** Public coding benchmarks remain useful for screening broad capability, research regression, and model development. They are not sufficient evidence for a close procurement choice, a private-repository deployment policy, or production acceptability. The scored object in agentic coding is the complete configuration—model, harness, prompt/context, tools, permissions, budget, environment, verifier, and trial—not the model name. BenchMe’s best first product is a local-first, service-assisted decision audit that produces validated task capsules, separates native-product from controlled comparisons, applies leakage and verifier-security controls, repeats trials, and explains what a team should buy, configure, permit, or keep human-led.

## What changed after the research

### Retain

- Public benchmark scores do not answer a private-repository procurement question by themselves.
- Harness/context/tooling effects are first-class and must be versioned.
- Native-product and controlled comparisons answer different questions and must remain separate.
- Generic routing consumes evidence; it does not create trustworthy software-engineering outcome labels.
- Verification and reviewer attention are more durable problems than raw token pricing.
- A local-first runner is the right trust posture for private source code.

### Modify

- **From “repo benchmark” to “evaluation assurance.”** Historical replay and hidden tests are already available from new competitors. The defensible method is proving that tasks, environments, verifiers, information policies, and interpretations are valid.
- **From automatic mining first to manual golden capsules first.** Candidate mining is feasible; validating representative, leakage-resistant, solvable tasks with adequate oracles is the expensive and differentiating step.
- **From one leaderboard to multiple evidence tracks.** Native product, fixed-harness model, controlled intervention, augmentation, and live outcome results cannot be blended honestly.
- **From test pass to verifier-qualified evidence.** A green result means “passed this versioned verifier,” not “good production engineering.”
- **From recurring re-benchmarking as an assumption to a hypothesis.** It becomes a subscription only if real model/harness/configuration changes repeatedly alter decisions.

### Defer

- RAG/context augmentation until the native baseline and capsule/oracle pipeline are trustworthy.
- LangGraph until durable pause/resume and human approval make plain Python orchestration painful.
- General observability dashboards; export to OpenTelemetry/Langfuse/LangSmith rather than making them the source of truth.
- Routing policy generation until the system has enough validated task-level evidence.
- PR evidence packs until BenchMe has methodological credibility and live provenance access.

### Discard

- A generic router, gateway, IDE, worktree orchestrator, PR-review commenter, or public model leaderboard as the company wedge.
- A single “BenchMe score.” It destroys information and invites gaming.
- Claims about developer productivity from offline agent pass rates.
- GUI automation as a core benchmarking method.

## Fifteen decision-critical findings

1. **The complete configuration is the evaluated unit.** Harness-Bench analyzed 5,194 trajectories on 106 tasks and argues for model–harness reporting. Claw-SWE-Bench reports a fixed GLM 5.1 backbone moving from 19.1% to 73.4% Pass@1 under a different adapter; its sweeps found model and harness choices produced similarly large variation. These are recent preprints, but the methodological conclusion is strongly corroborated by Aider, SWE-agent, Databricks, and vendor system-card disclosures.

2. **There is no neutral harness.** A fixed harness improves causal control but may suppress native retrieval, editing, compaction, and recovery behavior that buyers actually purchase. Native evaluation improves ecological validity but cannot isolate the base model. Both are legitimate; neither substitutes for the other.

3. **Harness versions can drift without obvious score gains.** A July 2026 longitudinal study held the LLM fixed across 35 Qwen Code CLI releases and found no statistically significant resolve-rate improvement while later versions nearly doubled token/tool use. Exact harness version and efficiency are therefore part of configuration identity, not metadata.

4. **Tests are necessary but incomplete specifications.** UTBoost found 345 incorrect generated patches accepted by original SWE-bench tests and materially changed leaderboard ordering after adding tests. BenchMe Demo 01 independently reproduced the issue: the first hidden-test suite accepted a backward-incompatible change until human review and a new regression oracle corrected the task.

5. **Positive and negative controls are mandatory.** A valid capsule should establish a healthy base, target failure before the change, reference success after it, preservation of regressions, and ideally rejection of no-op/near-miss patches. A reference solution is a positive control, not a gold code shape candidates must imitate.

6. **Expert curation does not make a benchmark permanently valid.** SWE-bench Verified used three expert reviewers per candidate, yet OpenAI’s 2026 audit of a selected hard subset found material prompt/test defects in 59.4%. Its separate public SWE-Bench Pro campaign found 249 of 731 public tasks breaking. The exact rates should not be generalized beyond the audited samples, but the governance lesson is decisive: tasks require incident response, versioning, quarantine, and retirement.

7. **Runtime retrieval is a different contamination channel from training exposure.** Cursor’s SWE-Bench Pro audit found many successful trajectories retrieved known fixes through the web or future Git history. Historical public-task evaluation therefore needs sealed history, default-deny egress, outbound logging, and trajectory sampling.

8. **A fresh unpublished task on public code is a strong middle ground, not a contamination cure.** It sharply reduces exact issue/patch retrieval and direct benchmark overfitting. Residual risks include repository familiarity, prior architecture exposure, dependencies, and task similarity. Label it precisely: “fresh private task on public code under sealed runtime conditions.”

9. **Public benchmarks are screening instruments.** HumanEval/MBPP measure compact synthesis; LiveCodeBench measures contemporary algorithmic coding; RepoBench/CrossCodeEval measure context retrieval/completion; SWE-style sets measure issue-to-patch systems; Terminal-Bench measures stateful terminal agents. Their ranks cannot be safely transferred across constructs.

10. **Private evaluation is already an engineering practice.** Databricks reports using reviewed internal tasks to choose model/harness tiers and found more than 2× cost differences for the same model/thinking effort under different harnesses. Google evaluates internal code repair with human semantic review beyond tests. Sigmabench and Stet validate the commercial category.

11. **Task mining is not the principal moat.** SWE-Smith, SWE-bench Live, R2E-Gym, RepoGauge/codeprobe-like tooling, and historical-replay systems demonstrate candidate generation. Environment reconstruction, oracle assurance, leakage defense, and statistical interpretation remain hard.

12. **Context can improve, degrade, or merely increase cost.** A generated context pack must be a hash-addressed intervention. Report native performance, context uplift, and cost separately. Start by testing lexical/symbol/dependency methods independently before adding embeddings or a broad RAG stack.

13. **One trial is a case study.** Use task-paired repeated trials, preregistered stopping rules, uncertainty intervals, and “indistinguishable” language for near ties. Report scientific capability and operational reliability separately: infrastructure-invalid runs should not be blamed on reasoning, but deployment-relevant harness failures should not be rerun out of existence.

14. **Cost per solved task is the first defensible economic metric.** Token price omits exploration length, retries, cached input, verifier calls, subscription accounting, and human review. Cost per accepted change requires later live attribution and should not be claimed from an offline harness.

15. **The white space is methodological trust plus decision interpretation.** Sigmabench, Stet, RepoGauge, Factory, public benchmark operators, gateways, and engineering-intelligence platforms cover adjacent pieces. BenchMe must distinguish itself through task/oracle assurance, native capability manifests, benchmark security, intervention ablations, reproducibility, and an actionable decision report.

## Optimal first product

### Buyer

An AI-forward organization with approximately 50–500 engineers that uses at least two coding-agent configurations and faces a renewal, standardization, open-model, cost, or governance decision. The champion is the staff/principal engineer already performing informal bakeoffs. The buyer is a VP Engineering, CTO, or platform/DevEx leader; security is initially a gate and later a buyer.

### Job to be done

> Before we standardize or expand AI coding, show us which configurations work on representative tasks from our repositories, what the verified cost and failure profile are, and what controls or human review are required.

### Product boundary

BenchMe should own:

- benchmarkability assessment;
- capsule authoring/mining and validation;
- versioned native capability manifests;
- isolated native-agent execution;
- clean deterministic verification plus human engineering review;
- repeated-trial statistics and cost attribution tiers;
- decision reports and later configuration-regression alerts.

BenchMe should integrate with, not replace:

- coding agents and IDEs;
- gateways/routers;
- CI and source control;
- OpenTelemetry and LLM trace platforms;
- static/security analysis tools.

## Minimum credible MVP

1. **One ecosystem:** Python + pytest in a reproducible container.
2. **Eight to twelve manually authored or carefully curated capsules** from one public repository, each with base-fail/reference-pass controls and O2/O3 oracle assurance.
3. **Two adapters:** Codex CLI and Claude Code. Add Aider or OpenCode only after adapter conformance and end-to-end stability.
4. **Two initial tracks:** native-product and standardized-task. Add a versioned context-pack intervention only after the native report is trustworthy.
5. **Isolation:** archive-to-single-commit workspace, no future history, default-deny egress, package setup separated from inference, hidden verifier absent during inference, outbound ledger.
6. **Artifacts:** exact configuration manifest, JSONL trace, patch, Git status, verifier log, cost tier, human review, hashes.
7. **Statistics:** three trials per decision-grade cell where affordable, paired analysis, confidence intervals, near-tie rule, sequential elimination of clearly dominated configurations.
8. **Report:** verified solve, regressions, operational reliability, time, cost per verified solve, failure decomposition, human-review findings, Pareto views, recommendation, and explicit non-claims.

The companion `BENCHME_MVP_SCHEMAS_2026-07-10.yaml` makes these objects concrete.

## Next three demos

### Demo 02 — capsule and adapter conformance

Use trivial and adversarial tasks to verify workspace write access, timeout behavior, network denial, hidden-test absence, forbidden-path enforcement, patch capture, and identical failure semantics across Codex and Claude Code. Do not publish agent rankings.

### Demo 03 — repeated native-product comparison

Run 8–12 validated Python maintenance tasks with two native products, three trials per task where feasible. Publish configuration cards, task validity evidence, uncertainty, operational failures, and blinded human review. The headline should be a methodological teardown, not “best model.”

### Demo 04 — controlled context intervention

On the same task set and one pinned baseline configuration, compare native context with a frozen symbol/lexical/dependency context pack and then one controlled repair cycle. Measure absolute solve uplift, task-level reversals, token/time changes, and failure-mode shifts. This directly tests whether a BenchMe augmentation layer is worth building.

## Fast falsification thresholds

Pause or pivot if several of these occur:

- fewer than 8 strong capsules can be produced from normal target repositories without disproportionate manual labor;
- repeated task-level ranks are stable across repositories/configurations and never change a real decision;
- buyers say a short vendor pilot plus existing telemetry is sufficient and 0 of 10 scoped audit offers convert for reasons other than price/timing;
- local execution and required telemetry are unacceptable to most target customers;
- continuous re-calibration fails to retain interest through two meaningful model/harness release cycles;
- oracle assurance and environment maintenance make gross margins unattractive;
- an incumbent ships neutral, local, configuration-to-outcome evidence with equivalent methodological trust.

## Final recommendation

**Build the evaluation core and sell the decision report, not the platform story.** BenchMe has a plausible and technically serious wedge if it becomes the trusted layer that certifies what an AI-coding evaluation actually means. The near-term career signal is also strong: the project demonstrates agent adapters, sandboxing, benchmark security, deterministic and human evaluation, experimentation, statistics, cost instrumentation, and customer-facing interpretation. The largest risk is not technical feasibility; it is whether evaluation assurance changes enough real buying and policy decisions to sustain recurring revenue.
