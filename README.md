# Sustainable Reverse Logistics MILP for EV Batteries

> Code repository for the paper:  
> **"Optimization model for sustainable reverse logistics of electric vehicle batteries"**  
> A. Neri, M. A. Butturi, B. Rimini, R. Gamberini  
> En&Tech Interdepartmental Centre / DISMI – University of Modena and Reggio Emilia

---

## Overview

This repository contains a **Mixed-Integer Linear Programming (MILP)** model for the optimal design of a sustainable reverse logistics network for end-of-life (EOL) lithium-ion EV batteries.

The model minimises a single objective that combines:
- battery acquisition costs
- fixed facility opening costs
- processing costs (collection, recycling, remanufacturing, disposal)
- transport costs, differentiated by vehicle type (diesel / hydrogen green)
- a carbon tax penalty on CO₂ emissions
- quality-differentiated government incentives (favoring remanufacturing over recycling and disposal)

**Three key innovations** with respect to prior literature:
1. Explicit green (hydrogen-fuelled) transport mode alongside diesel, with a minimum green-share constraint.
2. State-sponsored quality-differentiated incentives as decision variables (L1 remanufacturing > L2 recycling > L3 disposal).
3. Direct incorporation of a carbon tax within the objective function.

---

## Network structure

```
Collection centres (I)   →   Recycling/Remanufacturing centres (J)
                         ↘   Disposal centre (K)
                              ↑
Recycling/Remanufacturing (J) → Disposal centre (K)   [residual waste]
```

**Case study — Emilia-Romagna, Italy:**
| Tier | Nodes |
|------|-------|
| Collection | Parma (PR), Reggio Emilia (RE), Forlì (FC), Piacenza (PC) |
| Recycling / Remanufacturing | Imola (IM), Modena (MO) |
| Disposal | Ferrara (FE) |

---

## Repository structure

```
.
├── reverse_logistics_milp.py   # MILP model (build, solve, extract results)
├── parameters.dat              # All numerical parameters (commented)
├── visualize_results.py        # Figures: facility status, cost breakdown, flows
├── sensitivity_analysis.py     # Sensitivity analysis + tornado chart
├── figure/                     # Output PDFs (created at runtime)
└── requirements.txt
```

---

## Installation

Python ≥ 3.9 is required.

```bash
pip install -r requirements.txt
```

The solver used is **CBC** (bundled with PuLP, no extra installation needed).

---

## Usage

### Run the base model

```bash
python reverse_logistics_milp.py
```

Prints the optimal objective value, cost components, open facilities, and main cell flows.

### Generate figures

```bash
python visualize_results.py
```

Saves the following PDFs to `figure/`:
| File | Content |
|------|---------|
| `01_facility_status.pdf` | Open/closed status of candidate facilities |
| `02_cost_breakdown.pdf` | Stacked objective components |
| `03_cell_flows.pdf` | L1/L2 cell flows (diesel vs green) per arc |
| `04_disposal_flows.pdf` | L3 cells and residual waste to disposal |
| `05_transport_mix.pdf` | Overall diesel/green transport split |

### Run sensitivity analysis

```bash
python sensitivity_analysis.py
```

Saves to `figure/`:
| File | Content |
|------|---------|
| `06_sensitivity_comparison.pdf` | % change in objective vs % change in each parameter |
| `07_tornado.pdf` | Tornado chart — parameter impact ranking |

Sensitivity is performed by fixing the baseline optimal network and flows, then re-evaluating the objective at varied parameter values (green transport cost, remanufacturing processing cost, carbon tax, remanufacturing incentive).

---

## Model parameters

All parameters are documented in [`parameters.dat`](parameters.dat). Key values for the Emilia-Romagna case study:

| Parameter | Value | Source |
|-----------|-------|--------|
| Cells per battery (`bc`) | 96 | — |
| Cell grades (L1/L2/L3) | 75% / 22% / 3% | Pagliaro & Meneguzzo (2019) |
| Diesel transport cost | €0.075/cell·km | Wang et al. (2020), converted |
| Green transport cost | €0.105/cell·km | +40% over diesel (McKinsey 2024) |
| Carbon tax | €0.09968/kg CO₂ | OECD (2024) |
| L1 remanufacturing incentive | €25/cell | Policy hierarchy assumption |
| L2 recycling incentive | €10.75/cell | Market data (AMS 2020) |
| Min. green transport share | 30% | Model constraint |

---

## Results summary

**Baseline optimal solution:**
- Total cost: **€12,285,418**
- All four collection centres open
- Single recycling/remanufacturing centre selected: **Modena (MO)**
- Disposal centre: **Ferrara (FE)**
- Hybrid transport mix: green vehicles on shorter/higher-volume arcs (PR→MO, RE→MO), diesel on longer arcs

**Sensitivity ranking (impact over tested range):**
1. Remanufacturing processing cost — Δ ≈ €2.07 M (dominant)
2. Remanufacturing incentive — Δ ≈ €1.78 M
3. Green transport cost — Δ ≈ €262 K
4. Carbon tax — Δ ≈ €262 K

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `pulp` | LP/MILP modelling and CBC solver interface |
| `matplotlib` | Figure generation |
| `numpy` | Array operations in visualisation |

---

## Citation

If you use this code, please cite:

```
Neri, A., Butturi, M. A., Rimini, B., & Gamberini, R. (2026).
Optimization model for sustainable reverse logistics of electric vehicle batteries.
[Conference proceedings / journal — forthcoming]
```

---

## Funding

This research is co-funded by the **ERDF – ROP of Emilia-Romagna (Italy)** under project **SACER** (CUP J47G22000760003, POR-FESR 2021/2027), and by the **Institute of Advanced Studies** through the ISA Doctoral Prize.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
