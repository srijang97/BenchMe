"""
BenchMe evaluation cost model.
Anchored on measured telemetry from demo run 20260709T224810Z (pallets/itsdangerous).
API rates verified 2026-08-04.
"""
import json
from dataclasses import dataclass, asdict

# ----------------------------------------------------------------------------
# 1. RATE CARD  ($ per 1M tokens)   verified 2026-08-04
#    cache_write_mult = multiplier on base input for writing to cache
#    cache_read = price of a cache hit
#    cacheable  = does this endpoint support prompt caching in agentic harnesses
# ----------------------------------------------------------------------------
RATES = {
    # --- frontier closed ---
    "Claude Fable 5":      dict(inp=10.0, out=50.0, cw=1.25, cr=1.00, cache=True,  tier="frontier"),
    "Claude Opus 5":       dict(inp=5.00, out=25.0, cw=1.25, cr=0.50, cache=True,  tier="frontier"),
    "Claude Sonnet 5":     dict(inp=2.00, out=10.0, cw=1.25, cr=0.20, cache=True,  tier="frontier"),  # intro thru Aug 31
    "Claude Sonnet 5 (Sep+)": dict(inp=3.00, out=15.0, cw=1.25, cr=0.30, cache=True, tier="frontier"),
    "Claude Haiku 4.5":    dict(inp=1.00, out=5.00, cw=1.25, cr=0.10, cache=True,  tier="cheap"),
    "GPT-5.6 Sol":         dict(inp=5.00, out=30.0, cw=1.00, cr=0.50, cache=True,  tier="frontier"),
    "GPT-5.6 Terra":       dict(inp=2.00, out=12.0, cw=1.00, cr=0.20, cache=True,  tier="frontier"),
    "GPT-5.5":             dict(inp=5.00, out=30.0, cw=1.00, cr=0.50, cache=True,  tier="frontier"),
    "GPT-5.4":             dict(inp=2.50, out=15.0, cw=1.00, cr=0.25, cache=True,  tier="frontier"),
    "GPT-5.4 mini":        dict(inp=0.75, out=4.50, cw=1.00, cr=0.075,cache=True,  tier="cheap"),
    "GPT-5.6 Luna":        dict(inp=0.20, out=1.20, cw=1.00, cr=0.02, cache=True,  tier="cheap"),
    # --- open weight, hosted API ---
    "GLM-5.2":             dict(inp=1.40, out=4.40, cw=1.00, cr=0.28, cache=True,  tier="open"),
    "GLM-5":               dict(inp=1.00, out=3.20, cw=1.00, cr=0.20, cache=True,  tier="open"),
    "Kimi K2.6":           dict(inp=0.95, out=4.00, cw=1.00, cr=0.19, cache=True,  tier="open"),
    "Kimi K2.7 Code":      dict(inp=0.95, out=4.00, cw=1.00, cr=0.19, cache=True,  tier="open"),
    "DeepSeek V4 Pro":     dict(inp=0.43, out=0.87, cw=1.00, cr=0.043,cache=True,  tier="open"),
    "DeepSeek V4 Flash":   dict(inp=0.14, out=0.28, cw=1.00, cr=0.014,cache=True,  tier="open"),
    "MiniMax M3":          dict(inp=0.30, out=1.20, cw=1.00, cr=0.30, cache=False, tier="open"),
    "Qwen3.5 Plus":        dict(inp=0.40, out=2.40, cw=1.00, cr=0.40, cache=False, tier="open"),
    "Qwen3.7 Flash":       dict(inp=0.03, out=0.13, cw=1.00, cr=0.03, cache=False, tier="open"),
}

# ----------------------------------------------------------------------------
# 2. WORKLOAD ANCHOR — measured, BenchMe demo 20260709T224810Z
#    single feature task on a 36-file repo, Codex harness, medium reasoning
# ----------------------------------------------------------------------------
MEASURED = {
    "gpt-5.5":      dict(inp=663_652,   out=8_450,  sec=197.1),
    "gpt-5.4":      dict(inp=487_121,   out=7_201,  sec=158.5),
    "gpt-5.4-mini": dict(inp=1_031_987, out=20_713, sec=324.9),
}
ANCHOR_IN, ANCHOR_OUT = 487_121, 7_201     # gpt-5.4, the median behaviour

