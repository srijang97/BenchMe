# BenchMe — Agent Contribution Log

Central register of AI-agent work on this project. **Every agent session that produces a durable
artifact or a decision MUST append an entry here before finishing.** Read this file first, before
doing anything else — it tells you what already exists, what was decided, and what is contested.

---

## How to use this file

**Before starting work**
1. Read this log top to bottom. It is ordered newest-first.
2. Read the handoff document of the most recent agent whose scope overlaps yours.
3. Check the **Contested / Superseded** table before acting on any earlier conclusion.

**Before finishing work**
1. Append an entry using the template below. Newest entries go at the top of the Session Register.
2. If you overturned an earlier conclusion, add a row to **Contested / Superseded**.
3. If you produced a durable artifact, add it to the **Artifact Index**.
4. Never edit another agent's entry. Supersede it with a new one and cross-reference.

**Agent naming**: `<surface> agent <n>` — e.g. `cowork agent 1`, `claude-code agent 1`,
`codex agent 1`. Increment `n` per surface. Record the model you ran on; conclusions are not
model-independent.

**Entry template**

```markdown
### <agent-id> — <YYYY-MM-DD>
- **Model / surface**: <e.g. claude-opus-5 via Cowork>
- **Scope**: <one line — what you were asked to do>
- **Inputs read**: <files, dirs, external sources>
- **Artifacts produced**: <paths, relative to repo root>
- **Decisions made**: <bulleted, each one actionable>
- **Conclusions overturned**: <what you disagreed with and why, or "none">
- **Open questions left**: <what the next agent must resolve>
- **Cost / effort**: <rough, if known>
```

---

## Session register

### cowork agent 1 — 2026-08-08
- **Model / surface**: `claude-opus-5` via Cowork (remote sandbox + device bridge)
- **Scope**: (1) Analyse all prior research and simplify what to keep, rethink, discard.
  (2) Explain benchmarking mechanics in depth. (3) Build a real cost model on live API rates.
  (4) Analyse the 2026-07-10 benchmark dossier and complete it with missing state-of-the-art.
  (5) Strategy: validation → MVP → funding path for a solo founder.
- **Inputs read**:
  - `research/` — all 14 numbered docs + `research/claude/agent-eval-ci-teardown.md`
  - `docs/` — `PROJECT_KNOWLEDGE_BASE.md`, `CODING_BENCHMARKS_DEEP_RESEARCH_PROMPT.md`,
    `DEMO_01_CODEX_ITS_DANGEROUS.md`
  - `benchme_coding_benchmarks_research_2026-07-10/` — full dossier (183 KB), exec brief,
    landscape CSV, MVP schemas
  - ~60 external web sources; live API pricing verified 2026-08-04
  - **Not read**: `dev_workbench_research_docs/`, `demo/` source (only its documentation)
- **Artifacts produced**:
  - `research/claude/COWORK_AGENT_1_HANDOFF.md` — full brain dump, **read this**
  - `research/claude/benchmark_methodology_report.html` — methodology analysis + completion
  - `research/claude/cost_model/costmodel.py` — runnable cost model
  - `research/claude/cost_model/results.json` — computed outputs
  - `research/claude/cost_model/benchme_cost_calculator.html` — interactive calculator
  - `research/claude/cost_model/charts.py` + 3 PNG charts
  - `docs/AGENTS_LOG.md` — this file
- **Decisions made**:
  - **Routing is dead.** Cut entirely, not "third party at start". Includes policy artifacts.
  - **Reframe as verification/CI for the agent stack**, not benchmarking. Budget line matters.
  - **Environment reuse, not synthesis** — snapshot the customer's existing CI container.
  - **Oracle hardening (mutation + differential + alternate-solution) is the differentiator.**
  - **Verified wedge over judged wedge** — config regression, not AI-code-review replication.
  - **Target segment reranked**: cost-aware / gateway-instrumented orgs first, harness vendors
    second, regulated on-prem third, enterprise monorepo fourth (was first).
  - **Cost objection dissolved** — prior estimates were ~10–20× too high (ignored prompt caching).
  - **Task mining: automate the evidence, not the decision** — scored funnel + calibrated
    three-band human triage.
  - **Open-core split**: capsule format, miner, validator, triage queue open source; config grid,
    statistics, cross-customer priors, reporting commercial.
