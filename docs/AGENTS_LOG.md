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

### claude-code agent 2 — 2026-08-12
- **Model / surface**: `claude-opus-5` via Claude Code, with subagents on `claude-opus-5` and
  `claude-sonnet-5`. Council seats on seven models across five labs (see below).
- **Scope**: Continues the 2026-08-10 entry. Decide how tasks are mined, by multi-model council;
  build miner stages 0–2 against `pydantic`; run it; fix what running it exposed.
- **Inputs read**: the 2026-08-10 entry and its artifacts; `screener/metrics.py`, `screener/tierb.py`;
  `docs/PROJECT_KNOWLEDGE_BASE.md`; published task-mining literature (see `docs/council/01_task_mining_facts.md`
  for the sourced figures). **Not read**: `dev_workbench_research_docs/`, `demo/`.
- **Artifacts produced**:
  - `docs/council/` — two council rounds. Motions, per-model raw responses, chaired syntheses.
    `scripts/ask-model.sh` is the dispatch harness.
  - `docs/superpowers/specs/2026-08-11-miner-stages-0-2-design.md` and two plans
    (`2026-08-11-miner-stages-0-2.md`, `2026-08-11-classifier-redesign.md`)
  - `miner/` — enumeration, repo-quarter images, two-pass validation, funnel report. 90 unit tests.
  - `docs/miner/2025Q3-rerun.md` — the known-answer regression against a hand audit
  - Merged to `main` as PR #2 (42 commits, `5f4c15e`)

**The council.** Seven seats, five labs: Opus 5 (chair), Gemini 3.6 Flash, GPT-5.6 Luna, GPT-5.6 Sol,
DeepSeek V4 Flash, Kimi K3, GLM 5.2, Qwen3.8 Max — all at their highest available reasoning effort.
Round 1 ruled on the oracle contract; round 2 revised round 1 on evidence from running the build.

- **Decisions made**:
  - **Round 1 (oracle contract), unanimous**: mutation survival is a reported diagnostic and never a
    gate; no LLM judge decides solved/unsolved; an implementation-sensitive oracle measures style
    rather than capability.
  - **Round 2, 7–0: failure kind labels a capsule, it does not gate one.** Fail-to-pass against the
    genuine upstream fix already establishes the failure was caused by the missing fix, so the
    exception's name adds nothing about validity. The classifier does taxonomy, not validity.
  - **Gate on execution integrity instead**: pytest's own `<failure>` vs `<error>`. An exception raised
    in the *call* phase admits whatever its name; only collection/setup errors are disqualifying.
  - **Three requirements round 1 did not have**, each volunteered by multiple seats: the fail→pass
    transition must reproduce (pass 2 supplies this free — fresh clone, full-suite selection); one
    collection error must not zero unrelated tests (`--continue-on-collection-errors`); a node-ID
    change is a **rename to reconcile, never automatic regression breakage**.
  - **Read pytest through a plugin, not its terminal output.** `miner/reporter_plugin.py` is installed
    into the quarter container and hooks `pytest_runtest_logreport`. It yields node ids verbatim, the
    execution phase, and untruncated messages — and is immune to whatever the terminal reporter does.
    JUnit XML was measured and rejected for this: it carries no `file` attribute, so a node id has to
    be guessed back out of a dotted `classname`.
  - **Alternate implementations are sampled, stratified by failure label** (6–1; the dissent improved
    the rule — a random sample cannot certify a label it never touches).
  - **Composition is a mandatory report section, not an optional analysis**, and mining halts if
    apparatus exceeds 10% of a batch.
- **Measured result** — same 21 candidates, before and after the redesign: **validated 1 → 7**;
  `rejected:other` 4 → 0; `regression_broken` 3 → 1. `eb2c860a` had read *"34 previously-passing tests
  fail after the code patch"* and now records **34 renamed, 0 broken**. **4 of the 9 oracle tests carry
  labels round 1 would have rejected** — the retired rule's cost, measured rather than argued.
- **Conclusions overturned**: 4 rows added to the Contested table, three of them my own.
- **The finding that matters most**: the 2026-08-10 entry recorded that every layer of the screener
  eliminated good candidates for reasons about the tool rather than the subject. The miner repeated it
  exactly, and the numbers are worse than they look. Of the first batch's ten rejections, **seven were
  our defects**. The final whole-branch review then found three more Criticals of the same shape —
  including a crashed pytest session still writing the "session finished" marker, so a truncated report
  parsed as complete. And **my fix for one of them over-corrected in the opposite direction**: it
  discarded a candidate that had collected 869 tests and passed 773. The apparatus rate *rose* 28.6% →
  47.6% across two re-runs, which is the fix working — four candidates moved out of `rejected:*` once
  our own path filters stopped being booked as verdicts about commits.
