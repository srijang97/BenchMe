"""Hard gates and ranking. Gates eliminate; one key ranks; no composite score."""

CUTOFF_MIN_PAIRS = 360        # G2: 360 * 0.022 = 7.92 ~ 8 capsules
CUTOFF_MIN_FRESH_COMMITS = 30  # G3
MIN_TEST_MAP_RATIO = 0.5       # G4
MAX_OPERATOR_MINUTES = 120     # B1
MAX_FLAKE_RATE = 0.005         # B3
MAX_NET_DEPENDENT_SHARE = 0.02  # B4


def _g1(r):
    if not r.get("uses_pytest"):
        return "no pytest configuration detected"
    return None


def _g2(r):
    n = r.get("candidate_pairs", 0)
    if n < CUTOFF_MIN_PAIRS:
        return f"candidate_pairs {n} < {CUTOFF_MIN_PAIRS}"
    return None


def _g3(r):
    n = r.get("commits_since_cutoff", 0)
    if n < CUTOFF_MIN_FRESH_COMMITS:
        return f"commits_since_cutoff {n} < {CUTOFF_MIN_FRESH_COMMITS}"
    return None


def _g4(r):
    v = r.get("test_map_ratio", 0.0)
    if v < MIN_TEST_MAP_RATIO:
        return f"test_map_ratio {v} < {MIN_TEST_MAP_RATIO}"
    return None


def _g5(r):
    m = r.get("compiled_markers") or []
    if m:
        return f"compiled extension built from source: {', '.join(m[:3])}"
    return None


def _g6(r):
    m = r.get("service_markers") or []
    if m:
        return f"service dependency referenced in: {', '.join(m[:3])}"
    return None


def _g7(r):
    if not r.get("lockfile"):
        if r.get("requirements_unpinned"):
            return "requirements file present but not pinned (<80% of lines pinned)"
        return "no lockfile or pinned requirements"
    return None


TIER_A_GATES = [
    ("G1", "Python + pytest detected", _g1),
    ("G2", "candidate_pairs >= 360", _g2),
    ("G3", "commits_since_cutoff >= 30", _g3),
    ("G4", "test_map_ratio >= 0.5", _g4),
    ("G5", "no compiled extension built from source", _g5),
    ("G6", "no service dependency on default test path", _g6),
    ("G7", "lockfile or pinned dependencies present", _g7),
]


def _b1(r):
    if r.get("env_rung") in (None, 0):
        return "no usable environment definition"
    if r.get("operator_minutes", 0) > MAX_OPERATOR_MINUTES:
        return f"operator_minutes {r['operator_minutes']} > {MAX_OPERATOR_MINUTES}"
    return None


def _b2(r):
    if not r.get("head_green"):
        return "suite not green at HEAD"
    return None


def _b3(r):
    v = r.get("flake_rate", 1.0)
    if v > MAX_FLAKE_RATE:
        return f"flake_rate {v} > {MAX_FLAKE_RATE}"
    return None


def _b4(r):
    total = r.get("test_count", 0)
    net = len(r.get("net_dependent_tests") or [])
    if total and (net / total) > MAX_NET_DEPENDENT_SHARE:
        if r.get("net_marker_excludable"):
            return None
        return f"net_dependent_tests {net}/{total} and not marker-excludable"
    return None


TIER_B_GATES = [
    ("B1", "environment builds at rung <=4 within 120 operator minutes", _b1),
    ("B2", "suite green at HEAD", _b2),
    ("B3", "flake_rate <= 0.5%", _b3),
    ("B4", "network-dependent tests <=2% or marker-excludable", _b4),
]


def _evaluate(record, gates):
    for gate_id, _desc, predicate in gates:
        reason = predicate(record)
        if reason is not None:
            return f"gated:{gate_id}", reason
    return "passed", None


def evaluate_tier_a(record):
    return _evaluate(record, TIER_A_GATES)


def evaluate_tier_b(record):
    return _evaluate(record, TIER_B_GATES)


def rank(records):
    """Survivors only, ranked on the single key. No composite score."""
    survivors = [r for r in records if r.get("status") == "passed"]
    return sorted(survivors, key=lambda r: r.get("projected_capsules", 0),
                  reverse=True)
