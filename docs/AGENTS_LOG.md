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

### claude-code agent 2 — 2026-08-10
- **Model / surface**: `claude-opus-5` via Claude Code, with subagents on `claude-opus-5` and `claude-sonnet-5`
- **Scope**: Select, by measurement rather than judgement, the public Python repo BenchMe builds its
  first evaluation corpus against. Build the screener that does it.
- **Inputs read**: `docs/AGENTS_LOG.md`; `research/00`–`11`; `research/claude/` (teardown, methodology
  report, cost model); `research/claude/COWORK_AGENT_1_HANDOFF.md`; `docs/PROJECT_KNOWLEDGE_BASE.md`;
  `docs/DEMO_01_CODEX_ITS_DANGEROUS.md`; `demo/` layout. **Not read**: `dev_workbench_research_docs/`.
- **Artifacts produced**:
  - `docs/superpowers/specs/2026-08-10-repo-screener-design.md` — design, with two recorded retractions
  - `docs/superpowers/plans/2026-08-10-repo-screener.md` — 9-task implementation plan
  - `screener/` — two-tier screener. **`metrics.py` is the harvestable stage-0 rule set**
  - `screener/out/REPORT.md` + `tier_a.jsonl` / `tier_b.jsonl` — gate ledger and measurements, 18 repos
- **Decision — corpus repo is `pydantic`**, 35.13 projected capsules, passing all four Tier B gates
  (6,884 tests, 0 deterministic failures, 1 recorded skip, flake rate 0.0, hardening 2.77 h).
  Runners-up by diversity tag for repos 2 and 3: `starlette` (io, 8.98), `click` (cli, 8.98).
- **Decisions made**:
  - First artifact varies the **model-tier** axis (segment 1). At MDE ≈12.5 pp, frontier-vs-frontier
    (~3 pp) and prompt-level (~2 pp) effects are not observable, so only tier-scale effects qualify.
  - **Top-1 corpus now**; a diversity tag is recorded so repos 2–3 need no re-run.
  - **Gate-and-rank on a single key**, `projected_capsules`. No composite score, per `PROJECT_KNOWLEDGE_BASE.md` §12.
  - **Freshness ranks, does not gate** — a fresh-only gate eliminates the entire field.
  - **Three Tier A gates withdrawn on evidence** (G4, G5, G6 — see Contested table). Ids retired, not reused.
  - **Tier A gates only on what Tier B cannot measure**: ecosystem, volume, freshness, determinism.
    Environment feasibility is settled by building, not predicted from filenames.
  - **A recorded skip list is legitimate** and was used once: pydantic's `test_public_internal` exercises
    its own mypy-plugin internals at the mypy version its lockfile pins — tooling hygiene, not library
    behaviour. Configured per-repo in `candidates.yaml` with a reason; a stale skip fails loudly.
- **Conclusions overturned**: see Contested table — 4 entries, two of which are my own retractions.
- **The finding that matters most**: every layer of this tool, on first contact with real repositories,
  eliminated good candidates for reasons that were about the tool rather than the repository — and each
  emitted a confident, specific, checkable-sounding justification. Three Tier A gates withdrawn; a
  transient network drop recorded as `error` nearly discarded the second-highest-yield repo; my own
  pytest invocation (`-v` with `-q`) would have parsed zero tests and fabricated a flake rate; a nodeid
  regex missed 1,604 of 1,977 tests; containers running as root manufactured a permission-test failure;
  `core.autocrlf` injected CRLF that broke string comparisons; bind-mount shadowing produced zero
  collected tests twice. **Gate B4 was unreachable by construction** — its input set could only be
  non-empty when B2 had already eliminated the repo — so the repo it existed to rescue was eliminated
  with a reason pointing elsewhere. I had triaged that as a deferred minor; the final review caught it.
- **Open questions left**:
  - **k=5 does not stabilise a binary verdict.** `urllib3` returned three different Tier B outcomes
    across three sweeps on an unstable pyopenssl HTTP/2 test. Correcting B2 from 1-of-5 to 5-of-5 raised
    the bar without removing the coin flip. Independent echo of arXiv 2602.07150's "36 runs for +1 pp".
  - **The fresh stream is ~4× thinner than estimated**: `projected_fresh` is 0.77 (pydantic) and 0.81
    (click) — under *one* contamination-resistant capsule per repo. Contamination is effectively
    unavoidable for this corpus; report the fresh/stale split beside every downstream result.
  - **2.2% conversion is unvalidated here** and gates G2 on it. `jinja` missed by 26 pairs. Recalibrate
    after the miner's first real run; several eliminated candidates may return.
  - **The corpus cannot speak to application-shaped code.** Both application probes were eliminated
    (`pre-commit` G3, `mkdocs` G1); all survivors are libraries. The spec committed to reporting this.
  - Uniform zero-collection is misclassified as an apparatus error rather than a real `gated:B2`
    (parked: cannot cause false admission, unexercised by the current field).
- **Cost / effort**: one extended session; ~2.0 M subagent tokens across 13 subagents

---

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
| Demo 01's repo-selection criteria: "small enough to understand in one evening, fast, deterministic" | `docs/DEMO_01_CODEX_ITS_DANGEROUS.md` §1 | **Superseded** — those select a development *rig*, not a corpus. Used for a corpus they produced 3/3 solved (zero discrimination) on a 36-file repo that cannot exhibit a harness effect at all | claude-code agent 2: spec §1. New rule: **repo size sets a floor on which effects are observable** |
| `test_map_ratio` predicts whether targeted test selection is possible (gate G4) | claude-code agent 2's own spec, 2026-08-10 | **Withdrawn same day** — it measures whether tests are *named* after source modules. `pytest tests/test_basic.py::test_x` runs regardless, and a capsule's fail-to-pass tests come from the mined commit itself. Eliminated 3 of 3 trial repos on normal feature-based naming | claude-code agent 2, after the first live sweep |
| Filename scanning predicts environment feasibility (gates G5, G6) | claude-code agent 2's own spec, 2026-08-10 | **Withdrawn same day** — both scanned the whole repo tree while describing the primary package's build path, so vendored subprojects and peripheral CI tripped them. Both also *predicted* what Tier B *measures* | claude-code agent 2. Tier A now gates only on what Tier B cannot measure |
| "Installing pydantic compiles no Rust" → corrected to "the lockfile requires a Rust toolchain" | claude-code agent 2's own spec, 2026-08-10 | **Correction retracted** — the real cause was bind-mount shadowing; `_pydantic_core.so` was in the image and no toolchain was ever needed. The correction was worse than the original error because it dressed a misdiagnosis as evidence | claude-code agent 2. Operating rule recorded: **when a candidate fails, the apparatus is the leading hypothesis, not the fallback** |
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
| `docs/superpowers/specs/2026-08-10-repo-screener-design.md` | claude-code agent 2 | Corpus selection: gates, metrics, candidate set. Records 3 gate withdrawals and 2 retractions |
| `docs/superpowers/plans/2026-08-10-repo-screener.md` | claude-code agent 2 | 9-task implementation plan, amended in flight |
| `screener/` | claude-code agent 2 | Two-tier screener. **`metrics.py` is the harvestable stage-0 rule set** for the miner |
| `screener/out/REPORT.md` | claude-code agent 2 | Gate ledger + measurements for 18 candidates. Corpus decision: `pydantic` |

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
