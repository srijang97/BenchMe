"""Compare the 2025Q3 re-run against the hand-audited pre-redesign batch.

The pre-redesign batch was adjudicated by hand: of its ten rejections, seven
were traced to our own defects rather than to properties of the commits. That
audit is the known answer this script checks the redesigned classifier against.

Run:  python miner/compare_rerun.py
"""
import collections
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
OLD = OUT / "validated.2025Q3-preredesign.jsonl"
NEW = OUT / "validated.jsonl"


def load(path, skip=0):
    """{sha: record}, last write wins -- pass 2 supersedes pass 1."""
    records = {}
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i < skip or not line.strip():
                continue
            rec = json.loads(line)
            records[rec["sha"]] = rec
    return records


def main():
    if not OLD.exists():
        sys.exit(f"missing baseline: {OLD}")
    old = load(OLD)
    # The new records were appended after the archived baseline, so skip the
    # first len(old) lines of the live file rather than assuming a clean file.
    # The live file is append-only and now holds more than one re-run, so a
    # fixed skip would read a stale run. load() is last-write-wins by sha, so
    # reading the whole file yields the MOST RECENT verdict per candidate --
    # which is what "the current code's answer" means.
    new = load(NEW)

    print(f"baseline: {len(old)} candidates    re-run: {len(new)} candidates\n")

    print("STATUS COUNTS")
    oc = collections.Counter(r["status"] for r in old.values())
    nc = collections.Counter(r["status"] for r in new.values())
    for status in sorted(set(oc) | set(nc)):
        arrow = "" if oc.get(status, 0) == nc.get(status, 0) else "   <--"
        print(f"  {status:30} {oc.get(status, 0):3} -> {nc.get(status, 0):3}{arrow}")

    print("\nPER CANDIDATE")
    changed = same = 0
    for sha in old:
        o = old[sha]["status"]
        n = new[sha]["status"] if sha in new else "(not attempted)"
        mark = " " if o == n else "*"
        if o == n:
            same += 1
        else:
            changed += 1
        reason = (new[sha].get("reason") if sha in new else "") or ""
        print(f" {mark} {sha[:8]}  {o:28} -> {n:28} {reason[:52]}")
    print(f"\n  {changed} changed, {same} unchanged")

    print("\nORACLE LABELS on validated capsules")
    labels = collections.Counter()
    for rec in new.values():
        if rec.get("status") == "validated":
            labels.update((rec.get("failure_labels") or {}).values())
    if not labels:
        print("  (none)")
    for lbl, n in labels.most_common():
        print(f"  {lbl:28} {n}")

    print("\nAPPARATUS RATE")
    # "processed", not "adjudicated": report.py reserves "adjudicated" for
    # validated + rejected, which excludes apparatus by definition and so
    # cannot be this rate's denominator. Same word, two denominators, is how a
    # reader quotes one rate as the other.
    processed = [r for r in new.values() if r.get("status") != "error"]
    apparatus = [r for r in processed if r.get("status") == "apparatus"]
    if processed:
        rate = 100.0 * len(apparatus) / len(processed)
        print(f"  {len(apparatus)}/{len(processed)} processed = {rate:.1f}%"
              f"   (tripwire at 10%)")

    print("\nDETERMINISM (pass-1 oracle reproduced in pass 2)")
    seen = False
    for sha, rec in new.items():
        if "f2p_pass1" in rec:
            seen = True
            print(f"  {sha[:8]} {len(rec.get('f2p_reproduced') or [])}"
                  f"/{len(rec.get('f2p_pass1') or [])} reproduced"
                  f"   status={rec['status']}")
    if not seen:
        print("  (no candidate reached pass 2)")


if __name__ == "__main__":
    main()