# Difficulty tiers as multipliers on the anchor.
# The anchor repo is TINY (36 files). Enterprise repos carry far more context/turn.
DIFFICULTY = {
    "T1 trivial (dep bump, lint fix)":        0.35,
    "T2 small (bug fix from issue)":          0.70,
    "T3 medium (feature w/ spec) = anchor":   1.00,
    "T4 hard (multi-file, large repo)":       3.00,
    "T5 very hard (monorepo, long horizon)":  6.50,
}

# Harness overhead. Databricks measured >2x cost spread for one model across
# harnesses, driven by ~3x difference in context fed per turn.
HARNESS = {
    "lean (mini-SWE-agent / Aider)": 0.55,
    "Codex CLI":                     1.00,
    "Claude Code":                   1.35,
    "OpenHands":                     1.60,
    "context-heavy internal":        2.20,
}


# Token efficiency: weaker models take MORE turns to reach the same outcome,
# so they burn more tokens. Measured in the demo: gpt-5.4-mini consumed 2.12x
# the input and 2.88x the output of gpt-5.4 on the identical task.
# This is the effect that erases much of the cheap-model price advantage.
TOKEN_MULT = {"frontier": 1.00, "open": 1.45, "cheap": 2.10}

# Default pass rates by tier - weaker models also solve fewer tasks, which
# compounds into cost-per-SOLVED-task.
PASS_RATE = {"frontier": 0.60, "open": 0.50, "cheap": 0.33}


def per_run_cost(model, in_tok, out_tok, cache_hit=0.85):
    """Cost of ONE agent trajectory."""
    r = RATES[model]
    h = cache_hit if r["cache"] else 0.0
    eff_in = h * r["cr"] + (1 - h) * r["inp"] * r["cw"]
    return in_tok / 1e6 * eff_in + out_tok / 1e6 * r["out"]


def per_task_expected(model, difficulty=1.0, harness=1.0, cache_hit=0.85,
                      pass_rate=None, fail_mult=2.5):
    """
    Expected cost of one ATTEMPT, and cost per SOLVED task.
    fail_mult: failed trajectories burn more tokens (they run to the cap).
               SWE-Effi measured 8.8M vs 1.8M tokens (~4.9x); 2.5x is conservative.
    """
    tier = RATES[model]["tier"]
    if pass_rate is None:
        pass_rate = PASS_RATE[tier]
    scale = difficulty * harness * TOKEN_MULT[tier]
    base = per_run_cost(model, ANCHOR_IN * scale, ANCHOR_OUT * scale, cache_hit)
    attempt = pass_rate * base + (1 - pass_rate) * base * fail_mult
    return attempt, attempt / pass_rate


def sweep_cost(models, n_tasks, k, difficulty=1.0, harness=1.0,
               cache_hit=0.85, pass_rate=None, fail_mult=2.5,
               seq_stop_saving=0.0):
    """Total $ for a paired sweep: every model sees every task, k trials each."""
    total = 0.0
    detail = {}
    for m in models:
        att, _ = per_task_expected(m, difficulty, harness, cache_hit,
                                   pass_rate, fail_mult)
        c = att * n_tasks * k
        detail[m] = c
        total += c
    total *= (1 - seq_stop_saving)
    detail = {m: v * (1 - seq_stop_saving) for m, v in detail.items()}
    return total, detail


