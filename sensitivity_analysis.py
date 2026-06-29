import os
import logging
import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt

from reverse_logistics_milp import load_params, build_model, solve, extract_solution, evaluate_objective

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figure")

FIG_W = 3.35  # inches (~8.5 cm), half-column A4
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

# Plain descriptive names: no model-notation symbols on the figures.
SCENARIOS = [
    dict(key="CT_green", name="Green transport cost", color="#2E7D32",
         direction=-1, fractions=[0, 0.10, 0.20, 0.30, 0.40, 0.50]),
    dict(key="pcmj", name="Remanufacturing cost", color="#C62828",
         direction=-1, fractions=[0, 0.05, 0.10, 0.15, 0.20, 0.25]),
    dict(key="carbon_tax_per_kg", name="Carbon tax", color="#1565C0",
         direction=+1, fractions=[0, 0.10, 0.20, 0.30, 0.40, 0.50]),
    dict(key="s_L1", name="Remanufacturing incentive", color="#6A1B9A",
         direction=+1, fractions=[0, 0.10, 0.20, 0.30, 0.40, 0.50]),
]


def run_scenario(P_base, scenario, baseline_sol, sets, baseline_obj):
    baseline_value = P_base[scenario["key"]]
    points = []
    for frac in scenario["fractions"]:
        param_pct = scenario["direction"] * frac * 100
        param_value = baseline_value * (1 + scenario["direction"] * frac)
        P = dict(P_base)
        P[scenario["key"]] = param_value
        obj = evaluate_objective(P, baseline_sol, sets)
        obj_pct = (obj - baseline_obj) / baseline_obj * 100
        points.append((param_pct, obj, obj_pct))
    return points


def fig_comparison(results):
    """Single chart: % change in each parameter (x) vs resulting %
    change in the objective function (y), all on the same scale so the
    four slopes are directly comparable."""
    fig, ax = plt.subplots(figsize=(FIG_W, 3.1))
    for scenario, points in results:
        xs = [p[0] for p in points]
        ys = [p[2] for p in points]
        ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.4,
                color=scenario["color"], label=scenario["name"])

    ax.axhline(0, color="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Parameter change from baseline (%)")
    ax.set_ylabel("Objective change from baseline (%)")
    ax.set_title("Sensitivity comparison\n(flows fixed at baseline optimum)")
    ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "06_sensitivity_comparison.pdf")
    os.makedirs(OUT_DIR, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("Saved:", path)


def fig_tornado(results):
    """Horizontal bar chart of each parameter's impact (delta) over its
    full tested range, sorted descending."""
    names, delta, colors = [], [], []
    for scenario, points in results:
        ys = [p[1] for p in points]
        names.append(scenario["name"].replace(" ", "\n", 1))
        delta.append(max(ys) - min(ys))
        colors.append(scenario["color"])

    order = sorted(range(len(names)), key=lambda k: delta[k], reverse=True)
    names = [names[k] for k in order]
    delta = [delta[k] for k in order]
    colors = [colors[k] for k in order]

    fig, ax = plt.subplots(figsize=(FIG_W, 2.6))
    bars = ax.barh(names, delta, color=colors)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.28 * max(delta))
    ax.xaxis.set_major_locator(plt.MaxNLocator(4))
    ax.xaxis.set_major_formatter(lambda v, _: f"{v/1e6:,.1f}M")
    ax.set_xlabel("Objective change (EUR) over tested range")
    ax.set_title("Parameter impact ranking")
    for b, v in zip(bars, delta):
        ax.text(v + 0.02 * max(delta), b.get_y() + b.get_height() / 2,
                f"{v/1e6:,.2f}M", va="center", fontsize=6.5)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "07_tornado.pdf")
    fig.savefig(path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("Saved:", path)


def main():
    P_base = load_params()

    # Solve once: a real MILP solve, giving the baseline-optimal
    # network/flow allocation that every scenario below holds fixed.
    m0, variables0, sets, costs0 = build_model(P_base)
    status0 = solve(m0)
    baseline_obj = m0.objective.value()
    baseline_sol = extract_solution(variables0, sets)
    print(f"Baseline: status={status0}, objective = EUR {baseline_obj:,.2f}")

    check = evaluate_objective(P_base, baseline_sol, sets)
    print(f"Formula check (should match): EUR {check:,.2f}\n")

    results = []
    for scenario in SCENARIOS:
        print(f"Scenario: {scenario['name']} ({scenario['key']})")
        points = run_scenario(P_base, scenario, baseline_sol, sets, baseline_obj)
        for pct, obj, obj_pct in points:
            print(f"  {pct:+6.1f}%  ->  F = EUR {obj:,.2f}  ({obj_pct:+.2f}%)")
        results.append((scenario, points))
        print()

    fig_comparison(results)
    fig_tornado(results)


if __name__ == "__main__":
    main()
