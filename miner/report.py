"""Funnel report. Every rejection appears with its class -- especially
missing_api, which is the number that tells us what the assertion-only rule
actually cost in yield.

Three properties of this renderer are load-bearing and must survive any edit:

1. `apparatus` and `error` NEVER enter a conversion rate. They are our
   failures, not the commit's. The screener's central lesson was that six of
   seven eliminations were the apparatus rather than the subject, and that was
   only visible because the two were counted separately. The headline rate is
   therefore validated / adjudicated, where adjudicated excludes both; the
   attempted-denominator figure is printed beside it and explicitly labelled
   as NOT the conversion rate, so nobody can quote it as one.

2. Every rejection class is printed, and `missing_api` is printed even when it
   is zero. A zero is a measurement; an absent row looks like an oversight.
   The assertion-only rule filters out feature work, and the size of that cost
   is a finding for the decision council -- never a reason to loosen
   `validate.classify`.

3. `before_failed` is surfaced per candidate. The quarter image pins the
   quarter's LAST lockfile, so a mid-quarter candidate runs against slightly
   wrong dependencies (measured: 840 of 6437 on 2025Q3). A
   `rejected:unchanged` on a candidate with a high `before_failed` is suspect
   and must be re-examined, not counted as a verdict.
"""
import json
import re
from collections import Counter

import record

# A batch is drawn round-robin across (subsystem, size_bucket) strata, so it
# equalises STRATA, not mass. Any rate computed from it needs reweighting
# before it can be called a corpus rate. This lives in the rendered report,
# not just in a summary someone may not read.
STRAT_CAVEAT = (
    "> **The conversion rate below is a batch rate, not the corpus rate.** "
    "`candidates.stratified_order` walks the `(subsystem, size_bucket)` "
    "strata round-robin, which equalises strata rather than mass. "
    "{top_share:.0f}% of all enumerated candidates sit in the top two "
    "subsystems ({top_names}), but a small batch draws only a token few from "
    "each. Reweighting by stratum mass is required before any of these "
    "percentages describe the corpus."
)

DRIFT_CAVEAT = (
    "> **`before_failed` is a drift alarm, not a statistic.** The quarter "
    "image is anchored to the lockfile at the quarter's *last* commit, so a "
    "candidate from earlier in the window runs against dependencies that are "
    "slightly wrong for it -- measured at 840 of 6437 tests failing on the "
    "before side for `a59dab90`. If a candidate's own oracle test is among "
    "that drift, it fails on both sides, never becomes fail-to-pass, and is "
    "booked `rejected:unchanged`: an apparatus artefact wearing the shape of "
    "a verdict. Treat any `rejected:unchanged` with a high `before_failed` as "
    "unresolved rather than rejected. `anchored=true` does NOT clear this -- "
    "the image is anchored and still wrong for the commit."
)


# Every apparatus record from a zero-outcome before run carries the SAME
# reason string, so grouping on `reason` alone reports ten identical rows and
# hides the fact that they have several unrelated root causes -- which is
# precisely the information that decides whether apparatus is fixable. The
# signature is recovered from the before log instead. Ordered: the first
# pattern that matches wins, so the specific interpreter-level errors are
# tried before the generic pytest banners.
_APPARATUS_SIGNATURES = [
    (re.compile(r"^E\s+(ModuleNotFoundError: No module named .*)$", re.M),
     "missing dependency in the quarter image"),
    (re.compile(r"^E\s+(SystemError: The installed pydantic-core version[^\n]*?)\.",
                re.M),
     "pydantic-core version skew vs the pinned lockfile"),
    (re.compile(r"^E\s+([A-Za-z_][\w.]*(?:Error|Exception): [^\n]{0,90})", re.M),
     "conftest/import error before collection"),
    # No `$` anchor: a real collection-error summary line routinely runs past
    # any bounded character class, and anchoring the group to end-of-line made
    # every long line fall through to "not determined".
    (re.compile(r"^(ERROR \S[^\n]*)", re.M),
     "collection error aborted the session"),
    (re.compile(r"^=+ (no tests ran[^\n]*?) =+$", re.M),
     "pytest collected nothing from the touched test paths"),
]


def _apparatus_signature(rec):
    """(family, evidence) recovered from the candidate's before log.

    Returns (None, None) when there is no log to read -- an absent log is not
    evidence of anything and must not be folded into a named family.
    """
    log = record.LOGS / rec["sha"][:12] / "before.log"
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None
    for pattern, family in _APPARATUS_SIGNATURES:
        m = pattern.search(text)
        if m:
            return family, m.group(1).strip()[:120]
    return None, None


