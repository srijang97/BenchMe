import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

d = json.load(open("/home/claude/benchme/results.json"))

INK = "#1c1c1a"; MUTED = "#6b6a66"; GRID = "#e4e2dd"; BG = "#ffffff"
C = {"frontier": "#3b6ea5", "open": "#2f8f6f", "cheap": "#b07d3a"}
ACCENT = "#a8452f"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG,
    "font.family": "DejaVu Sans", "font.size": 10.5,
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "axes.linewidth": 0.9,
})


def clean(ax, xgrid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRID); ax.spines["bottom"].set_color(GRID)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
        ax.yaxis.grid(False)
    else:
        ax.yaxis.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
        ax.xaxis.grid(False)


# ---------------- CHART 1 : cost per solved task by model ----------------
b = d["B_per_task_by_model"]
skip = {"Claude Sonnet 5 (Sep+)", "Kimi K2.7 Code", "GLM-5", "DeepSeek V4 Flash",
        "GPT-5.5", "Qwen3.7 Flash", "MiniMax M3", "Claude Mythos 5"}
rows = [(m, v) for m, v in b.items() if m not in skip]
rows.sort(key=lambda r: r[1]["per_solved"])

fig, ax = plt.subplots(figsize=(10.2, 6.4))
names = [r[0] for r in rows]
vals = [r[1]["per_solved"] for r in rows]
cols = [C[r[1]["tier"]] for r in rows]
bars = ax.barh(names, vals, color=cols, height=0.68)
for bar, v, r in zip(bars, vals, rows):
    ax.text(v + max(vals) * 0.012, bar.get_y() + bar.get_height() / 2,
            f"${v:,.2f}", va="center", ha="left", fontsize=10,
            color=INK, fontweight="600")
ax.set_xlim(0, max(vals) * 1.18)
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
clean(ax)
ax.set_xlabel("Cost per SOLVED task (USD)", color=MUTED, labelpad=9)
ax.set_title("Cost per solved task — medium difficulty, 85% cache hit",
             fontsize=14.5, fontweight="700", pad=36, loc="left")
ax.text(0, 1.012, "includes the cost of failed attempts; assumes weaker models "
        "burn more tokens and solve fewer tasks",
        transform=ax.transAxes, fontsize=10, color=MUTED, va="bottom")
handles = [plt.Rectangle((0, 0), 1, 1, color=C[k]) for k in ["frontier", "open", "cheap"]]
ax.legend(handles, ["Frontier (closed)", "Open weight", "Cheap tier"],
          frameon=False, loc="lower right", fontsize=10)
plt.tight_layout()
plt.savefig("/home/claude/benchme/chart1_per_task.png", dpi=190,
            bbox_inches="tight", facecolor=BG)
plt.close()

# ---------------- CHART 2 : cache sensitivity ----------------
f = d["F_cache_sensitivity"]
fig, ax = plt.subplots(figsize=(9.4, 5.2))
ks = list(f.keys()); vs = list(f.values())
cols = [ACCENT if "0%" == k.split()[0] else
        ("#3b6ea5" if k.startswith("85") else "#93a8bf") for k in ks]
bars = ax.bar(ks, vs, color=cols, width=0.62)
for bar, v in zip(bars, vs):
    ax.text(bar.get_x() + bar.get_width() / 2, v + max(vs) * 0.02,
            f"${v:,.0f}", ha="center", fontsize=10.5, fontweight="600", color=INK)
ax.set_ylim(0, max(vs) * 1.14)
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x/1000:,.0f}k"))
clean(ax, xgrid=False)
ax.set_ylabel("Total cost of one full sweep", color=MUTED, labelpad=9)
ax.set_title("Prompt caching is the single biggest cost lever",
             fontsize=14.5, fontweight="700", pad=36, loc="left")
ax.text(0, 1.012, "200 tasks x 6 configs x k=5  =  6,000 agent trajectories",
        transform=ax.transAxes, fontsize=10, color=MUTED, va="bottom")
ax.annotate("realistic for a\nwell-built harness", xy=(4, f["85% cache hit"]),
            xytext=(3.4, max(vs) * 0.62), fontsize=9.5, color="#3b6ea5",
            ha="center", fontweight="600",
            arrowprops=dict(arrowstyle="->", color="#3b6ea5", lw=1.2))
plt.tight_layout()
plt.savefig("/home/claude/benchme/chart2_cache.png", dpi=190,
            bbox_inches="tight", facecolor=BG)
plt.close()

# ---------------- CHART 3 : scenarios ----------------
s = d["E_scenarios"]
order = ["S1 nightly smoke", "S2 weekly regression (config change)",
         "S3 pilot bake-off (realistic)", "S6 cheap-model screen",
         "S4b release gate + sequential stopping", "S5 hard-task gate (enterprise monorepo)",
         "S4 release gate (teardown spec)"]
labels = ["Nightly smoke\n20 tasks x 1 cfg x k=1",
          "Weekly config A/B\n60 x 2 x k=3",
          "Pilot bake-off\n30 x 4 x k=5",
          "Cheap-model screen\n200 x 4 x k=5",
          "Release gate + early stop\n200 x 6 x k=5",
          "Hard-task gate (monorepo)\n100 x 4 x k=5, T4",
          "Full release gate\n200 x 6 x k=5"]
vals = [s[k]["total"] for k in order]

fig, ax = plt.subplots(figsize=(10.2, 5.8))
cols = ["#2f8f6f", "#2f8f6f", "#3b6ea5", "#3b6ea5", "#3b6ea5", "#b07d3a", "#b07d3a"]
bars = ax.barh(labels, vals, color=cols, height=0.66)
for bar, v in zip(bars, vals):
    ax.text(v + max(vals) * 0.012, bar.get_y() + bar.get_height() / 2,
            f"${v:,.0f}", va="center", fontsize=10.5, fontweight="600", color=INK)
ax.invert_yaxis()
ax.set_xlim(0, max(vals) * 1.16)
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"${x:,.0f}"))
clean(ax)
ax.set_xlabel("API cost per run (USD)", color=MUTED, labelpad=9)
ax.set_title("What one evaluation run actually costs",
             fontsize=14.5, fontweight="700", pad=36, loc="left")
ax.text(0, 1.012, "medium-difficulty tasks, 85% cache hit, failures costed in",
        transform=ax.transAxes, fontsize=10, color=MUTED, va="bottom")
plt.tight_layout()
plt.savefig("/home/claude/benchme/chart3_scenarios.png", dpi=190,
            bbox_inches="tight", facecolor=BG)
plt.close()

print("charts written")
