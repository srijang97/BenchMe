"""BenchMe repo screener.

Two tiers. Tier A reads git metadata only and never executes repository code.
Tier B builds a container and runs the suite for the top N survivors.

See docs/superpowers/specs/2026-08-10-repo-screener-design.md
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
WORK = ROOT / "work"
LOGS = OUT / "logs"
TIER_A = OUT / "tier_a.jsonl"
TIER_B = OUT / "tier_b.jsonl"

TERMINAL = ("passed", "unavailable")


def load_candidates(path):
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["candidates"]


def read_records(path):
    """Return {name: record} keyed by name, last write wins."""
    records = {}
    p = Path(path)
    if not p.exists():
        return records
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records[rec["name"]] = rec
    return records


def append_record(path, record):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def is_done(record):
    """A record is done if it reached a terminal state. gated:* counts as done."""
    status = record.get("status", "")
    return status in TERMINAL or status.startswith("gated:")


def operator_minutes_for(name, args):
    """Minutes the operator spent getting this repo's suite green.

    Spec section 4.1 makes this a human-supplied number on purpose: it is the
    leading indicator on the services-trap gate. It therefore FAILS CLOSED
    rather than defaulting to 0 -- a silently fabricated 0 would corrupt the
    one metric that says whether this is a product or a consultancy.
    """
    mapping = {}
    for pair in getattr(args, "operator_minutes", []) or []:
        key, _, value = pair.partition("=")
        mapping[key.strip()] = value.strip()
    if name in mapping:
        return int(mapping[name])
    if sys.stdin.isatty():
        return int(input(f"  operator minutes spent on {name}: ").strip() or 0)
    raise SystemExit(
        f"operator_minutes for '{name}' was not supplied and stdin is not a "
        f"terminal. Re-run with --operator-minutes {name}=<minutes>."
    )


def cmd_tier_a(args):
    import gates
    import gitmeta
    import metrics

    candidates = load_candidates(args.candidates)
    done = read_records(TIER_A)
    for cand in candidates:
        name = cand["name"]
        if not args.force and name in done and is_done(done[name]):
            print(f"skip {name} ({done[name]['status']})")
            continue
        log_dir = LOGS / name
        dest = WORK / name
        print(f"tier-a {name} ...", flush=True)
        record = {"name": name, "url": cand["url"], "tag": cand["tag"],
                  "note": cand.get("note", ""), "cutoff": args.cutoff}
        try:
            # clone() is total by contract, but it stays INSIDE the guard so a
            # future regression there degrades one candidate instead of
            # aborting the sweep. Spec section 6: the sweep never aborts.
            if not gitmeta.clone(cand["url"], dest, log_dir):
                record.update(status="unavailable",
                              reason="clone failed after retry")
                append_record(TIER_A, record)
                continue
            commits = gitmeta.log_commits(dest)
            tracked = gitmeta.tracked_files(dest)
            record["head_sha"] = gitmeta.head_sha(dest)
            record.update(metrics.compute_tier_a(commits, tracked, dest,
                                                 args.cutoff))
        except Exception as exc:  # a screener bug, not a repo verdict
            record.update(status="error", reason=f"{type(exc).__name__}: {exc}")
            append_record(TIER_A, record)
            continue
        status, reason = gates.evaluate_tier_a(record)
        record.update(status=status, reason=reason)
        append_record(TIER_A, record)
        print(f"  {status} {reason or ''}")
    return 0


def cmd_tier_b(args):
    print("tier-b not implemented yet", file=sys.stderr)
    return 1


def cmd_report(args):
    import subprocess

    import report

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         cwd=str(ROOT.parent), capture_output=True,
                         text=True).stdout.strip() or "unknown"
    text = report.render(read_records(TIER_A), read_records(TIER_B),
                         args.cutoff, sha)
    path = OUT / "REPORT.md"
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="screen")
    parser.add_argument("--candidates", default=str(ROOT / "candidates.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("tier-a", help="static git-metadata screen, all candidates")
    a.add_argument("--cutoff", default="2026-05-01")
    a.add_argument("--force", action="store_true")
    a.set_defaults(func=cmd_tier_a)

    b = sub.add_parser("tier-b", help="container build and suite measurement, finalists only")
    b.add_argument("--top", type=int, default=4)
    b.add_argument("--force", action="store_true")
    b.add_argument("--operator-minutes", action="append", default=[],
                   metavar="NAME=MINUTES",
                   help="minutes you spent per repo, e.g. --operator-minutes click=35. "
                        "Required when stdin is not a terminal.")
    b.set_defaults(func=cmd_tier_b)

    r = sub.add_parser("report", help="render REPORT.md")
    r.add_argument("--cutoff", default="2026-05-01")
    r.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    for d in (OUT, WORK, LOGS):
        d.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
