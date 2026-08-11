# 2025Q3 re-run — known-answer regression against the hand audit

The first 2025Q3 batch was adjudicated by hand. That audit concluded seven of
its ten rejections were our own defects rather than properties of the commits.
This document reports what the redesigned classifier does with the same 21
candidates.

Baseline: `miner/out/validated.2025Q3-preredesign.jsonl`.
Comparison: `python miner/compare_rerun.py` (reads the most recent verdict per
candidate from the append-only store).

Two re-runs were made. The first ran before the final pre-merge review; the
numbers below are from the **second**, after that review's fixes landed. Where
the two differ the difference is itself informative and is called out.

## Headline

| | before | after |
|---|---|---|
| validated | 1 | **7** |
| rejected:other (unparsed / missing_api / structural) | 4 | **0** |
| rejected:regression_broken | 3 | 1 |
| rejected:unchanged | 3 | 3 |
| apparatus | 10 | 10 |

**Validated capsules went from 1 to 7 on the same 21 commits.** Conversion on
candidates we can actually adjudicate went from 1/11 = 9.1% to 7/11 = 63.6%.

Treat that as a description of these 21, not an estimate. They were a
stratified sample and `CONVERSION_RATE` should not be recalibrated on them.

## Predictions vs what happened

The plan recorded four predictions. Two held, one held partly, one was wrong.

**✅ Held. Three `regression_broken` rejections were the line-number rename
defect.** All three now validate. `eb2c860a` is the clean demonstration: its old
record said *"34 previously-passing tests fail after the code patch"*; its new
record reads **34 renamed, 0 broken**. The code patch shifted source lines,
`test_docstrings_examples` re-parametrised on the new line numbers, and the old
rule read the renumbering as breakage. Same for `8a62354c` and `9c5eb6e5`.

**◐ Held partly. Four `other:unparsed` rejections — three were ours, one was
not.** `71a02fcf`, `e28f7544` and `27aaf685` validate. `f7a9b735` does not; see
below. Rejecting it for an unparseable exception name was still the wrong
*reason* — it reached a defensible verdict by accident.

**❌ Wrong. "8 apparatus cases on `tests/typechecking/` should no longer be
attempted."** The hand audit's account of the apparatus causes was substantially
incorrect, and the apparatus count did not fall at all. What changed is that
every one of the ten now says what actually happened:

| cause | count |
|---|---|
| `hypothesis` missing from the quarter image — `tests/conftest.py` cannot import, so pytest dies before its session starts and writes no report | 3 |
| the candidate's *own* touched test files failed to collect | 4 |
| our path filters left pass 1 with no target at all | 3 |

Under the old code these all read *"no test outcomes parsed on the before
side"*, which said nothing.

**✅ Held. Some apparatus remains.** Just not the cases or the counts claimed.

## The apparatus rate went up, and that is the fix working

First re-run: 28.6%. Second: **47.6%**. The increase is the point.

Between the two runs, the final review found that four candidates were being
booked as verdicts about the commit when the cause was ours:

- `dac3c437`, `568509c0`, `9b438b49` booked `rejected:unchanged` — a terminal
  verdict — because *our own* `NON_PYTEST_TEST_DIRS` filter had removed every
  target. They now read `OUR path selection left pass 1 with no target`.
- `aa7705f7` booked `rejected:regression_broken` with "9 previously-passing
  tests fail". Its own touched test files had failed to collect, so those tests
  never ran. It now books apparatus.

Moving four candidates out of `rejected:*` and into `apparatus` raises the
apparatus rate and lowers the rejection count. That is the discipline working:
we stopped blaming commits for our failures. **The tripwire (council decision
13, 10%) fires, correctly. Mining should not continue until the tooling gaps
below are closed.**

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

`missing_api` appeared zero times again, now through a correct parser. Two
batches at zero is still not evidence that feature work is rare (zero in 21 is
consistent with a true rate near 14%, per the round 2 synthesis) — but it is no
longer consistent with the rule having been load-bearing.

## The determinism check

Every candidate reaching pass 2 reproduced **100%** of its pass-1 oracle. No
candidate booked `rejected:unstable`. Reassuring about the oracles — and it
means the check has **not yet been exercised in its failing direction**. It is
unproven, not proven, by this batch.

## The known answer held

`a59dab90`, the batch's one original validated capsule, validated again with
the same single-test oracle and the same `assertion` label.

## The one remaining rejection, and what it exposes

`f7a9b735` books `rejected:regression_broken` with a reason that is worth
reading carefully:

> 0 previously-passing test(s) fail after the code patch and 7 vanished from
> the after run (first: `tests/test_docs.py::test_docs_examples[docs/concepts/serialization.md:722-745]`)

**Zero tests actually failed.** `test_docs_examples` is parametrised on line
ranges inside *documentation* files, and this commit edits
`docs/concepts/serialization.md`. Seven ids vanished and eight others
reconciled as renames; the exact-swap rule requires the vanished and appeared
counts to match, and here the edit changed how many examples the file has.

This is the Task 3 trade-off landing on its conservative side: ambiguity
resolves toward `broken`, which costs a candidate rather than admitting a bad
one. That direction is correct by design. But the verdict string
*"previously-passing tests fail after the code patch"* is literally false when
the failed count is zero, and a rejection whose entire basis is an unreconciled
id-space change is not really a regression.

**Recorded as the top follow-up:** a `broken` set with zero actual failures
should not book `regression_broken`. It is either apparatus or its own
`rejected:unreconciled`. This is only visible because the final review split
the reason into failed-vs-vanished counts.

## Next work, in order

1. **Get `hypothesis` into the quarter image's dependency closure.** It is
   imported by `tests/conftest.py` at this quarter but absent from the exported
   groups, so every candidate whose targets pull that conftest dies before
   pytest starts. Largest single apparatus cause.
2. **Split the zero-failures regression verdict** described above.
3. **Narrow the pass-2 collection-error predicate** to the candidate's own
   target files. Pass 1 is handled; pass 2 is deliberately left open because a
   blanket rule there would retire nearly every candidate under endemic
   dependency drift.
4. Re-run 2025Q3 once 1–3 land, and only then consider recalibrating
   `CONVERSION_RATE`.

## The honest summary

The redesign did what the council said it would: it stopped rejecting
candidates for how their tests failed, and validated capsules went from 1 to 7
on the same commits. It also made our own failures legible — every apparatus
case now names its cause, where before they all said the same uninformative
thing.

Two caveats worth carrying. The hand audit that motivated this work was itself
wrong in places: it over-claimed on the apparatus causes and mis-called one of
the four unparsed rejections. And nearly half of these candidates still cannot
be adjudicated at all — the corpus is currently limited by our environment, not
by the commits.
