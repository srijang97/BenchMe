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
            # evaluate_tier_a stays INSIDE the guard. It reads a record that a
            # partial failure upstream may have left malformed, so a KeyError
            # or TypeError here is a screener bug and must degrade this one
            # candidate rather than abort the sweep.
            status, reason = gates.evaluate_tier_a(record)
        except Exception as exc:  # a screener bug, not a repo verdict
            record.update(status="error", reason=f"{type(exc).__name__}: {exc}")
            append_record(TIER_A, record)
            continue
        record.update(status=status, reason=reason)
        append_record(TIER_A, record)
        print(f"  {status} {reason or ''}")
    return 0


def tierb_default_user():
    """Read the default lazily so screen.py does not import tierb at parse time."""
    import tierb
    return tierb.DEFAULT_CONTAINER_USER


def cmd_tier_b(args):
    import gates
    import gitmeta
    import tierb

    tier_a = read_records(TIER_A)
    # Per-repo config lives in candidates.yaml so it is version-controlled and
    # visible beside the candidate: currently the recorded B2 skip list.
    config = {c["name"]: c for c in load_candidates(args.candidates)}
    finalists = gates.rank(list(tier_a.values()))[: args.top]
    if not finalists:
        print("no Tier A survivors", file=sys.stderr)
        return 1
    if args.only:
        finalists = [r for r in finalists if r["name"] in args.only]
        if not finalists:
            print(f"none of {args.only} is among the top {args.top} finalists",
                  file=sys.stderr)
            return 1
    done = read_records(TIER_B)
    for cand in finalists:
        name = cand["name"]
        if not args.force and name in done and is_done(done[name]):
            print(f"skip {name} ({done[name]['status']})")
            continue
        repo = WORK / name
        log_dir = LOGS / name
        record = {"name": name, "tag": cand.get("tag")}
        # Everything that touches git, docker or the filesystem runs INSIDE
        # this guard, mirroring cmd_tier_a. Tier B shells out to docker at
        # five sites, each with its own timeout; before this, any one of them
        # raising aborted the sweep AND left the offending repo unrecorded, so
        # the resume path retried it and re-aborted. A screener failure must
        # degrade one candidate, never the run.
        try:
            record["head_sha"] = gitmeta.head_sha(repo)
            tracked = gitmeta.tracked_files(repo)
            rung, source = tierb.detect_rung(repo, tracked)
            record["env_rung"] = rung
            record["env_source"] = source
            print(f"tier-b {name}: rung {rung} ({source})", flush=True)
            if rung == 0:
                record.update(status="gated:B1",
                              reason="no usable environment definition",
                              operator_minutes=0)
                append_record(TIER_B, record)
                continue

            image = tierb.build_image(repo, name, rung, log_dir, record=record)
            if image is None:
                record.update(status="gated:B1",
                              reason="docker build failed; see docker-build.log",
                              operator_minutes=0)
                append_record(TIER_B, record)
                continue

            # The build may have generated source files inside the image's
            # /repo; the measurement mount would otherwise replace them.
            generated = tierb.sync_generated(image, repo, log_dir)
            record["generated_restored"] = generated[:20]
            record["generated_count"] = len(generated)

            record["operator_minutes"] = operator_minutes_for(name, args)
            skips = config.get(name, {}).get("skip_tests") or []
            record.update(tierb.measure(image, repo, log_dir,
                                        user=args.container_user, skips=skips))
        except Exception as exc:  # a screener bug, not a repo verdict
            record.update(status="error", reason=f"{type(exc).__name__}: {exc}")
            append_record(TIER_B, record)
            print(f"  error {type(exc).__name__}: {exc}", file=sys.stderr)
            continue

        if record.get("stale_skips"):
            print(f"  !! STALE SKIP for {name}: "
                  f"{', '.join(record['stale_skips'])} -- configured in "
                  f"candidates.yaml but matched no test that ran. A stale "
                  f"skip can hide a real failure; fix or remove it.",
                  file=sys.stderr, flush=True)
        for sk in record.get("skipped_tests") or []:
            print(f"  skipped {sk['test']}", flush=True)

        # An apparatus error is NOT a gate verdict. A dead container run makes
        # every id differ between runs, which would otherwise surface as
        # `gated:B3 flake_rate 1.0` -- eliminating a repo for our fault.
        if record.get("apparatus_error"):
            record.update(status="error",
                          reason=f"apparatus: {record['apparatus_error']}")
            append_record(TIER_B, record)
            print(f"  error apparatus: {record['apparatus_error']}",
                  file=sys.stderr)
            continue

        record.update(tierb.budgets(record))
        status, reason = gates.evaluate_tier_b(record)
        record.update(status=status, reason=reason)
        append_record(TIER_B, record)
        print(f"  {status} {reason or ''}")
    return 0


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
    b.add_argument("--container-user", default=tierb_default_user(),
                   metavar="UID:GID",
                   help="uid:gid the suite runs as inside the container "
                        "(default 1000:1000). Pass an empty string to run as "
                        "root, which is NOT recommended: root bypasses Unix "
                        "permission bits, manufacturing false failures on "
                        "tests that assert access is denied and masking real "
                        "ones. The value used is recorded per repo.")
    b.add_argument("--only", action="append", default=[], metavar="NAME",
                   help="restrict to these finalists, e.g. --only click. "
                        "Filters WITHIN the top N -- it never promotes a repo "
                        "the ranking did not already select, so it cannot be "
                        "used to slip a lower-ranked candidate into Tier B.")
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