- **Conclusions overturned**: see Contested / Superseded table below (6 entries)
- **Open questions left**:
  - Actual prompt-cache hit rate for Codex and Claude Code — measurable from JSONL traces, one
    afternoon of work, replaces the largest assumption in the cost model.
  - Real capsule yield and curation cost on a repo not controlled by the author.
  - Whether mutation survival is a valid ranking signal on BenchMe's own capsules
    (ISSTA 2026 casts doubt in the defect-detection setting).
  - Whether the routing-counterfactual finding reproduces on public repos (~$150 experiment).
- **Cost / effort**: one extended session; ~340 k subagent tokens across 5 research subagents

---

## Contested / superseded

| Earlier claim | Source | Status | Superseded by |
|---|---|---|---|
| Full sweep costs $6–12 k; ~$300–600 k/yr compute for one customer | `research/claude/agent-eval-ci-teardown.md` §VIII | **Wrong** — priced all input at list rate, ignored prompt caching (3.4× lever) | cowork agent 1: ~$4.9 k/sweep, ~$93 k/yr enterprise. `cost_model/results.json` |
| Start with the AI-code-review wedge (DashBench replica) | teardown §IV.3 | **Contested** — contradicts the same doc's "execution-based primary, refuse the LLM judge" doctrine | cowork agent 1: verified wedge preferred; see handoff §3 |
| Enterprise monorepo (500–2,000 eng) is the primary target | teardown §IV.4, research `08_gtm` | **Reranked to 4th** — worst ratio of unmeasured variance to access friction | cowork agent 1 handoff §4 |
| "30–60% per-repo variance" as a load-bearing fact | `research/01`, `research/09` | **Do not cite** — sourced from Sigmabench, a vendor selling repo evals | Already flagged in `PROJECT_KNOWLEDGE_BASE.md` banned-claims list; reaffirmed |
| Routing as Phase 3 via gateway partners | `research/03`, `research/09` | **Cut entirely** | cowork agent 1 handoff §2 |
| `codeprobe` is a competitor | `research/02` | **Could not be verified to exist** — no company, product, repo or paper found | cowork agent 1 competitive sweep 2026-08-08 |
| Task yield 10–50 capsules/repo (unsourced) vs 50–200 needed | `research/00`, `research/04`, `research/06` — mutually inconsistent | **Resolved** — 2.2% conversion from raw commit pairs is the published figure; and 30 tasks × k=5 gives a defensible ~12.5 pp MDE | cowork agent 1 handoff §5, §6 |

---

## Artifact index

| Path | Produced by | What it is |
|---|---|---|
| `research/claude/COWORK_AGENT_1_HANDOFF.md` | cowork agent 1 | Full session brain dump — decisions, findings, build queue |
| `research/claude/benchmark_methodology_report.html` | cowork agent 1 | Methodology analysis; 34 systems the July dossier missed |
| `research/claude/cost_model/costmodel.py` | cowork agent 1 | Runnable cost model, live API rates as of 2026-08-04 |
| `research/claude/cost_model/results.json` | cowork agent 1 | Computed scenarios, sensitivity, build-side costs |
| `research/claude/cost_model/benchme_cost_calculator.html` | cowork agent 1 | Interactive calculator, self-contained |
| `research/claude/agent-eval-ci-teardown.md` | prior claude session | Strategic teardown, 2026-08-04. Strong except §VIII (costs) |
| `research/00`–`11` + `research/_raw/` | prior researcher | Market/competitive research, 2026-07-05. See caution list |
| `benchme_coding_benchmarks_research_2026-07-10/` | prior researcher | Benchmark methodology dossier, 123 sources, 27 families |
| `docs/PROJECT_KNOWLEDGE_BASE.md` | founder + agents | **Controlling doctrine.** Oracle ladder, tracks, manifests, gates |
| `docs/DEMO_01_CODEX_ITS_DANGEROUS.md` | founder | The empirical anchor. Read before touching `demo/` |

---

## Standing rules for all agents

1. **Do not add research.** The project is over-researched and under-built. If your output is a
   document rather than code or a measurement, justify it explicitly in your log entry.
2. **Never cite the banned-claims list** in `PROJECT_KNOWLEDGE_BASE.md` §external-claims without
   re-verification: market-size and ARR figures from aggregators, the 30–60% variance figure,
   EU-law compliance requirements, routing/subagent savings, any "no competitor does X".
3. **Absence of evidence from a search sweep is weak evidence.** The July research graded
   "nobody does this" as [HARD] from 15 searches. Do not repeat that error.
4. **Single-run results are case studies, not rankings.** Published noise floor is 2.2–6.0 pp
   (arXiv 2602.07150). Anything smaller than your MDE is `indistinguishable`.
5. **Corrections create a new version.** Never rewrite a task, capsule or result in place.
