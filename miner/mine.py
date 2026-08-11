"""BenchMe capsule miner, stages 0-2.

See docs/superpowers/specs/2026-08-11-miner-stages-0-2-design.md
"""
import argparse
import sys

import record


def cmd_enumerate(args):
    import candidates

    rows = candidates.enumerate_candidates(record.REPO)
    ordered = candidates.stratified_order(rows)
    record.CANDIDATES.unlink(missing_ok=True)
    for r in ordered:
        record.append(record.CANDIDATES, r)

    by_q = {}
    for r in ordered:
        by_q[r["quarter"]] = by_q.get(r["quarter"], 0) + 1
    print(f"enumerated {len(ordered)} candidates")
    for q in sorted(by_q, reverse=True)[:12]:
        print(f"  {q}: {by_q[q]}")
    return 0


def cmd_validate(args):
    print("validate not implemented yet", file=sys.stderr)
    return 1


def cmd_report(args):
    print("report not implemented yet", file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mine")
    sub = parser.add_subparsers(dest="command", required=True)

    e = sub.add_parser("enumerate", help="stages 0-1 over the whole history")
    e.set_defaults(func=cmd_enumerate)

    v = sub.add_parser("validate", help="stage 2 for one repo-quarter")
    v.add_argument("--quarter", required=True, help="e.g. 2025Q3")
    v.add_argument("--limit", type=int, default=10,
                   help="sampling budget for this batch; recorded in the report")
    v.add_argument("--keep-images", action="store_true")
    v.add_argument("--force", action="store_true")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("report", help="render the funnel")
    r.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    for d in (record.OUT, record.LOGS):
        d.mkdir(parents=True, exist_ok=True)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