- **Open questions left**:
  - **`missing_api = 0` is an artifact, not a measurement.** Both batches read zero, and Kimi and GLM
    both flagged zero-in-21 as consistent with a true rate near 14%. It is worse than weak: feature work
    whose test imports a new symbol at *module top level* dies at **collection**, so it never reaches
    the call-level check at all. Verified on `3a7fe26a`, whose new test imports a class the code patch
    adds. Feature work has been in the corpus throughout, filed under "our tooling broke".
  - **A vanished test is being counted as a failed one.** `f7a9b735` books `regression_broken` on
    *"0 previously-passing tests fail … and 7 vanished"*. Both remaining regression rejections are
    docs-example tests parametrised on **line ranges inside markdown files the commit edits**. The
    reconciliation key (`base_id`) lumps every docs file into one bucket, so two genuine deletions
    poisoned the verdict for seven pure renames.
  - **The pass-2 collection-error predicate is deliberately broad.** Narrowing it to the candidate's own
    target files is follow-up; a blanket rule would retire nearly every candidate under dependency drift.
  - **Two cheap enumeration filters are unbuilt**: 105 of 1,568 candidates are pydantic-**core** commits
    grafted into the pydantic clone; and 2 of 21 change the pinned `pydantic-core` version, so their
    before and after states need different environments by construction.
  - **Repo-quarter profiles survive scrutiny — barely, and by luck.** Only 29% of 2025Q3 candidates have
    a parent pinned to the image's `pydantic-core`, which looked fatal; cross-referencing against outcomes
    disproved it (capsules validated at every pin level). The genuine predictor is narrow: commits that
    *change* the pin. Do not re-derive this from the pin distribution alone.
  - **`CONVERSION_RATE` still unvalidated.** 7/11 adjudicated reads 63.6%, but 10 of 21 candidates could
    not be adjudicated at all. Recalibrate only after the filters above land.
  - **Docs-example tests as oracles.** `aa7705f7`'s oracle is a test that checks a documentation snippet
    executes. It is a real fail→pass, but a thin oracle, and pydantic has hundreds. Decide deliberately
    whether they may carry a capsule or belong only in the regression set.
- **Cost / effort**: one extended session; 7 council responses ×2 rounds; ~1.6 M subagent tokens across
  14 subagents (7 implementers, 7 reviewers)

---

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
  Runners-up by diversity tag for repos 2 and 3: `urllib3` (io, 15.51), `click` (cli, 8.98).
  All four Tier A survivors ultimately passed Tier B; `starlette` (io, 8.98) is suppressed only because
  `urllib3` holds the `io` slot at higher yield.
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
  Caveat, stated because it matters: B4's corrected routing is confirmed synthetically and by replaying
  the stored record from the sweep that exposed it, but **B4 has still never fired on live data** —
  no finalist has since produced a network-dependent failure.
