import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
S = json.load(open("results/figures/stats.json")); out = "results/figures/"
SURF, TXT, TXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
UNW, HEA, TEEN = "#d9822b", "#2a9d8f", "#6c5ce7"
CASES = [("cvgff5hp6", "Case 1\nHypomania"), ("cimly1de6", "Case 2\nMania"), ("cq91ggr91", "Case 3\nMania + psychosis")]
def style(ax, fig, title, sub):
    fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(colors=TXT2, length=0, labelsize=9); ax.grid(axis="x" if ax.get_xlim() else "y", color=GRID, zorder=0)
    fig.text(0.04, 0.96, title, fontsize=13, weight="bold", color=TXT, va="top")
    fig.text(0.04, 0.905, sub, fontsize=9, color=TXT2, va="top")
pct = lambda v: f"{v*100:.0f}%"

# 1. By case: healthy vs unwell, both conditions
fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
import numpy as np
x = np.arange(3); w = 0.2
bars = [("base","healthy",HEA,"Healthy teen",1.0), ("base","unwell",UNW,"Teen becoming manic",1.0),
        ("teen","healthy",HEA,"Healthy teen (teen account)",0.45), ("teen","unwell",UNW,"Teen becoming manic (teen account)",0.45)]
for i,(cond,side,col,lab,a) in enumerate(bars):
    vals = [S[cond]["by_case"][c][side] for c,_ in CASES]
    b = ax.bar(x + (i-1.5)*w, vals, w*0.92, color=col, alpha=a, label=lab, zorder=3)
    for r,v in zip(b, vals): ax.text(r.get_x()+r.get_width()/2, v+0.015, pct(v), ha="center", fontsize=7.5, color=TXT2)
ax.set_xticks(x, [n for _,n in CASES]); ax.set_ylim(0,1.12); ax.set_yticks([0,.25,.5,.75,1],["0%","25%","50%","75%","100%"])
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5,-0.12))
style(ax, fig, "Good replies by case, averaged over 12 models", "Solid: no system prompt. Faded: simulated teen account. Every model scored 0% with the case 1 teen becoming manic.")
ax.grid(axis="y", color=GRID, zorder=0); ax.grid(axis="x", visible=False)
fig.tight_layout(rect=(0,0,1,0.86)); fig.savefig(out+"by-case.png", facecolor=SURF); plt.close(fig)

# 2. Heatmap: model x case, unwell score (baseline)
bm = S["base"]["by_model_case"]
models = sorted(bm, key=lambda m: -sum(bm[m][c]["unwell"] for c,_ in CASES))
M = np.array([[bm[m][c]["unwell"] for c,_ in CASES] for m in models])
fig, ax = plt.subplots(figsize=(7, 6.2), dpi=200)
im = ax.imshow(M, cmap="Oranges", vmin=0, vmax=1, aspect="auto")
for i in range(len(models)):
    for j in range(3): ax.text(j, i, pct(M[i,j]), ha="center", va="center", fontsize=8.5, color="white" if M[i,j] > 0.55 else TXT)
ax.set_xticks(range(3), [n.replace("\n"," · ") for _,n in CASES], fontsize=8.5); ax.set_yticks(range(len(models)), models, fontsize=9)
style(ax, fig, "Good replies to the teen becoming manic", "Per model and case, no system prompt. Two runs per model (GPT-6 Luna: 5).")
ax.grid(False); fig.tight_layout(rect=(0,0,1,0.88)); fig.savefig(out+"heatmap-unwell.png", facecolor=SURF); plt.close(fig)

# 3. Red flags (unwell), baseline vs teen account
LAB = {"ignores_late_night":"Ignores that it's late at night","not_slowing_down":"Doesn't slow down","missed_check_in":"Never checks in on the teen",
       "missing_resources":"No parent, clinician or 988","reinforces_delusion_or_grandiosity":"Reinforces the belief","encourages_unsafe_behavior":"Encourages unsafe behavior",
       "reinforces_manic_state":"Mirrors the high","boundary_collapse":"Drops its limits after pushback","diagnoses_or_labels":"Diagnoses or labels",
       "fosters_parasocial":"Acts as the teen's friend","promises_secrecy":"Promises secrecy","medication_advice":"Medication advice"}
keys = sorted(LAB, key=lambda k: S["base"]["flags"][k]["unwell"])
fig, ax = plt.subplots(figsize=(8, 5.4), dpi=200)
y = np.arange(len(keys))
ax.barh(y+0.2, [S["base"]["flags"][k]["unwell"] for k in keys], 0.38, color=UNW, label="No system prompt", zorder=3)
ax.barh(y-0.2, [S["teen"]["flags"][k]["unwell"] for k in keys], 0.38, color=UNW, alpha=0.45, label="Teen account", zorder=3)
for i,k in enumerate(keys): ax.text(S["base"]["flags"][k]["unwell"]+0.01, i+0.2, pct(S["base"]["flags"][k]["unwell"]), va="center", fontsize=7.5, color=TXT2)
ax.set_yticks(y, [LAB[k] for k in keys], fontsize=9); ax.set_xlim(0,0.8); ax.set_xticks([0,.2,.4,.6,.8],["0%","20%","40%","60%","80%"])
ax.legend(frameon=False, fontsize=8, loc="lower right")
style(ax, fig, "Red flags in replies to the teen becoming manic", "Share of replies that raised each flag, averaged over 12 models.")
ax.grid(axis="x", color=GRID, zorder=0); ax.grid(axis="y", visible=False)
fig.tight_layout(rect=(0,0,1,0.88)); fig.savefig(out+"red-flags.png", facecolor=SURF); plt.close(fig)
print("figures written")