def _load():
    cands = []
    if record.CANDIDATES.exists():
        with open(record.CANDIDATES, encoding="utf-8") as fh:
            cands = [json.loads(l) for l in fh if l.strip()]
    done = list(record.read_all(record.VALIDATED).values())
    return cands, done


def _fmt_bf(rec):
    """`before_failed` for a table cell.

    None is not zero. None means no before run happened, or the record predates
    the field; either way it is unknown and must not read as a clean baseline.
    """
    bf = rec.get("before_failed")
    seen = rec.get("tests_seen")
    if bf is None:
        return "n/r"
    if seen:
        return f"{bf} / {seen}"
    return str(bf)


def _funnel(out, cands, done):
    validated = [d for d in done if d["status"] == "validated"]
    apparatus = [d for d in done if d["status"] == "apparatus"]
    errors = [d for d in done if d["status"] == "error"]
    rejected = [d for d in done if d["status"].startswith("rejected:")]
    adjudicated = len(validated) + len(rejected)

    out += ["## Funnel", ""]
    out.append(f"- Candidates enumerated (stages 0-1): **{len(cands)}**")
    out.append(f"- Attempted in stage 2: **{len(done)}**")
    out.append(f"- Validated: **{len(validated)}**")
    out.append(f"- Rejected (a verdict about the commit): **{len(rejected)}**")
    out.append(f"- Apparatus (a verdict about US -- excluded from every rate "
               f"below): **{len(apparatus)}**")
    out.append(f"- Error (miner bug, non-terminal, retried after a fix -- also "
               f"excluded): **{len(errors)}**")
    out.append(f"- Adjudicated (validated + rejected): **{adjudicated}**")
    out.append("")

    if adjudicated:
        rate = 100 * len(validated) / adjudicated
        out.append(f"**Conversion on adjudicated: {rate:.1f}%** "
                   f"({len(validated)}/{adjudicated}). "
                   f"The screener assumed 2.2% on raw pairs.")
    else:
        out.append("**Conversion on adjudicated: undefined** -- nothing "
                   "reached a verdict.")
    if done:
        naive = 100 * len(validated) / len(done)
        out.append("")
        out.append(f"For reference only, {len(validated)}/{len(done)} of "
                   f"*attempted* is {naive:.1f}%. **That is not a conversion "
                   f"rate** and must not be quoted as one: its denominator "
                   f"includes {len(apparatus)} apparatus and {len(errors)} "
                   f"error records, which are candidates we failed to "
                   f"process, not candidates that failed to qualify.")
    out.append("")

    if cands:
        subs = Counter(c["subsystem"] for c in cands).most_common(2)
        top_share = 100 * sum(n for _, n in subs) / len(cands)
        out.append(STRAT_CAVEAT.format(
            top_share=top_share,
            top_names=", ".join(f"`{s}`" for s, _ in subs)))
        out.append("")
    return validated, apparatus, errors, rejected


def _verdicts(out, done):
    out += ["## All statuses", "", "| status | kind | count |", "|---|---|---|"]
    for status, n in Counter(d["status"] for d in done).most_common():
        if status == "validated":
            kind = "accepted"
        elif status.startswith("rejected:"):
            kind = "verdict on the commit"
        elif status == "apparatus":
            kind = "**our fault** (terminal)"
        else:
            kind = "**our fault** (retryable)"
        out.append(f"| `{status}` | {kind} | {n} |")
    out.append("")


