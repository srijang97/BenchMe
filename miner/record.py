"""Candidate records and the append-only JSONL store.

A record is keyed by the candidate commit sha. Statuses:
  validated          fail-to-pass established, assertion-class, regressions clean
  rejected:<reason>  a real verdict about the commit
  apparatus          our fault (OOM, build failure, patch would not apply)
  error              miner bug; traceback recorded, sweep continues

rejected and apparatus are kept rigidly separate. The screener's central
lesson was that six of seven eliminations were the apparatus rather than the
subject, and that was only visible because the two were recorded differently.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BENCH = ROOT.parent
REPO = BENCH / "screener" / "work" / "pydantic"
OUT = ROOT / "out"
CANDIDATES = OUT / "candidates.jsonl"
VALIDATED = OUT / "validated.jsonl"
LOGS = OUT / "logs"


def append(path, record):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def read_all(path):
    """Return {sha: record}; last write wins."""
    records = {}
    p = Path(path)
    if not p.exists():
        return records
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                records[rec["sha"]] = rec
    return records


def is_done(record):
    """error is NOT terminal -- a miner bug should be retried after a fix."""
    status = record.get("status", "")
    return status == "validated" or status == "apparatus" \
        or status.startswith("rejected:")
