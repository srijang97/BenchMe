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

B_COLUMNS = [
    ("env_rung", "rung"),
    ("operator_minutes", "op_min"),
    ("head_green", "green"),
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
        out.append("`harden_h` and `verify_h` are soft thresholds, not gates.")
    else:
        out.append("Tier B has not been run.")
    out.append("")

    out.append("## 5. Recommendation\n")
    passed_b = [r for r in b_records if r.get("status") == "passed"]
    passed_b.sort(key=lambda r: r.get("hardening_hours", 1e9))
    if passed_b:
        top = passed_b[0]
        out.append(f"**Corpus repo: `{top['name']}`** — cleared Tier A and "
                   f"Tier B, environment rung {top.get('env_rung')}, "
                   f"{top.get('operator_minutes')} operator minutes, "
                   f"hardening budget {top.get('hardening_hours')} h.\n")
        out.append("Runners-up by diversity tag, for repos 2 and 3 without "
                   "re-running Tier A:\n")
        seen = {top.get("tag")}
        for r in survivors:
            if r.get("tag") not in seen:
                out.append(f"- `{r['name']}` ({r.get('tag')}) — "
                           f"{r.get('projected_capsules')} projected capsules")
                seen.add(r.get("tag"))
    else:
        out.append("No finalist cleared Tier B. Review the gate ledger.")
    out.append("")
    return "\n".join(out)
