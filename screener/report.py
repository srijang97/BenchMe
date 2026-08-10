"""REPORT.md rendering. Every candidate appears, including eliminated ones."""
import datetime as _dt

import gates

# `test_map_ratio`, `test_map_ambiguous`, `compiled_markers` and
# `service_markers` back the now-retired G4/G5/G6 gates (see gates.py). They
# are still computed by metrics.compute_tier_a and stay in the report as
# diagnostic columns -- reported, not scored, and no longer eliminating.
A_COLUMNS = [
    ("candidate_pairs", "pairs"),
    ("projected_capsules", "proj"),
    ("candidate_pairs_fresh", "fresh"),
    ("projected_fresh", "proj_f"),
    ("fresh_share", "fresh%"),
    ("excluded_nonhuman", "nonhuman"),
    ("frac_multifile", "multifile"),
    ("files_p50", "f_p50"),
    ("files_p90", "f_p90"),
    ("test_map_ratio", "testmap"),
    ("test_map_ambiguous", "ambig"),
    ("compiled_markers", "compiled"),
    ("service_markers", "service"),
    ("revert_commits", "reverts"),
    ("hotfix_commits", "hotfix"),
    ("tracked_files", "files"),
    ("python_loc", "loc"),
    ("lockfile", "lock"),
    ("tag", "tag"),
]

# Verified against the first real Tier B record (click, 2026-08-10): every key
# below is present in the record `measure`/`budgets` actually write. A column
# naming a field that does not exist renders as a blank cell, which in a
# decision report reads as a measured value of nothing.
#
# `install_strategy` is rendered because G7 admits a candidate on the strength
# of a lockfile: the report has to show whether the build then HONOURED that
# lock or resolved fresh. `test_count` is rendered because it is the
# denominator of `flake_rate`, and a silently-zero denominator is exactly how
# a parser bug once turned a clean suite into a `gated:B3`.
B_COLUMNS = [
    ("env_rung", "rung"),
    ("install_strategy", "install"),
    ("container_user", "user"),
    ("operator_minutes", "op_min"),
    ("head_green", "green"),
    ("test_count", "tests"),
    ("head_failure_count", "hard_fail"),
    ("skipped_count", "skipped"),
    ("intermittent_count", "intermit"),
    ("flake_rate", "flake"),
    ("suite_runtime_p50", "suite_s"),
    ("targeted_latency_warm", "warm_s"),
    ("net_dependent_count", "net"),
    ("hardening_hours", "harden_h"),
    ("verification_hours", "verify_h"),
]


