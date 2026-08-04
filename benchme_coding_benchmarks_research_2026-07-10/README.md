# BenchMe coding-benchmark research package

**Research date:** 2026-07-10  
**Scope:** coding-model and coding-agent benchmark design, mechanics, security, harness effects, statistics, economics, industry use, product white space, and BenchMe MVP design.

## Start here

1. **`BENCHME_EXECUTIVE_BRIEF_2026-07-10.md`** — founder decision brief and recommended product/MVP.
2. **`BENCHME_CODING_BENCHMARKS_RESEARCH_DOSSIER_2026-07-10.md`** — full research dossier, approximately 23,500 words.
3. **`BENCHME_MVP_SCHEMAS_2026-07-10.yaml`** — implementation-ready draft schemas and contracts for capsules, environments, configurations, events, verification, review, failures, artifacts, CLI, and reports.

## Reference files

- **`BENCHME_BENCHMARK_LANDSCAPE_2026-07-10.csv`** — structured comparison of 27 benchmark families.
- **`BENCHME_SOURCE_LEDGER_2026-07-10.md`** — human-readable ledger of 123 sources.
- **`BENCHME_SOURCE_LEDGER_2026-07-10.csv`** — machine-readable source ledger.
- **`SHA256SUMS.txt`** — integrity hashes for package contents.
- **`inputs/`** — the controlling research prompt, BenchMe Demo 01 write-up, and current project knowledge base used as internal context.

## Main research conclusion

The defensible product is not a generic model leaderboard or a historical-replay harness. It is a **local-first evaluation-assurance and continuous calibration system**. The scored unit is the complete model–harness–context–tools–permissions–budget–environment–verifier–trial configuration. BenchMe should validate tasks and oracles, preserve native-product behavior, run controlled interventions separately, prevent runtime answer retrieval, repeat stochastic trials, and issue an auditable decision report.

## Evidence posture

- Online factual claims in the dossier use source IDs such as `[S034]`; each ID resolves in the source ledger.
- **High** evidence means an official artifact, peer-reviewed result, independent reproduction, or directly reproduced BenchMe result.
- **Medium** evidence generally means transparent official methodology without reproduction, a credible preprint, or a vendor study with material caveats.
- **Low** evidence means anecdotal, marketing-heavy, configuration-incomplete, or otherwise weak support.
- Exact current leaderboard values are intentionally deemphasized because models, harnesses, task versions, and submission policies change rapidly.
- Internal BenchMe documents are treated as empirical context or hypotheses, not independent market evidence.

## Quality checks performed

- All 16 required report sections are present.
- The report’s source IDs resolve to the ledger; no duplicate ledger IDs were found.
- The benchmark landscape contains 27 families.
- The YAML schema bundle was parsed successfully with PyYAML.
- Known superseded or mistyped source URLs were removed during the audit pass.
- Claims from the 2026 SWE-bench audits distinguish selected hard subsets, public splits, and held-out/commercial variants rather than generalizing one rate to all tasks.
- New 2026 harness and security papers are labeled as preprints where applicable.

## Recommended use

Use the executive brief for product decisions, the dossier for technical and methodological grounding, the landscape/ledger for follow-up research, and the YAML bundle as the starting contract for the next BenchMe implementation slice.
