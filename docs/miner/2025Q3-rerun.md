# 2025Q3 re-run — known-answer regression against the hand audit

The first 2025Q3 batch was adjudicated by hand. That audit concluded seven of
its ten rejections were our own defects rather than properties of the commits.
This re-run puts the redesigned classifier against the same 21 candidates and
checks whether it reproduces the hand-derived answer.

Baseline: `miner/out/validated.2025Q3-preredesign.jsonl`.
Comparison script: `miner/compare_rerun.py`.

## Headline

| | before | after |
|---|---|---|
| validated | 1 | **7** |
| rejected:other (unparsed / missing_api / structural) | 4 | **0** |
| rejected:regression_broken | 3 | 2 |
| rejected:unchanged | 3 | 6 |
| apparatus | 10 | 6 |

11 of 21 candidates changed verdict. Conversion on adjudicated candidates
(excluding apparatus) went from **1/11 = 9.1%** to **7/15 = 46.7%**.

Treat 46.7% as a description of these 21, not an estimate of the corpus. The
21 were a stratified sample, and `CONVERSION_RATE` should still not be
recalibrated on them.

## Predictions vs what happened

The plan recorded four predictions before the run. Two held, one held partly,
one was wrong.

**✅ Held. Three `regression_broken` rejections were the line-number rename
defect.** All three now validate. `eb2c860a` is the clean demonstration: its
old record said *"34 previously-passing tests fail after the code patch"*; its
new record reads **34 renamed, 0 broken**. The patch shifted source lines,
`test_docstrings_examples` re-parametrised on the new line numbers, and the old
rule read the renumbering as breakage. Same for `8a62354c` and `9c5eb6e5`, one
rename each.

**◐ Held partly. Four `other:unparsed` rejections — three were ours, one was
not.** `71a02fcf`, `e28f7544` and `27aaf685` now validate. But `f7a9b735` came
back `rejected:regression_broken` with 7 genuinely broken tests. The hand audit
called all four false rejections; it was wrong about that one. Rejecting it for
an unparseable exception name was still the wrong *reason* — it just happened
to reach a defensible verdict by accident.

**❌ Wrong. "8 apparatus cases on `tests/typechecking/` should no longer be
attempted."** Apparatus only fell 10 → 6, and the cases that cleared did so by
different routes than predicted. The hand audit's account of the apparatus
causes was substantially incorrect. The real causes, now visible because the
new error messages name them:

| cause | count | evidence |
|---|---|---|
| `hypothesis` missing from the quarter image | 3 | `tests/conftest.py:15: ModuleNotFoundError: No module named 'hypothesis'` — the conftest import dies before pytest's session starts, so no report is written |
| `tests/mypy/` static-analysis fixtures | 3 | `collected 0 items / 2 errors` on `tests/mypy/modules/frozen_field.py` |

**✅ Held. Some apparatus remains.** Just not the cases or the counts claimed.

## What the labels show

Across the seven validated capsules, nine tests form the oracles:

| label | count |
|---|---|
| `assertion` | 5 |
| `expectation` (pytest's `DID NOT RAISE` / `DID NOT WARN` / `fail()`) | 2 |
| `exception:ValidationError` | 1 |
| `exception:PydanticDeprecatedSince20` | 1 |

**Four of nine — 44% — would have been rejected under round 1's assertion-only
rule.** That is the retired rule's cost, measured rather than argued.

`missing_api` appeared zero times again, now across a correct parser. Two
batches with zero is still not evidence that feature work is rare — the round 2
synthesis records why (zero in 21 is consistent with a true rate near 14%) —
but it is no longer consistent with the rule having been load-bearing.

## The determinism check

Every candidate that reached pass 2 reproduced **100%** of its pass-1 oracle:

```
aa7705f7 1/1    f7a9b735 3/3    71a02fcf 1/1    a59dab90 1/1
e28f7544 1/1    eb2c860a 1/1    8a62354c 2/2    27aaf685 2/2    9c5eb6e5 1/1
```

No candidate booked `rejected:unstable`. That is reassuring about the oracles,
and it also means **the check has not yet been exercised in its failing
direction** — it is unproven, not proven, by this batch.

## The known answer held where it mattered

`a59dab90`, the batch's one original validated capsule, validated again with
the same single-test oracle and the same `assertion` label. The redesign did
not disturb the one result we already trusted.

## The tripwire fired

Apparatus is **6/21 = 28.6%**, above the 10% threshold adopted as council
decision 13. By that rule mining should not continue until the two causes above
are fixed. Both are tooling gaps, both are cheap:

1. Add `tests/mypy/` to `candidates.NON_PYTEST_TEST_DIRS` alongside
   `tests/typechecking/`. This is precisely the per-repo config the design made
   explicit so that gaps would be visible rather than silently mis-verdicted.
2. Get `hypothesis` into the quarter image's dependency closure. It is imported
   by `tests/conftest.py` at this quarter but is absent from the exported
   groups, so *every* candidate whose targets pull that conftest dies before
   pytest starts.

Neither is a classifier defect. Both are recorded as the immediate next work.

## The honest summary

The redesign did what the council said it would: it stopped rejecting
candidates for how their tests failed, and the corpus grew sevenfold on the
same 21 commits. It also made our own failures legible — the two remaining
apparatus causes were invisible behind *"no test outcomes parsed on the before
side"* in the old code and are named outright in the new.

The part that should temper confidence: the hand audit that motivated this
redesign was itself wrong in places. It over-claimed on the apparatus causes
and mis-called one of the four unparsed rejections. The redesign is validated
by execution here, not by that audit.