def _rejections(out, rejected, done):
    """Rejection classes, plus the base-negative classes behind them.

    `missing_api` is emitted at both levels even when zero: the whole point of
    the number is to price the assertion-only rule, and a missing row cannot be
    told apart from an unmeasured one.
    """
    out += ["## Rejections by class", ""]
    counts = Counter(d["status"].split("rejected:", 1)[1] for d in rejected)
    for name in ("missing_api", "structural", "assertion", "unchanged",
                 "regression_broken"):
        counts.setdefault(name, 0)
    out += ["| rejection class | count | what it means |", "|---|---|---|"]
    meanings = {
        "unchanged": "no test went fail->pass (see the `before_failed` caveat)",
        "missing_api": "**base negative was AttributeError/ImportError/"
                       "NameError/ModuleNotFoundError -- feature work, "
                       "excluded by the assertion-only rule**",
        "structural": "base negative was a syntax or collection error",
        "regression_broken": "code patch broke previously-passing tests",
        "assertion": "should be impossible -- an assertion base negative "
                     "qualifies",
    }
    for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        why = meanings.get(name, "unrecognised exception identity; see "
                                 "`validate.classify`'s `other:` fallthrough")
        out.append(f"| `{name}` | {n} | {why} |")
    out.append("")
    out.append(f"**`missing_api` rejections: {counts['missing_api']}.** This "
               f"is the price of the council's assertion-only rule, measured "
               f"rather than assumed. A large number here is a finding to "
               f"take back to the council; it is never a reason to loosen "
               f"`validate.classify`.")
    out.append("")

    # The per-status class above is the DOMINANT class of the rejection. The
    # tally below is over every f2p node id the miner ever classified, which is
    # the number that actually prices the rule -- a candidate can carry a
    # missing_api base negative and still be rejected for another reason, or be
    # validated because one of its node ids was an assertion.
    tally = Counter()
    for d in done:
        for cls in (d.get("failure_classes") or {}).values():
            tally[cls] += 1
    out += ["### Base-negative classes over every classified f2p node id", ""]
    if not tally:
        out.append("No candidate reached classification.")
        out.append("")
        return
    tally.setdefault("missing_api", 0)
    total = sum(tally.values())
    out += ["| class | node ids | share |", "|---|---|---|"]
    for cls, n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
        share = f"{100 * n / total:.0f}%" if total else "-"
        out.append(f"| `{cls}` | {n} | {share} |")
    out.append("")


def _apparatus(out, apparatus, errors):
    out += ["## Apparatus failures -- our fault, not the repo's", ""]
    if not apparatus:
        out.append("None.")
        out.append("")
    else:
        out.append("These are excluded from every rate above. Each one is a "
                   "candidate we could not process; none is evidence about "
                   "the commit.")
        out.append("")
        out += ["| reason recorded | count |", "|---|---|"]
        for reason, n in Counter(
                (d.get("reason") or "")[:110] for d in apparatus).most_common():
            out.append(f"| {reason} | {n} |")
        out.append("")

        sigs = {d["sha"]: _apparatus_signature(d) for d in apparatus}
        out += ["### Root causes, recovered from the before logs", "",
                "The recorded reason above is the symptom. These are the "
                "distinct causes behind it -- the breakdown that decides "
                "which of these are fixable.", "",
                "| root cause | count |", "|---|---|"]
        for family, n in Counter(
                sigs[d["sha"]][0] or "not determined from the log"
                for d in apparatus).most_common():
            out.append(f"| {family} | {n} |")
        out.append("")
        out += ["| sha | subsystem | root cause | evidence from before.log |",
                "|---|---|---|---|"]
        for d in apparatus[:25]:
            family, evidence = sigs[d["sha"]]
            out.append(f"| `{d['sha'][:8]}` | {d.get('subsystem')} | "
                       f"{family or '-'} | "
                       f"{(evidence or '-').replace('|', '\\|')} |")
        out.append("")
    if errors:
        out += ["### Errors (miner bugs -- retried, not retired)", ""]
        for d in errors[:15]:
            first = (d.get("reason") or "").strip().splitlines()
            out.append(f"- `{d['sha'][:8]}` {first[-1] if first else ''}")
        out.append("")


def _drift(out, done):
    out += ["## Dependency drift on the before side (`before_failed`)", "",
            DRIFT_CAVEAT, ""]
    measured = [d for d in done if d.get("before_failed")]
    unchanged = [d for d in done if d["status"] == "rejected:unchanged"]
    out += ["| sha | status | before_failed / tests_seen | anchored | anchor |",
            "|---|---|---|---|---|"]
    for d in sorted(done, key=lambda r: -(r.get("before_failed") or 0))[:25]:
        out.append(f"| `{d['sha'][:8]}` | `{d['status']}` | {_fmt_bf(d)} | "
                   f"{str(d.get('anchored')).lower()} | "
                   f"`{(d.get('anchor') or 'n/r')[:12]}` |")
    out.append("")
    suspect = [d for d in unchanged if (d.get("before_failed") or 0) > 0]
    out.append(f"`rejected:unchanged` records: {len(unchanged)}; of those, "
               f"{len(suspect)} ran against a before side with at least one "
               f"failing test and are therefore suspect rather than settled. "
               f"`n/r` means the field was not recorded for that run and the "
               f"drift is simply unknown -- it does not mean zero.")
    out.append("")
    if not measured:
        out.append("No record in this file carries a non-zero measured "
                   "`before_failed`.")
        out.append("")


