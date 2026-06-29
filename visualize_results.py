import os
import logging
import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt
import numpy as np

from reverse_logistics_milp import load_params, build_model, solve, extract_solution, cost_value

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figure")

# --- layout: half-column A4 (~8.5 cm wide) ---
FIG_W = 3.35  # inches (~8.5 cm)
plt.rcParams.update({
    "font.family": ["EB Garamond", "Times New Roman", "Liberation Serif", "serif"],
    "font.size": 7.5,
    "axes.titlesize": 8.5,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.5,
    "axes.linewidth": 0.6,
})

GREEN = "#2E7D32"
DIESEL = "#616161"
RED = "#C62828"

# Italian province vehicle codes (Imola has none officially; IM used here
# for brevity, consistent with the other cities).
CITY = {"Parma": "PR", "Reggio": "RE", "Forli": "FC", "Piacenza": "PC",
        "Imola": "IM", "Modena": "MO", "Ferrara": "FE"}


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("Saved:", path)


def fig_facility_status(sol, sets):
    nodes = [(f"Coll.\n{CITY[i]}", sol["x"][i]) for i in sets["I"]] \
        + [(f"Recyc.\n{CITY[j]}", sol["y"][j]) for j in sets["J"]] \
        + [(f"Disp.\n{CITY[k]}", sol["z"][k]) for k in sets["K"]]
    names = [n for n, _ in nodes]
    values = [v for _, v in nodes]
    colors = [GREEN if v > 0.5 else "#BDBDBD" for v in values]

    fig, ax = plt.subplots(figsize=(FIG_W, 1.9))
    ax.bar(names, [1] * len(names), color=colors, edgecolor="white", linewidth=0.5)
    for i, v in enumerate(values):
        ax.text(i, 0.5, "open" if v > 0.5 else "closed", ha="center", va="center",
                color="white" if v > 0.5 else "#616161", fontweight="bold", fontsize=6.5)
    ax.set_yticks([])
    ax.set_title("Candidate facility status")
    fig.tight_layout()
    _save(fig, "01_facility_status.pdf")