- **Open questions left**:
  - **Cross-sweep instability that k=5 cannot see.** `urllib3`'s Tier B verdict flipped across sweeps:
    2 passed, 1 gated. Stated carefully, because an earlier draft of this entry overstated it — most of
    that instability was **our own B4 defect**, and under the corrected code the gated sweep would also
    have passed. The residual finding is still real and still awkward: a pyopenssl HTTP/2 variant failed
    5-of-5 in one sweep having passed in others, so five runs *within* a sweep cannot detect variance
    that lives *between* sweeps. Consistent in direction with arXiv 2602.07150's "36 runs for +1 pp",
    but this is n=3 sweeps on one repo and should not be cited as more.
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
| A capsule's base negative must fail for the *right reason*, and only an assertion failure qualifies; `AttributeError`/`ImportError` mean feature work and are rejected | Council round 1, `docs/council/ROUND_01_SYNTHESIS.md` | **Superseded 7–0** — fail-to-pass against the genuine upstream fix already establishes the failure was caused by the missing fix, so the exception name is taxonomy, not validity. Measured cost of the rule: **4 of 9 oracle tests**, and 50% of the first batch's classified f2p tests, rejected on a parser artefact | Council round 2, `docs/council/ROUND_02_SYNTHESIS.md`. Replacement gates on execution integrity (`<failure>` vs `<error>`) and labels everything else |
| `missing_api` occurs at a rate of zero — the assertion-only rule cost no yield in practice | claude-code agent 2, both 2025Q3 batches | **Artifact, not a measurement** — feature work whose test imports a new symbol at module top level dies at **collection**, so it never reaches the call-level check the rate was computed from. Verified on `3a7fe26a`. Two seats had already flagged zero-in-21 as consistent with ~14% | claude-code agent 2, 2026-08-12. The rate must be recomputed at the collection layer before it means anything |
| The first batch's 10 apparatus cases were 8 × `tests/typechecking/` fixtures and 2 grafted pydantic-core commits | claude-code agent 2's own hand audit, 2026-08-11 | **Wrong on both counts** — the real causes were `tests/mypy/` fixtures, pydantic-core version skew, commits from a *different project* grafted into the clone, and warning-as-error at import. The audit also mis-called one of four `other:unparsed` rejections as a false rejection when the candidate has a genuine regression | claude-code agent 2, 2026-08-12, `docs/miner/2025Q3-rerun.md`. **The redesign is validated by execution, not by that audit** |
| A pass-1 collection error means the candidate could not be measured, so book `apparatus` | claude-code agent 2's own fix, 2026-08-12 | **Over-corrected** — `aa7705f7` had 869 tests collected and 773 passing, and was discarded because 2 of its 4 touched files failed to import. The reviewer had warned in the same review that over-correcting into `apparatus` is also a defect, because `apparatus` is terminal | claude-code agent 2, same day. Correct rule: a collection error matters only when it leaves us **unable to conclude** |

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
| `screener/FUTURE_WORK.md` | claude-code agent 2 | Parked screener backlog. Top item: `sqlalchemy`, 4,098 candidate pairs, eliminated only on unpinned requirements — possibly a detector gap |
| `docs/council/01_task_mining_facts.md` | claude-code agent 2 | **Read before any oracle decision.** How SOTA benchmarks mine tasks, with sourced figures: 2.2% honest yield, 77.0% of SWE-bench Verified admit a wrong patch, ≥59.4% have flawed tests |
| `docs/council/ROUND_01_*.md` + `round01/` | claude-code agent 2 + 7 council seats | Oracle contract. Motion, seven raw responses, chaired synthesis |
| `docs/council/ROUND_02_*.md` + `round02/` | claude-code agent 2 + 7 council seats | **Supersedes round 1's base-negative rule 7–0.** 14 numbered decisions in the synthesis table |
| `scripts/ask-model.sh` | claude-code agent 2 | Council dispatch across five labs. Records two live workarounds (a codex-cli config parse failure, a validated-but-nonexistent `CODEX_BIN`) |
| `docs/superpowers/specs/2026-08-11-miner-stages-0-2-design.md` | claude-code agent 2 | Miner design: quarter images, two-pass validation, the rejected/apparatus/error split |
| `docs/superpowers/plans/2026-08-11-miner-stages-0-2.md` | claude-code agent 2 | 7-task plan for the miner |
| `docs/superpowers/plans/2026-08-11-classifier-redesign.md` | claude-code agent 2 | 7-task plan implementing council round 2 |
| `miner/` | claude-code agent 2 | Stages 0–2. `outcomes.py` is the pure core; `reporter_plugin.py` runs *inside* the container and is never imported by the miner |
| `miner/out/REPORT.md` | claude-code agent 2 | Funnel, oracle composition by failure label, apparatus tripwire |
| `docs/miner/2025Q3-rerun.md` | claude-code agent 2 | Known-answer regression: 1 → 7 validated, and an honest account of which predictions failed |

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
6. **A failure of the apparatus must never be recorded as a verdict about the subject.** Learned twice
   at cost — the screener eliminated 6 of 7 repos on its own defects, and 7 of the miner's first 10
   rejections were ours. Keep the three statuses rigidly apart: `rejected:*` is a verdict about the
   subject, `apparatus` is our tooling failing, `error` is a bug and is **non-terminal** so the
   candidate returns after a fix. Two corollaries, both paid for: an empty result is not a verdict —
   if nothing parsed, say so rather than concluding "nothing changed"; and **over-correcting is also a
   defect**, because `apparatus` is terminal and silently shrinks the corpus. When something fails,
   the apparatus is the leading hypothesis, not the fallback.