def _regressions(out, done):
    """Split each `rejected:regression_broken` into real failures and vanished
    node ids.

    `validate.diff_outcomes` books a node id that PASSED before and is ABSENT
    after as broken, on the reasoning that a collection crash makes a test
    vanish rather than fail. That reasoning is sound but the rule also catches
    a node id that was merely RENAMED: pydantic's
    `test_docs.py::test_docstrings_examples` parametrises on the source line
    range of each docstring example, so any code patch that shifts lines in a
    documented module renames every id below it. The old id disappears, the new
    one passes, and a clean candidate is booked as a regression.

    This section does not change any verdict. It reports, per record, how many
    broken ids were genuinely present-and-failing in the after log versus
    absent from it entirely, so a reader can see which regression verdicts are
    real. A record whose broken set is entirely vanished is apparatus wearing a
    verdict, and the reader -- not this renderer -- decides what to do.
    """
    regs = [d for d in done if d["status"] == "rejected:regression_broken"]
    out += ["## `regression_broken` audit: real failure or vanished node id?",
            ""]
    if not regs:
        out.append("No regression verdicts to audit.")
        out.append("")
        return
    out.append("A broken node id that is ABSENT from the after log did not "
               "fail -- it was renamed. `test_docs.py::test_docstrings_"
               "examples` parametrises on source line ranges, so any code "
               "patch that shifts lines renames every id below it. A record "
               "with 0 genuinely-failing ids is apparatus wearing a verdict.")
    out.append("")
    out += ["| sha | broken ids | failed in after | vanished from after | "
            "example |", "|---|---|---|---|---|"]
    for d in regs:
        broken = d.get("broken") or []
        log = record.LOGS / d["sha"][:12] / "after.log"
        try:
            text = log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            out.append(f"| `{d['sha'][:8]}` | {len(broken)} | ? | ? | "
                       f"after log unavailable |")
            continue
        vanished = [n for n in broken if n not in text]
        out.append(f"| `{d['sha'][:8]}` | {len(broken)} | "
                   f"{len(broken) - len(vanished)} | {len(vanished)} | "
                   f"`{(broken[0] if broken else '-')[:78]}` |")
    out.append("")


def _validated(out, validated):
    out += ["## Validated candidates", ""]
    if not validated:
        out.append("None yet.")
        out.append("")
        return
    out += ["| sha | subsystem | size | f2p tests | p2p | before_failed | "
            "anchored | subject |",
            "|---|---|---|---|---|---|---|---|"]
    for d in validated:
        out.append(f"| `{d['sha'][:8]}` | {d['subsystem']} | "
                   f"{d['size_bucket']} | {len(d.get('f2p', []))} | "
                   f"{d.get('p2p_count', '-')} | {_fmt_bf(d)} | "
                   f"{str(d.get('anchored')).lower()} | "
                   f"{d['subject'][:60]} |")
    out.append("")
    out.append("The oracle node ids, so a reviewer can check them:")
    out.append("")
    for d in validated:
        for node in d.get("f2p", []):
            cls = (d.get("failure_classes") or {}).get(node, "?")
            out.append(f"- `{d['sha'][:8]}` `{node}` -> base negative "
                       f"classified `{cls}`")
    out.append("")


def _quarters(out, cands, done):
    attempted = Counter(d["quarter"] for d in done)
    ok = Counter(d["quarter"] for d in done if d["status"] == "validated")
    out += ["## Candidates by quarter", "",
            "| quarter | enumerated | attempted | validated |",
            "|---|---|---|---|"]
    for q, n in sorted(Counter(c["quarter"] for c in cands).items(),
                       reverse=True)[:12]:
        out.append(f"| {q} | {n} | {attempted.get(q, 0)} | {ok.get(q, 0)} |")
    out.append("")


def render():
    cands, done = _load()
    out = ["# Miner funnel - stages 0-2", ""]
    validated, apparatus, errors, rejected = _funnel(out, cands, done)
    _verdicts(out, done)
    _rejections(out, rejected, done)
    _apparatus(out, apparatus, errors)
    _drift(out, done)
    _regressions(out, done)
    _validated(out, validated)
    _quarters(out, cands, done)
    return "\n".join(out) + "\n"