def fig_cost_breakdown(costs, obj_value):
    names = ["Acquisition", "Fixed", "Processing", "Transport", "CO2", "Incentives"]
    values = [cost_value(costs["f_AC"]), cost_value(costs["f_FC"]), cost_value(costs["f_PC"]),
              cost_value(costs["f_TC"]), cost_value(costs["f_co2"]), -cost_value(costs["f_inc"])]
    colors = [GREEN if v >= 0 else RED for v in values]

    fig, ax = plt.subplots(figsize=(FIG_W, 2.6))
    bars = ax.bar(names, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_ylabel("EUR")
    ax.set_title(f"Objective breakdown (total: {obj_value/1e6:,.2f} M EUR)")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    span = max(values) - min(values)
    ax.set_ylim(min(values) - 0.16 * span, max(values) + 0.16 * span)
    for b, v in zip(bars, values):
        offset = 0.02 * span
        ax.text(b.get_x() + b.get_width() / 2, v + (offset if v >= 0 else -offset),
                f"{v/1e6:,.2f}M", ha="center", va="bottom" if v >= 0 else "top", fontsize=6)
    fig.tight_layout()
    _save(fig, "02_cost_breakdown.pdf")


def fig_cell_flows(sol, sets):
    arcs = [a for a in sets["D_ij"] if sum(sol["R"][a]) + sum(sol["M"][a]) > 1e-6]
    arcs.sort()
    labels = [f"{CITY[i]}\u2192{CITY[j]}" for i, j in arcs]
    Rd = np.array([sol["R"][a][0] for a in arcs])
    Rg = np.array([sol["R"][a][1] for a in arcs])
    Md = np.array([sol["M"][a][0] for a in arcs])
    Mg = np.array([sol["M"][a][1] for a in arcs])

    x = np.arange(len(arcs))
    w = 0.35
    fig, ax = plt.subplots(figsize=(FIG_W, 2.9))
    ax.bar(x - w / 2, Rd, w, color=DIESEL, label="Recycling, diesel")
    ax.bar(x - w / 2, Rg, w, bottom=Rd, color=GREEN, label="Recycling, green")
    ax.bar(x + w / 2, Md, w, color=DIESEL, alpha=0.6, hatch="//", label="Remanufacturing, diesel")
    ax.bar(x + w / 2, Mg, w, bottom=Md, color=GREEN, alpha=0.6, hatch="//", label="Remanufacturing, green")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Cells / year")
    ax.set_ylim(0, 1.15 * max((Rd + Rg).max(), (Md + Mg).max()))
    ax.set_title("Cell flows to recycling/remanufacturing")
    ax.legend(fontsize=6, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False)
    fig.tight_layout()
    _save(fig, "03_cell_flows.pdf")


def fig_disposal_flows(sol, sets):
    fig, axes = plt.subplots(2, 1, figsize=(FIG_W, 3.8))

    centres_w = [i for i in sets["I"] if sum(sol["W"][i]) > 1e-6]
    Wd = np.array([sol["W"][i][0] for i in centres_w])
    Wg = np.array([sol["W"][i][1] for i in centres_w])
    x = np.arange(len(centres_w))
    b1 = axes[0].bar(x, Wd, color=DIESEL)
    b2 = axes[0].bar(x, Wg, bottom=Wd, color=GREEN)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([CITY[i] for i in centres_w])
    axes[0].set_ylabel("Cells / year")
    axes[0].set_ylim(0, 1.18 * (Wd + Wg).max())
    axes[0].set_title("L3 cells to disposal")

    centres_v = [j for j in sets["J"] if sum(sol["V"][j]) > 1e-6]
    Vd = np.array([sol["V"][j][0] for j in centres_v])
    Vg = np.array([sol["V"][j][1] for j in centres_v])
    x2 = np.arange(len(centres_v))
    axes[1].bar(x2, Vd, color=DIESEL)
    axes[1].bar(x2, Vg, bottom=Vd, color=GREEN)
    axes[1].set_xticks(x2)
    axes[1].set_xticklabels([CITY[j] for j in centres_v])
    axes[1].set_xlim(-1, 1)
    axes[1].set_ylabel("kg / year")
    axes[1].set_ylim(0, 1.18 * (Vd + Vg).max())
    axes[1].set_title("Residual waste to disposal")

    fig.legend([b1, b2], ["diesel", "green"], fontsize=6.5, ncol=2,
               loc="upper center", bbox_to_anchor=(0.5, 0.045), frameon=False)
    fig.tight_layout(rect=(0, 0.04, 1, 1), h_pad=2.2)
    _save(fig, "04_disposal_flows.pdf")


def fig_transport_mix(sol):
    tot_d = sum(sol["R"][a][0] for a in sol["R"]) + sum(sol["M"][a][0] for a in sol["M"]) \
        + sum(sol["W"][i][0] for i in sol["W"])
    tot_g = sum(sol["R"][a][1] for a in sol["R"]) + sum(sol["M"][a][1] for a in sol["M"]) \
        + sum(sol["W"][i][1] for i in sol["W"])

    fig, ax = plt.subplots(figsize=(FIG_W, 2.6))
    ax.pie([tot_d, tot_g], labels=[f"Diesel\n{tot_d:,.0f}", f"Green\n{tot_g:,.0f}"],
           colors=[DIESEL, GREEN], autopct="%1.0f%%", startangle=90,
           wedgeprops={"edgecolor": "white", "linewidth": 0.5},
           textprops={"fontsize": 7})
    ax.set_title("Transport mix (cells)")
    fig.tight_layout()
    _save(fig, "05_transport_mix.pdf")


def main():
    P = load_params()
    m, variables, sets, costs = build_model(P)
    status = solve(m)
    print("Status:", status)
    obj_value = m.objective.value()
    print(f"Objective: EUR {obj_value:,.2f}")

    sol = extract_solution(variables, sets)

    fig_facility_status(sol, sets)
    fig_cost_breakdown(costs, obj_value)
    fig_cell_flows(sol, sets)
    fig_disposal_flows(sol, sets)
    fig_transport_mix(sol)


if __name__ == "__main__":
    main()
