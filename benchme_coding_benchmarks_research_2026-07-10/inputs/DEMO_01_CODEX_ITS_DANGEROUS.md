# Demo 01: comparing Codex models on one fresh Python task

## Purpose

This demo is the first executable slice of BenchMe. It compares model choices
inside the same native Codex harness while holding the repository, task,
reasoning effort, execution policy, and verifier constant.

It is a native-product experiment, not a pure base-model benchmark. The measured
unit is:

```text
model + Codex harness + prompt + tools + budget + environment + verifier
```

## 1. Repository selection

The repository is `pallets/itsdangerous`, pinned to commit
`672971d66a2ef9f85151e53283113f33d642dabd`.

It was selected because it is:

- a real, known Python library;
- small enough to understand in one evening;
- deterministic and fast to test;
- free of databases and external services;
- rich enough to exercise inheritance, typing, security-sensitive behavior,
  backward compatibility, file APIs, and timed tokens.

The untouched checkout has 36 tracked files and passes 297 tests.

## 2. Contamination mitigation

The code is public, so model familiarity with the library cannot be ruled out.
We did not replay a public issue or historical patch. Instead, we authored a new
unpublished feature: fallback salt rotation for `Serializer`.

The agent receives:

- the pinned one-commit checkout;
- the public task specification;
- the normal repository test suite.

It does not receive:

- a known solution patch;
- future Git history or a Git remote;
- evaluator-owned private tests;
- web search or shell network access.

This reduces direct answer retrieval and issue memorization. It does not make
the repository architecture unknown to the model, so the result must still be
described as a private task on public code.

## 3. Task capsule

The capsule lives at [demo/tasks/fallback-salts](../demo/tasks/fallback-salts/).

Its core contract is:

- accept `fallback_salts` in `Serializer.__init__`;
- continue signing only with the primary salt;
- load with primary salt followed by fallback salts;
- bypass configured fallbacks when an explicit salt is supplied;
- combine salt rotation with fallback signers and secret-key rotation;
- inherit behavior in timed and URL-safe serializers;
- preserve `SignatureExpired` for normal timed loads;
- preserve unsafe loading's `(False, payload)` contract;
- keep public typing and documentation accurate.

The evaluator owns nine private tests. A small evaluator-authored reference
implementation is also validated before any model is scored. This proves the
task is solvable and the oracle can accept a correct implementation. It is a
positive control, not a patch that candidate solutions must imitate.

## 4. Baseline and reference controls

The controls answer different questions:

| Control | Expected result | Purpose |
|---|---:|---|
| Untouched repo + upstream tests | 297 pass | The pinned repository is healthy. |
| Untouched repo + private tests | 9 fail | The private tests detect the missing feature. |
| Reference patch + all tests | 306 pass | The task and oracle admit a known solution. |

Both negative and positive controls are necessary. Without the negative control,
hidden tests may pass vacuously. Without the positive control, the evaluator may
be impossible or incorrectly specified.

## 5. Controlled Codex execution

The runner is [demo/run_experiment.py](../demo/run_experiment.py). For each
model, it:

1. creates a fresh local clone at the pinned commit;
2. removes the remote;
3. disables project rules and user configuration injection;
4. runs Codex ephemerally at medium reasoning;
5. selects the Windows `unelevated` workspace sandbox explicitly;
6. disables Codex web search and sandboxed outbound network access;
7. places the controlled Python environment on `PATH`;
8. persists the JSONL trace during execution;
9. captures the Git diff and status;
10. runs upstream tests, private tests, mypy, Pyright, and Ruff checks;
11. emits normalized JSON and Markdown reports.

The Codex configuration keys are documented in OpenAI's
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
and the two native Windows sandbox modes are described in the
[Windows sandbox guide](https://learn.chatgpt.com/docs/windows/windows-sandbox).

## 6. Why task v1 was superseded

The first executable run surfaced two evaluator defects.

First, the native Windows sandbox remained read-only until the runner explicitly
selected `windows.sandbox="unelevated"`. The agent reasoned about the task but
could not write. That run is marked invalid, not failed.

Second, task v1 said unsafe APIs should behave "consistently" with `loads`.
`gpt-5.4-mini` interpreted that as making expired unsafe loads raise
`SignatureExpired`. All eight private tests passed, but human review noticed the
backward-incompatible change. Task v2 now explicitly preserves `(False,
payload)` and includes a regression test.

This incident is the clearest demonstration of the product thesis: evaluation
quality depends on task wording, environment, oracles, and human compatibility
review—not only on model output.

## 7. Comparable v2 result

The complete raw report is
[demo/runs/20260709T224810Z/REPORT.md](../demo/runs/20260709T224810Z/REPORT.md),
and the qualitative review is
[demo/runs/20260709T224810Z/REVIEW.md](../demo/runs/20260709T224810Z/REVIEW.md).

| Model | Result | Time | Input tokens | Output tokens |
|---|---:|---:|---:|---:|
| `gpt-5.5` | solved | 197.1 s | 663,652 | 8,450 |
| `gpt-5.4` | solved | 158.5 s | 487,121 | 7,201 |
| `gpt-5.4-mini` | solved | 324.9 s | 1,031,987 | 20,713 |

These figures describe this run only. One trial cannot estimate variance, and
ChatGPT-authenticated token telemetry is not an API-dollar cost measure.

## 8. What the MVP needs next

### Runner correctness

- Automate a write, test-environment, and network-policy preflight before model
  trials.
- Use a stronger external container boundary so private tests are not merely
  outside the candidate Git root.
- Record OS, CLI, dependency, Git, sandbox, and model-catalog versions.
- Classify infrastructure, environment, agent, verifier, and timeout failures
  separately.

### Experimental validity

- Run at least three trials per configuration.
- Add tasks with different shapes: localization, small bug fix, multi-file
  change, test generation, and review-only analysis.
- Version every task prompt, hidden oracle, harness setting, and evaluator.
- Separate native-product, normalized-context, and augmented-context tracks.
- Add post-hoc adversarial tests only as a new task version, never silently.

### Metrics

- Distinguish cached and uncached input.
- Track command count, failed commands, test attempts, file reads, files changed,
  diff size, and retry loops.
- Add API pricing only when runs use an attributable billing surface.
- Add human-review fields for scope, compatibility, maintainability, and test
  quality.

### Product scope

The next engineering step is still the evaluation core:

```text
task capsule -> isolated checkout -> native agent adapter -> trace + patch
             -> deterministic verifier -> human review -> report
```

RAG, LangGraph, routing, and a dashboard are not required for the next slice.
They become useful after the task schema, isolation boundary, verifier, and
result model are trustworthy.
