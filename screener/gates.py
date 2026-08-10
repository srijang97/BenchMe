"""Hard gates and ranking. Gates eliminate; one key ranks; no composite score."""

CUTOFF_MIN_PAIRS = 360        # G2: 360 * 0.022 = 7.92 ~ 8 capsules
CUTOFF_MIN_FRESH_COMMITS = 30  # G3
MIN_TEST_MAP_RATIO = 0.5       # G4 -- RETIRED, used only by the unused _g4
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
    """RETIRED -- withdrawn from TIER_A_GATES, see the note above TIER_A_GATES.

    Kept unused and deliberately: `test_map_ratio` and `test_map_ambiguous` are
    still computed and still reported, they simply stop being fatal.
    """
    v = r.get("test_map_ratio", 0.0)
    if v < MIN_TEST_MAP_RATIO:
        return f"test_map_ratio {v} < {MIN_TEST_MAP_RATIO}"
    return None


def _g5(r):
    """RETIRED -- withdrawn from TIER_A_GATES, see the note above TIER_A_GATES.

    Kept unused and deliberately: `compiled_markers` is still computed and
    still reported, it simply stops being fatal.
    """
    m = r.get("compiled_markers") or []
    if m:
        return f"compiled extension built from source: {', '.join(m[:3])}"
    return None


def _g6(r):
    """RETIRED -- withdrawn from TIER_A_GATES, see the note above TIER_A_GATES.

    Kept unused and deliberately: `service_markers` is still computed and
    still reported, it simply stops being fatal.
    """
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


# G4, G5 and G6 are RETIRED, not reused. Each id stays burned so a future
# gate cannot silently inherit it and make the ledger's history lie.
#
# All three failed the same way: each scanned the ENTIRE repository tree
# while purporting to describe the primary package's build and test path, so
# vendored subprojects, examples/ directories and peripheral CI workflows
# tripped them.
#
# G4 (test_map_ratio >= 0.5) measured filename convention, not selectability.
# Capsules are mined from commits that touch source AND tests, so a capsule's
# fail-to-pass tests come from the commit itself -- name-based mapping is
# never required for mutation hardening. Tier B's `targeted_latency` measures
# the real constraint empirically, on finalists. The live sweep was the
# evidence: three of three mature repositories failed G4 while being
# perfectly selectable, because they name test files after behaviours rather
# than modules.
#
# G5 (no compiled extension) and G6 (no service dependency) were withdrawn
# together for a second, structural reason on top of the tree-wide-scan bug:
# they PREDICT environment feasibility, which Tier B MEASURES. B1 builds the
# container, B2 requires the suite green at HEAD, B4 runs it with network
# denied. A repo that genuinely needs a Rust toolchain fails B1; one that
# genuinely needs a database fails B2 or B4. Predicting a priori what a later
# tier measures empirically only adds a false-elimination path. The evidence:
# pydantic -- the highest-yield candidate in the field at 35.13 projected
# capsules against the next survivor's 8.98 -- was eliminated by G5 on
# `pydantic-core/Cargo.toml`, a vendored subproject carrying its own
# pyproject.toml, while the root package's build backend is hatchling and
# installing pydantic compiles no Rust. It would separately have been
# eliminated by G6 on `.github/workflows/third-party.yml`, a third-party
# integration workflow that is not the default test path.
#
# `_g4`, `_g5` and `_g6` are kept above, unused, so the retired rules stay
# readable. `compiled_markers` and `service_markers` are still computed by
# `compute_tier_a` and still reported; they simply stop eliminating.
TIER_A_GATES = [
    ("G1", "Python + pytest detected", _g1),
    ("G2", "candidate_pairs >= 360", _g2),
    ("G3", "commits_since_cutoff >= 30", _g3),
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
