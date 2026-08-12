"""Funnel report. Every rejection appears with its class, and the label mix
across validated oracles is printed on every run.

Three properties of this renderer are load-bearing and must survive any edit:

1. `apparatus`, `error` and `not_minable:*` NEVER enter a conversion
   rate. apparatus and error are our failures, not the commit's;
   `not_minable:*` means the commit is outside what this method can measure
   at all (a foreign project grafted into the clone; a commit that straddles
   an exact dependency pin change) and never entered a container. The
   screener's central lesson was that six of seven eliminations were the
   apparatus rather than the subject, and that was only visible because the
   two were counted separately. The headline rate is therefore validated /
   adjudicated, where ADJUDICATED means "reached a verdict about the commit"
   -- validated plus rejected, excluding our failure classes and the
   not_minable family; ATTEMPTED means "entered a container" (validated +
   rejected + apparatus + error, never not_minable), and the
   attempted-denominator figure is printed beside the conversion rate and
   explicitly labelled as NOT the conversion rate, so nobody can quote it as
   one.

   "Adjudicated" has exactly that one meaning in this file. The apparatus rate
   in `_composition` needs a DIFFERENT denominator -- apparatus has to be
   inside its own denominator or the rate is meaningless -- so it counts
   `processed` records (everything but `error`) and says so. The two words are
   kept distinct deliberately: one shared word for two denominators is how a
   reader ends up quoting one rate as the other.

2. Oracle composition and the apparatus rate are emitted unconditionally, even
   when empty. A zero is a measurement; an absent section looks like an
   oversight and is one nobody notices is missing. Round 2 retired failure kind
   as a gate on the understanding that composition becomes a REPORTED property,
   so `outcomes.label`'s output is described here and gates nothing.

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


def _fmt_repro(rec):
    """How much of pass 1's oracle reproduced in pass 2, for a table cell.

    Decision 7's determinism check is otherwise invisible in this report: a
    validated capsule looks the same whether its oracle survived an
    independent rerun or was never checked. Both fields are read with
    `.get`, so pre-redesign records -- written before the check existed --
    render "n/r" rather than claiming a ratio nobody measured.
    """
    pass1 = rec.get("f2p_pass1") or []
    if not pass1:
        return "n/r"
    return f"{len(rec.get('f2p_reproduced') or [])} / {len(pass1)}"


def _funnel(out, cands, done):
    validated = [d for d in done if d["status"] == "validated"]
    apparatus = [d for d in done if d["status"] == "apparatus"]
    errors = [d for d in done if d["status"] == "error"]
    rejected = [d for d in done if d["status"].startswith("rejected:")]
    not_minable = [d for d in done if d["status"].startswith("not_minable:")]
    attempted = len(done) - len(not_minable)
    adjudicated = len(validated) + len(rejected)

    out += ["## Funnel", ""]
    out.append(f"- Candidates enumerated (stages 0-1): **{len(cands)}**")
    out.append(f"- Attempted in stage 2 (entered a container): **{attempted}**")
    out.append(f"- Not minable (reported separately -- never entered a "
               f"container): **{len(not_minable)}**")
    out.append(f"- Validated: **{len(validated)}**")
    out.append(f"- Rejected (a verdict about the commit): **{len(rejected)}**")
    out.append(f"- Apparatus (a verdict about US -- excluded from every rate "
               f"below): **{len(apparatus)}**")
    out.append(f"- Error (miner bug, non-terminal, retried after a fix -- also "
               f"excluded): **{len(errors)}**")
    out.append(f"- Adjudicated -- reached a verdict about the commit "
               f"(validated + rejected; apparatus, error and not_minable "
               f"excluded): "
               f"**{adjudicated}**")
    out.append("")

    if adjudicated:
        rate = 100 * len(validated) / adjudicated
        out.append(f"**Conversion on adjudicated: {rate:.1f}%** "
                   f"({len(validated)}/{adjudicated}). "
                   f"The screener assumed 2.2% on raw pairs.")
    else:
        out.append("**Conversion on adjudicated: undefined** -- nothing "
                   "reached a verdict.")
    if attempted:
        naive = 100 * len(validated) / attempted
        out.append("")
        out.append(f"For reference only, {len(validated)}/{attempted} of "
                   f"*attempted* (entered a container; the {len(not_minable)} "
                   f"not_minable records never did) is {naive:.1f}%. "
                   f"**That is not a conversion "
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
        elif status.startswith("not_minable:"):
            kind = "outside what the method can measure (not attempted)"
        elif status == "apparatus":
            kind = "**our fault** (terminal)"
        else:
            kind = "**our fault** (retryable)"
        out.append(f"| `{status}` | {kind} | {n} |")
    out.append("")


APPARATUS_TRIPWIRE = 10.0


def _composition(out, done):
    """Label mix across validated oracles, plus the apparatus tripwire.

    Emitted unconditionally, including when it is empty. Round 2 retired
    failure kind as a gate on the understanding that composition becomes a
    REPORTED property -- the chair's answer to the objection that labels only
    protect the corpus if someone actually looks at them. A section that
    disappears when it has nothing to say is a section nobody notices is
    missing.
    """
    labels = Counter()
    for rec in done:
        if rec.get("status") == "validated":
            labels.update((rec.get("failure_labels") or {}).values())
    total = sum(labels.values())

    out += ["## Oracle composition", "",
            "How the fail-to-pass tests failed, across validated capsules. "
            "Descriptive only -- no label gates admission "
            "(`docs/council/ROUND_02_SYNTHESIS.md`).", ""]
    if not total:
        out += ["_No validated capsules yet._", ""]
    else:
        out += ["| label | count | share |", "|---|---|---|"]
        for lbl, n in labels.most_common():
            out.append(f"| `{lbl}` | {n} | {100.0 * n / total:.1f}% |")
        out.append("")

    # NOT "adjudicated". That word means validated + rejected everywhere else
    # in this file (see _funnel and the module docstring), and apparatus is
    # excluded from it by definition -- so an apparatus rate over it would be
    # zero over a denominator that cannot contain its numerator. This rate
    # needs apparatus INSIDE the denominator, so it counts every record we
    # processed to a durable outcome, i.e. everything but the retryable
    # `error`. That includes the `not_minable` family: it never entered a
    # container, but it DID get a durable, terminal outcome, so it belongs in
    # "processed" even though it is excluded from "attempted" (which means
    # "entered a container") and from "adjudicated" (which means a verdict
    # about the commit). Different denominator, different word.
    processed = [r for r in done if r.get("status") != "error"]
    if processed:
        not_minable = [r for r in processed
                       if r.get("status", "").startswith("not_minable:")]
        apparatus = [r for r in processed if r.get("status") == "apparatus"]
        rate = 100.0 * len(apparatus) / len(processed)
        out += [f"Apparatus: {len(apparatus)}/{len(processed)} processed "
                f"candidates ({rate:.1f}%) -- 'processed' is every record "
                f"except the retryable `error`s, which is a WIDER denominator "
                f"than the 'adjudicated' one in the funnel above (that one is "
                f"validated + rejected and excludes apparatus by definition) "
                f"and WIDER than the 'attempted' one (that one means 'entered "
                f"a container' and excludes the {len(not_minable)} not_minable "
                f"records, which never did).", ""]
        # Decision 13. The first 2025Q3 batch ran at 48%: mining on would have
        # spent candidates on our own defects and called the result a yield.
        if rate > APPARATUS_TRIPWIRE:
            out += [f"> **TRIPWIRE** apparatus is {rate:.1f}%, above the "
                    f"{APPARATUS_TRIPWIRE:.0f}% threshold. Stop mining and fix "
                    f"tooling before spending more of the corpus.", ""]


def _rejections(out, rejected):
    """Rejection classes, each emitted even when zero.

    The three live classes are printed at zero on purpose: a zero is a
    measurement, and a missing row cannot be told apart from an unmeasured one.

    The base-negative-class breakdown that used to follow this table is gone.
    It counted `missing_api` and friends to price the assertion-only rule;
    round 2 retired that rule (`docs/council/ROUND_02_SYNTHESIS.md`), so those
    rows now price nothing and would show a permanent zero that reads like
    evidence. How the oracle tests failed is still reported -- descriptively,
    and over validated capsules only -- by `_composition`.
    """
    out += ["## Rejections by class", ""]
    counts = Counter(d["status"].split("rejected:", 1)[1] for d in rejected)
    for name in ("unchanged", "regression_broken", "unstable"):
        counts.setdefault(name, 0)
    out += ["| rejection class | count | what it means |", "|---|---|---|"]
    meanings = {
        "unchanged": "no test went fail->pass (see the `before_failed` caveat)",
        "regression_broken": "code patch broke previously-passing tests (the "
                             "recorded reason counts genuinely-failing and "
                             "vanished node ids separately -- see the audit "
                             "below)",
        "unstable": "pass 1's fail->pass set did not reproduce in the "
                    "full-suite pass-2 run -- flaky or selection-dependent",
    }
    for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        why = meanings.get(name, "no longer produced; a class from the "
                                 "retired base-negative classifier")
        out.append(f"| `{name}` | {n} | {why} |")
    out.append("")


def _not_minable(out, done):
    """The `not_minable:*` family: commits outside what this method can
    measure, never entered a container.

    Reported separately from the funnel -- never inside any conversion
    denominator -- and listed per reason. Emitted unconditionally, including
    when it is empty: a zero is a measurement, and an absent section looks
    like an oversight.
    """
    not_minable = [d for d in done
                   if d.get("status", "").startswith("not_minable:")]
    out += ["## Not minable -- outside what this method can measure", ""]
    out.append("These never entered a container, so they are reported "
               "separately and appear in no conversion or attempted "
               "denominator. `not_minable:*` is a property of the commit, "
               "not a verdict about it and not our tooling failing.")
    out.append("")
    if not not_minable:
        out.append("None -- every candidate so far entered a container.")
        out.append("")
        return
    out += ["| reason | count | what it means |", "|---|---|---|"]
    meanings = {
        "foreign_project": "the commit is a foreign project grafted into the "
                           "clone (e.g. pydantic-core inside pydantic)",
        "straddles_dependency_bump": "an exact dependency pin changes across "
                                     "the commit; before and after need "
                                     "different environments",
        "no_pytest_tests": "every touched test was removed by our non-pytest "
                           "filter -- nothing pytest can run",
    }
    for reason, n in sorted(
            Counter(d["status"].split("not_minable:", 1)[1]
                    for d in not_minable).items(),
            key=lambda kv: (-kv[1], kv[0])):
        why = meanings.get(reason, "no longer produced; a retired family")
        out.append(f"| `{reason}` | {n} | {why} |")
    out.append("")

    details = [d for d in not_minable if d.get("reason")]
    if details:
        out += ["### Reason detail", "",
                "| sha | status | reason |", "|---|---|---|"]
        for d in details:
            out.append(f"| `{d['sha'][:8]}` | `{d['status']}` | "
                       f"{(d.get('reason') or '').replace('|', '\\|')} |")
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

    `outcomes.diff` books a node id that PASSED before and is ABSENT after as
    `renamed` when the exact-swap rule holds -- within that test function, the
    after side gained exactly as many newly-passing ids as it lost, so the
    disappearance reconciles as a renumbering -- and as `vanished` otherwise,
    on the reasoning that a collection crash makes a test vanish rather than
    fail. `broken` holds only ids that RAN AND FAILED after the patch; absent
    ids are never booked as broken.
    The rename case is real: pydantic's
    `test_docs.py::test_docstrings_examples` parametrises on the source line
    range of each docstring example, so any code patch that shifts lines in a
    documented module renames every id below it. The old id disappears, the new
    one passes, and under the old rule a clean candidate was booked as a
    regression.

    The exact-swap rule is a heuristic, so this audit stays: a `broken` set
    that is entirely absent from the after log is a rename the rule did not
    catch. An absent id now books `vanished` rather than `broken`, so this
    audit is a belt-and-braces check rather than the primary routing.

    This section does not change any verdict. It reports, per record, how many
    broken ids were genuinely present-and-failing in the after log versus
    absent from it entirely, so a reader can see which regression verdicts are
    real. A record whose broken set is entirely absent from the after log is
    apparatus wearing a verdict, and the reader -- not this renderer --
    decides what to do.
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
    out += ["| sha | subsystem | size | f2p tests | reproduced | p2p | "
            "before_failed | anchored | subject |",
            "|---|---|---|---|---|---|---|---|---|"]
    for d in validated:
        out.append(f"| `{d['sha'][:8]}` | {d['subsystem']} | "
                   f"{d['size_bucket']} | {len(d.get('f2p', []))} | "
                   f"{_fmt_repro(d)} | "
                   f"{d.get('p2p_count', '-')} | {_fmt_bf(d)} | "
                   f"{str(d.get('anchored')).lower()} | "
                   f"{d['subject'][:60]} |")
    out.append("")
    out.append("The oracle node ids, so a reviewer can check them:")
    out.append("")
    for d in validated:
        for node in d.get("f2p", []):
            label = (d.get("failure_labels") or {}).get(node, "?")
            out.append(f"- `{d['sha'][:8]}` `{node}` -> failed as "
                       f"`{label}` before the fix")
    out.append("")


def _quarters(out, cands, done):
    # "Attempted" means "entered a container" here, matching _funnel:
    # not_minable records never did, so they are excluded from this column.
    attempted = Counter(d["quarter"] for d in done
                        if not d["status"].startswith("not_minable:"))
    ok = Counter(d["quarter"] for d in done if d["status"] == "validated")
    out += ["## Candidates by quarter", "",
            "| quarter | enumerated | attempted (entered a container) | "
            "validated |",
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
    _composition(out, done)
    _rejections(out, rejected)
    _not_minable(out, done)
    _apparatus(out, apparatus, errors)
    _drift(out, done)
    _regressions(out, done)
    _validated(out, validated)
    _quarters(out, cands, done)
    return "\n".join(out) + "\n"
