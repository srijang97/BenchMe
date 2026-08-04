# Repo Benchmarking and PoC Blueprint

## 1. What we mean by repo benchmarking

Repo benchmarking is not “run SWE-bench on everything.”

It means:
- evaluating AI tools/models/agents on tasks that matter for a specific repo or class of repos,
- measuring not just quality but cost/latency/review burden,
- and using the result to drive procurement, workflow policy, or routing.

## 2. Benchmarkability ladder

Not every repo can support the same benchmark depth.

### Level 0 — Repo intelligence only
Tasks:
- file discovery
- subsystem summary
- codebase Q&A
- issue-to-plan
- PR summary

Pros:
- works on most repos
- no full environment needed
- great first PoC

### Level 1 — Static / review benchmark
Tasks:
- historical PR review
- review comment comparison
- risk classification
- test suggestion
- security/static review

Pros:
- useful without full execution
- directly relevant to verification

### Level 2 — Current-head executable benchmark
Tasks:
- run tests at HEAD
- generate tests
- make small edits
- verify with CI/devcontainer/Docker

Pros:
- much stronger signal
- still easier than historical replay

### Level 3 — Historical replay benchmark
Tasks:
- recreate historical bugfix or issue-to-patch task
- run tests on pre-fix commit
- compare generated patch against hidden fix / expected behavior

Pros:
- strongest benchmark for coding agents
Cons:
- environment complexity much higher

### Level 4 — Curated golden benchmark
Tasks:
- customer-curated important workflows
- hidden oracles
- risk classes
- benchmark capsules

Pros:
- highest business relevance
Cons:
- requires curation / customer cooperation

## 3. Why this is different from public benchmark scores

If we only rerun the same public SWE-bench tasks, the difference versus vendor claims is limited.

The real differentiation comes when we add:
- multi-tool neutral comparisons
- cost and latency metrics
- PR review and test-generation tasks
- repo-intelligence tasks
- customer/private repo evaluation
- procurement recommendations
- routing/policy implications

## 4. Benchmark capsule concept

A benchmark capsule is a portable task definition:

```yaml
id: repo_task_001
repo: org/project
base_sha: abc123
task_type: bugfix
prompt: "Users are charged after cancelling trial subscriptions..."
setup:
  env: devcontainer
  commands:
    - pnpm install
    - pnpm db:test:reset
verify:
  commands:
    - pnpm test billing
    - pnpm typecheck
risk_class: payments
forbidden_paths:
  - infra/prod/**
  - secrets/**
```

The long-term benchmark engine should generate, store, and score these capsules.

## 5. Practical PoC path

### Step 1 — Start with public repos only
Do not start with arbitrary private enterprise repos.

Use repos with:
- tests
- CI
- issue/PR history
- Docker/devcontainer or straightforward setup
- medium complexity

### Step 2 — Run 3 task families
1. repo understanding
2. verified code edits
3. PR review

### Step 3 — Compare multiple tools/models
Examples:
- Claude Code
- Codex
- Aider
- OpenCode
- Cline
- OpenHands
- cheap hosted open models
- local/open models
- PR reviewers where possible

### Step 4 — Score
Metrics:
- success
- cost
- latency
- retries
- human intervention
- false positives
- tests passed
- accepted output quality

## 6. Public repos to start with

### Python / benchmark-friendly
- django/django
- pytest-dev/pytest
- psf/requests
- pallets/flask
- scikit-learn/scikit-learn
- sphinx-doc/sphinx
- sympy/sympy
- pylint-dev/pylint

### JS/TS
- eslint/eslint
- expressjs/express
- prettier/prettier
- vitejs/vite
- selected Next.js example or moderate app repo

### Go / Rust / Java
- gin-gonic/gin
- prometheus client libs or smaller Go systems
- rust-clippy or another well-tested Rust project
- spring-projects/spring-petclinic

### App-like repo
- cal.com
- plausible
- another open-source SaaS repo if feasible

## 7. What to avoid initially

Avoid:
- giant monorepos
- infra/cloud-heavy repos
- mobile-only repos
- poorly tested repos
- repos requiring private datasets or secrets
- highly visual apps needing complex browser/device simulation

## 8. Who is already doing related work

- codeprobe
- Sigmabench
- Factory Agent Readiness
- Sourcegraph CodeScaleBench
- OpenHands evaluation harness
- Qodo public benchmark / scanner
- OpenHands Index
- CodeReviewBench

This validates the direction but also means the PoC must be honest about where it is differentiated.

## 9. Best initial PoC story

The best PoC story is:

> “We benchmark multiple AI coding tools and reviewers on a selected public portfolio, measure quality + cost + latency + review burden, and show that rankings differ by workflow and repo.”

That is stronger than:
> “We ran one benchmark and got one score.”

## 10. Long-term progression

1. Public benchmark-friendly portfolio
2. Deeper task classes on same repos
3. Holdout tasks from same repos
4. Private repo benchmarkability audit
5. Private repo benchmark
6. Procurement recommendation
7. Runtime evidence / routing / governance
