# Screener — future work

> Status: **parked** 2026-08-10, after the first full run selected `pydantic`.
> Nothing here blocks the build queue. Revisit when the corpus needs widening or
> the miner's real conversion rate is known.

The screener is a throwaway tool by design; the durable artifact is
`metrics.py`, whose counting rules get harvested into the miner's stage 0.
Items below are ordered by value, not effort.

---

## 1. Re-examine G7 against `sqlalchemy` — highest value

`sqlalchemy` is the richest candidate in the field by a wide margin: **4,098
candidate pairs, 90.16 projected capsules — 2.6× the selected repo.** It was
eliminated for `requirements file present but not pinned (<80% of lines pinned)`.

That may be a real property or a detector gap. `_requirements_pinned` scores
each `requirements*.txt` independently and needs one file at ≥80% pinned; it
does not look at `setup.cfg`, `pyproject.toml` dependency groups, or tox
`deps=` blocks, any of which `sqlalchemy` may use instead.

**Check first**: what `sqlalchemy`'s requirements files actually contain, and
whether its real pinning lives somewhere the detector never reads. If the latter,
this single fix more than doubles the available corpus.

## 2. Recalibrate `CONVERSION_RATE` after the miner's first real run

`0.022` (SWE-Next's honest yield over a broad corpus) sets G2's threshold of 360
pairs. The spec always called it a conservative floor pending validation.

`jinja` missed by **26 pairs**. `attrs`, `packaging`, `fastapi` and `jsonschema`
sit just below too. If a curated repo converts at 5% rather than 2.2%, four or
five eliminated candidates become viable and the threshold should move.

**Do this the moment item 4 of the build queue produces a real yield number.**

## 3. Uniform zero-collection is misclassified as an apparatus error

Introduced by the fix for false `gated:B3`. A run collecting zero tests is
treated as apparatus failure — correct when *some* runs are normal, wrong when
**all five** are zero, which is what a genuine `ModuleNotFoundError` looks like.

Consequence: a real `gated:B2` becomes a non-terminal `status: error` that the
resume path retries forever, and `B_COLUMNS` has no field to surface it.

**Fix**: uniform zero across all runs is a real collection failure; mixed counts
are apparatus. Cannot cause a false *admission* (`error` is excluded from
`rank()`), so it was parked rather than fixed.

## 4. Budgets measure container startup, not test cost

`targeted_latency_warm` came out at 0.90s against 0.93s cold on `click` — no
warming, because each invocation spawns a fresh `docker run`. So
`hardening_hours` is mostly 1,800 container starts.

Did not change the `pydantic` decision (0.45h either way) but would mislead on a
slower repo. **Fix**: run N invocations inside one container so the second and
third are genuinely warm.

## 5. Two paths have never executed

- **Gate B4** (network-dependent test rescue) — corrected after being found
  unreachable, but confirmed only synthetically and by replaying a stored record.
  No finalist has since produced a network-dependent failure.
- **Environment rung 2** (repo ships its own Dockerfile) — no candidate in the
  field used it. `detect_rung` records `env_source` from tracked files while
  `build_image` independently picks `next(repo.rglob("Dockerfile"))`, possibly a
  different and untracked file, and such a build gets none of the generated
  image's guarantees (no pytest assertion, no `less`, possibly no test deps).

Both need a candidate that exercises them before they can be trusted.

## 6. Smaller recorded items

- `--filter=blob:none` defers *tree* fetches too, so `git log --name-only` needs
  network mid-sweep. `urllib3` errored on a transient drop and was nearly lost —
  it turned out to be the second-highest-yield repo. Mitigated only by `error`
  being non-terminal so a re-run retries.
- `_install_strategy` only recognises `uv.lock`; a repo admitted on
  `poetry.lock` or `pdm.lock` resolves fresh from PyPI. Visible via
  `install_strategy`, so not silent.
- `is_test_file` treats `tests/helpers.py` as a test, so a source + test-helper
  commit counts as a candidate pair.
- `DEPENDENCY_LINE` reads as a PEP 508 validator and is a shape heuristic —
  accepts `pkg,,,`, rejects `pkg [extra]==1.0`. Comment corrected; consider
  renaming before harvest.
- UTF-8 BOM survives `.strip()`, so a BOM'd single-line `requirements.txt`
  yields "no evidence" instead of pinned. One-character fix: `encoding="utf-8-sig"`.
- `compute_tier_a` recomputes the test-map ratio inline rather than calling
  `test_map_ratio()`; the two can drift after harvest.

---

## Known limits of the current result

Not defects — properties of the run, and they belong in any report the corpus
supports.

- **The corpus cannot speak to application-shaped code.** Both application
  probes were eliminated (`pre-commit` on G3, `mkdocs` on G1). All four
  survivors are libraries. 16 of 18 candidates were libraries to begin with.
- **The fresh stream is ~4× thinner than estimated.** `projected_fresh` is
  0.77–0.81 — under *one* contamination-resistant capsule per repo. Contamination
  is effectively unavoidable; report the fresh/stale split beside every result.
- **k=5 cannot see between-sweep variance.** `urllib3`'s verdict flipped across
  sweeps (2 passed, 1 gated). Most of that was our own B4 defect, but a pyopenssl
  HTTP/2 variant failed 5-of-5 in one sweep having passed in others.
- **Gate ids G4, G5, G6 are retired, not reused.** Their functions remain in
  `gates.py`, unused, so no future gate silently inherits their meaning.
