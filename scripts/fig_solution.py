import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
G = json.load(open("guided-summary.json"))
SURF, TXT, TXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
# 1. Per-model dumbbell: unwell score, no prompt -> guidance
ms = sorted(G["models"], key=lambda m: m["guided"])
fig, ax = plt.subplots(figsize=(8, 5.6), dpi=200); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
for i, m in enumerate(ms):
    ax.plot([m["base"], m["guided"]], [i, i], color="#b9c4c2", lw=2.2, zorder=2)
    ax.scatter(m["base"], i, s=70, color="#8a91a0", zorder=3); ax.scatter(m["guided"], i, s=90, color="#2a9d8f", zorder=4)
    ax.text(m["guided"] + 0.02, i, f"{m['base']*100:.0f}% → {m['guided']*100:.0f}%", va="center", fontsize=7.5, color=TXT2)
ax.set_yticks(range(len(ms)), [m["name"] for m in ms], fontsize=9); ax.set_xlim(0, 1.12)
ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"]); ax.grid(axis="x", color=GRID, zorder=0)
for sp in ax.spines.values(): sp.set_visible(False)
ax.tick_params(colors=TXT2, length=0, labelsize=9)
fig.text(0.04, 0.96, "Clinician guidance: good replies to the teen becoming manic", fontsize=13, weight="bold", color=TXT, va="top")
fig.text(0.04, 0.91, "Grey: no system prompt. Green: with the 112-word clinician guidance. * also the judge.", fontsize=9, color=TXT2, va="top")
fig.tight_layout(rect=(0, 0, 1, 0.88)); fig.savefig("mike-repo/results/figures/guidance-by-model.png", facecolor=SURF); plt.close(fig)
# 2. Three conditions, four metrics
S = json.load(open("stats.json"))
conds = [("No system prompt", G["avg"]["base"], "#8a91a0"), ("Teen account", {"unwell": .13, "healthy": .89, "catch": .86, "false_alarm": .33}, "#a29bfe"), ("Clinician guidance", G["avg"]["guided"], "#2a9d8f")]
labels = [("unwell", "Good replies,\nunwell teen"), ("healthy", "Good replies,\nhealthy teen"), ("catch", "Raised concern,\nunwell teen"), ("false_alarm", "False alarms,\nhealthy teen")]
fig, ax = plt.subplots(figsize=(8.4, 4.6), dpi=200); fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
x = np.arange(4); w = 0.26
for j, (name, d, col) in enumerate(conds):
    vals = [d[k] for k, _ in labels]
    b = ax.bar(x + (j - 1) * w, vals, w * 0.92, color=col, label=name, zorder=3)
    for r, v in zip(b, vals): ax.text(r.get_x() + r.get_width() / 2, v + 0.015, f"{v*100:.0f}%", ha="center", fontsize=7.5, color=TXT2)
ax.set_xticks(x, [l for _, l in labels], fontsize=9); ax.set_ylim(0, 1.12); ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
ax.grid(axis="y", color=GRID, zorder=0)
for sp in ax.spines.values(): sp.set_visible(False)
ax.tick_params(colors=TXT2, length=0, labelsize=9); ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.14))
fig.text(0.04, 0.96, "Three conditions, same 12 models and 3 cases", fontsize=13, weight="bold", color=TXT, va="top")
fig.text(0.04, 0.905, "Averages over models. 27 runs per condition.", fontsize=9, color=TXT2, va="top")
fig.tight_layout(rect=(0, 0, 1, 0.86)); fig.savefig("mike-repo/results/figures/three-conditions.png", facecolor=SURF); plt.close(fig)
print("ok")