def _cell(value):
    """Render one field for a markdown table cell.

    List-valued diagnostic fields (compiled_markers, service_markers) render
    as a comma-joined string instead of a Python repr; empty lists/None/""
    all render as the empty cell so a clean record doesn't show `[]` or
    `None`.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _table(records, columns):
    head = "| repo | " + " | ".join(label for _k, label in columns) + " |"
    rule = "|---" * (len(columns) + 1) + "|"
    rows = []
    for r in records:
        cells = [_cell(r.get(key, "")) for key, _label in columns]
        rows.append("| " + r["name"] + " | " + " | ".join(cells) + " |")
    return "\n".join([head, rule, *rows])


def render(tier_a, tier_b, cutoff, screener_sha):
    now = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    a_records = list(tier_a.values())
    survivors = gates.rank(a_records)
    b_records = list(tier_b.values())

    out = []
    out.append("# Repo screener report\n")
    out.append("## 1. Run metadata\n")
    out.append(f"- Generated: {now}")
    out.append(f"- Freshness cutoff: `{cutoff}`")
    out.append(f"- Screener commit: `{screener_sha}`")
    out.append(f"- Candidates screened: {len(a_records)}")
    out.append(f"- Tier A survivors: {len(survivors)}")
    out.append(f"- Tier B finalists: {len(b_records)}\n")

    out.append("## 2. Gate ledger\n")
    out.append("Every candidate, including eliminated ones. A screener that "
               "reports only survivors is indistinguishable from one with a "
               "bug in its gates.\n")
    out.append("| repo | status | reason | head_sha |")
    out.append("|---|---|---|---|")
    for r in sorted(a_records, key=lambda x: x["name"]):
        out.append("| {} | `{}` | {} | `{}` |".format(
            r["name"], r.get("status", "?"), r.get("reason") or "",
            (r.get("head_sha") or "")[:8]))
    out.append("")
    out.append("Gate definitions:\n")
    for gate_id, desc, _p in gates.TIER_A_GATES:
        out.append(f"- **{gate_id}** — {desc}")
    for gate_id, desc, _p in gates.TIER_B_GATES:
        out.append(f"- **{gate_id}** — {desc}")
    out.append("")

    out.append("## 3. Ranked survivors\n")
    if survivors:
        out.append("Ranked on `projected_capsules` alone. All other columns "
                   "are reported, not scored.\n")
        out.append(_table(survivors, A_COLUMNS))
    else:
        out.append("No candidate cleared all Tier A gates.")
    out.append("")

    out.append("## 4. Tier B finalists\n")
    if b_records:
        out.append(_table(b_records, B_COLUMNS))
        out.append("")
        out.append("`harden_h` and `verify_h` are soft thresholds, not gates, "
                   "and do not affect ranking.")
        out.append("")
        out.append("**Budget caveat.** `warm_s` measures a whole `docker run` "
                   "per invocation, not test execution: on click warm (0.90 s) "
                   "and cold (0.93 s) are indistinguishable because both are "
                   "dominated by container startup. `harden_h` is therefore "
                   "roughly *invocations x container start*, not a measured "
                   "hardening cost. Hardening that reuses one container would "
                   "be substantially cheaper than the figure shown.")
        skipped = [(r["name"], sk) for r in b_records
                   for sk in (r.get("skipped_tests") or [])]
        if skipped:
            out.append("")
            out.append("**Recorded B2 skips.** Gate B2 reads \"all tests pass "
                       "at HEAD, modulo a recorded skip list\". Every skip is "
                       "declared in `candidates.yaml` and reproduced here so "
                       "it is never silently invisible:\n")
            for name, sk in skipped:
                out.append(f"- `{name}` — `{sk['test']}`  \n  "
                           f"{sk.get('reason', '').strip()}")
        stale = [(r["name"], s) for r in b_records
                 for s in (r.get("stale_skips") or [])]
        if stale:
            out.append("")
            out.append("**STALE SKIPS — these matched no test that ran.** A "
                       "stale skip can hide a real failure and must be fixed "
                       "or removed:\n")
            for name, s in stale:
                out.append(f"- `{name}` — `{s}`")
    else:
        out.append("Tier B has not been run.")
    out.append("")

    out.append("## 5. Recommendation\n")
    passed_b = [r for r in b_records if r.get("status") == "passed"]
    # Ranked on `projected_capsules`, the spec's single ranking key, read
    # from the Tier A record. It was previously sorted on `hardening_hours`,
    # which the spec declares a SOFT THRESHOLD precisely so it decides
    # nothing -- that silently promoted a budget estimate to the corpus
    # selection key and picked an 8.98-capsule repo over a 15.51-capsule one.
    # Budgets stay as reported columns: they inform, they do not choose.
    passed_b.sort(key=lambda r: tier_a.get(r["name"], {}).get(
        "projected_capsules", 0), reverse=True)
    if passed_b:
        top = passed_b[0]
        out.append(f"**Corpus repo: `{top['name']}`** — cleared Tier A and "
                   f"Tier B, environment rung {top.get('env_rung')}, "
                   f"{top.get('operator_minutes')} operator minutes, "
                   f"hardening budget {top.get('hardening_hours')} h.\n")
        out.append("Runners-up by diversity tag, for repos 2 and 3 without "
                   "re-running Tier A:\n")
        # Runners-up are restricted to Tier B PASSERS, and anything else is
        # labelled explicitly. Deduplicating on diversity tag alone offered
        # urllib3 -- gated:B2 in section 4 -- as repo 2 while suppressing
        # starlette, which shares the `io` tag and passed cleanly. The list
        # exists to pick maximally different repos that actually work, so a
        # gated or unmeasured entry must never be quoted as settled.
        seen = {top.get("tag")}
        for r in survivors:
            tag = r.get("tag")
            if tag in seen:
                continue
            same = [x for x in survivors if x.get("tag") == tag]
            passer = next(
                (x for x in same
                 if tier_b.get(x["name"], {}).get("status") == "passed"), None)
            chosen = passer or same[0]
            status = tier_b.get(chosen["name"], {}).get("status")
            if status == "passed":
                label = ""
            elif status:
                label = f" — **not selectable: Tier B `{status}`**"
            else:
                label = " — **not measured in Tier B**"
            out.append(f"- `{chosen['name']}` ({tag}) — "
                       f"{chosen.get('projected_capsules')} projected "
                       f"capsules{label}")
            seen.add(tag)
    else:
        out.append("No finalist cleared Tier B. Review the gate ledger.")
    out.append("")
    return "\n".join(out)