if __name__ == "__main__":
    out = {}

    # --- A. validate the model against the measured demo run ---
    va = {}
    for name, rate_key in [("gpt-5.5", "GPT-5.5"), ("gpt-5.4", "GPT-5.4"),
                           ("gpt-5.4-mini", "GPT-5.4 mini")]:
        m = MEASURED[name]
        va[name] = {
            "in_tok": m["inp"], "out_tok": m["out"], "sec": m["sec"],
            "cost_nocache": round(per_run_cost(rate_key, m["inp"], m["out"], 0.0), 3),
            "cost_cache50": round(per_run_cost(rate_key, m["inp"], m["out"], 0.50), 3),
            "cost_cache85": round(per_run_cost(rate_key, m["inp"], m["out"], 0.85), 3),
            "cost_cache92": round(per_run_cost(rate_key, m["inp"], m["out"], 0.92), 3),
        }
    out["A_measured_run_costs"] = va

    # --- B. cost per solved task, by model, at T3 medium, Codex harness ---
    b = {}
    for m in RATES:
        att, solved = per_task_expected(m)
        b[m] = {"tier": RATES[m]["tier"],
                "pass_rate_assumed": PASS_RATE[RATES[m]["tier"]],
                "per_attempt": round(att, 3),
                "per_solved": round(solved, 3),
                "per_solved_nocache": round(
                    per_task_expected(m, cache_hit=0.0)[1], 3)}
    out["B_per_task_by_model"] = b

    # --- C. difficulty ladder for representative models ---
    c = {}
    for m in ["Claude Opus 5", "GPT-5.4", "GLM-5.2", "DeepSeek V4 Pro", "GPT-5.4 mini"]:
        c[m] = {d: round(per_task_expected(m, difficulty=mult)[1], 2)
                for d, mult in DIFFICULTY.items()}
    out["C_difficulty_ladder"] = c

    # --- D. harness overhead, one model ---
    out["D_harness_overhead"] = {
        hn: round(per_task_expected("GPT-5.4", harness=hm)[1], 2)
        for hn, hm in HARNESS.items()}

    # --- D2. validation against Databricks published per-task figures ---
    out["D2_databricks_check"] = {
        "published_GLM_5.2_per_task": 1.28,
        "modelled_GLM_5.2_per_attempt_T4": round(
            per_task_expected("GLM-5.2", difficulty=3.0)[0], 2),
        "published_Opus_4.8_per_task": 1.94,
        "modelled_Opus_5_per_attempt_T4": round(
            per_task_expected("Claude Opus 5", difficulty=3.0)[0], 2),
        "HAL_swebench_per_task_range": "0.13 - 0.73",
        "modelled_GPT_5.4_per_attempt_T2": round(
            per_task_expected("GPT-5.4", difficulty=0.70)[0], 2),
    }

    # --- E. THE SCENARIOS ---
    frontier6 = ["Claude Opus 5", "Claude Sonnet 5", "GPT-5.6 Sol", "GPT-5.4",
                 "GLM-5.2", "Kimi K2.6"]
    lean4 = ["Claude Sonnet 5", "GPT-5.4", "GLM-5.2", "DeepSeek V4 Pro"]
    cheap4 = ["Claude Haiku 4.5", "GPT-5.4 mini", "DeepSeek V4 Pro", "Qwen3.5 Plus"]

    scen = {}

    def add(name, models, n, k, diff, seq=0.0, note=""):
        t, d = sweep_cost(models, n, k, difficulty=diff, seq_stop_saving=seq)
        scen[name] = {"n_tasks": n, "k": k, "configs": len(models),
                      "trajectories": n * k * len(models),
                      "difficulty": diff, "total": round(t, 0),
                      "per_config": {m: round(v, 0) for m, v in d.items()},
                      "note": note}

    add("S1 nightly smoke", ["GPT-5.4"], 20, 1, 0.70,
        note="1 production config, easy tasks, k=1 - guardrail only")
    add("S2 weekly regression (config change)", ["GPT-5.4", "GPT-5.4"], 60, 3, 1.00,
        note="A/B of two AGENTS.md variants, same model")
    add("S3 pilot bake-off (realistic)", lean4, 30, 5, 1.00,
        note="4 configs, 30 tasks, k=5 -> MDE ~12.5pp")
    add("S4 release gate (teardown spec)", frontier6, 200, 5, 1.00,
        note="the 6,000-trajectory sweep from the teardown")
    add("S4b release gate + sequential stopping", frontier6, 200, 5, 1.00, seq=0.50,
        note="same, with 50% compute killed early")
    add("S5 hard-task gate (enterprise monorepo)", lean4, 100, 5, 3.00,
        note="T4 hard tasks, big repo context")
    add("S6 cheap-model screen", cheap4, 200, 5, 1.00,
        note="screening pass on cheap tier before spending on frontier")
    out["E_scenarios"] = scen

    # --- F. cache sensitivity on the big sweep ---
    out["F_cache_sensitivity"] = {
        f"{int(h*100)}% cache hit": round(
            sweep_cost(frontier6, 200, 5, cache_hit=h)[0], 0)
        for h in [0.0, 0.30, 0.50, 0.70, 0.85, 0.92]}

    # --- G. annual run rate for one enterprise customer ---
    # Realistic enterprise repo: difficulty 2.0 blend (T3/T4), Claude Code harness
    ENT = dict(difficulty=2.0, harness=1.35)
    n_smoke, _ = sweep_cost(["GPT-5.4"], 20, 1, **ENT)
    n_week, _ = sweep_cost(["GPT-5.4", "GPT-5.4"], 60, 3, **ENT)
    n_gate, _ = sweep_cost(frontier6, 200, 5, seq_stop_saving=0.50, **ENT)
    out["G_annual_one_customer_ENTERPRISE"] = {
        "assumptions": "difficulty 2.0 (T3/T4 blend), Claude Code harness (1.35x), 85% cache",
        "nightly_smoke_per_run": round(n_smoke, 0),
        "weekly_regression_per_run": round(n_week, 0),
        "release_gate_per_run": round(n_gate, 0),
        "nightly_x250": round(n_smoke * 250, 0),
        "weekly_x52": round(n_week * 52, 0),
        "gates_x8": round(n_gate * 8, 0),
        "TOTAL_ANNUAL": round(n_smoke * 250 + n_week * 52 + n_gate * 8, 0),
    }

    # --- G2. worst case: no caching, heavy harness, hard tasks, no seq stopping
    wc_gate, _ = sweep_cost(frontier6, 200, 5, difficulty=3.0, harness=2.2,
                            cache_hit=0.0)
    out["G2_worst_case"] = {
        "note": "no prompt caching, context-heavy internal harness, all T4 hard tasks",
        "single_release_gate": round(wc_gate, 0),
        "annual_8_gates": round(wc_gate * 8, 0),
    }

    # --- I. build-side costs (mining + oracle hardening), one repo ---
    # SWE-Factory: $0.024-0.045 per mined instance, 33-40% survive validation
    mined_needed = 200 / 0.35
    mining = mined_needed * 0.045
    # mutation hardening: ~60 mutants/task, each = 1 test-suite run (compute, not LLM)
    # plus ~15 LLM-generated semantic mutants per task on a cheap model
    llm_mutants = 200 * 15 * per_run_cost("GPT-5.4 mini", 12_000, 800, 0.85)
    mutant_compute = 200 * 60 * 0.004   # ~14s of a 4-vCPU container per suite run
    out["I_build_side_one_repo"] = {
        "candidates_to_mine_for_200_tasks": round(mined_needed, 0),
        "mining_llm_cost": round(mining, 2),
        "llm_semantic_mutants": round(llm_mutants, 2),
        "mutant_test_execution_compute": round(mutant_compute, 2),
        "TOTAL_BUILD": round(mining + llm_mutants + mutant_compute, 2),
    }

    # --- H. non-API infra, for contrast ---
    # 4 vCPU / 8GB container, ~5 min per trajectory, on-demand cloud ~ $0.20/vCPU-hr
    traj_min = 5
    infra_per_traj = 4 * 0.05 * (traj_min / 60)  # ~$0.017
    out["H_infra"] = {
        "per_trajectory_usd": round(infra_per_traj, 4),
        "S4_infra_total": round(infra_per_traj * 6000, 2),
        "S4_api_total": scen["S4 release gate (teardown spec)"]["total"],
        "infra_share_pct": round(
            100 * infra_per_traj * 6000 /
            scen["S4 release gate (teardown spec)"]["total"], 2),
    }

    print(json.dumps(out, indent=2))
    with open("/home/claude/benchme/results.json", "w") as f:
        json.dump(out, f, indent=2)
