# Reverse Logistics MILP for End-of-Life EV Batteries

A Mixed-Integer Linear Programming (MILP) model for designing sustainable reverse logistics networks for end-of-life lithium-ion EV batteries. The model minimises a single monetised objective covering operational costs, transport emissions (via carbon tax), and quality-differentiated government incentives.

---

## Model overview

The network spans three tiers of facilities:

```
Collection centres (I)  ──L2──►  Recycling/Remanufacturing centres (J)
                         ──L1──►  Remanufacturing centres (J)
                         ──L3──►  Disposal centres (K)

Recycling/Remanufacturing (J)  ──residual waste──►  Disposal centres (K)
```

Batteries collected at tier *I* are disassembled into cells and classified by state-of-health into three grades:

| Grade | SOH | Destination |
|-------|-----|-------------|
| L1 | > 80% | Remanufacturing |
| L2 | 60–80% | Recycling |
| L3 | ≤ 60% | Disposal |

Each arc carries **two transport modes** — diesel and green (e.g. hydrogen) — subject to a minimum green-share constraint across the network.

The objective function aggregates:
- battery acquisition costs
- fixed facility opening costs
- processing costs per cell (collection, recycling, remanufacturing, disposal)
- transport costs by mode and arc
- a carbon tax on CO₂ emissions (processing + transport)
- quality-differentiated incentives (L1 > L2 > L3), subtracted

---

## Repository structure

```
.
├── reverse_logistics_milp.py   # model definition, solver, result extraction
├── parameters.dat              # all input parameters (edit this to adapt the model)
├── visualize_results.py        # generates publication-ready figures
├── sensitivity_analysis.py     # one-at-a-time sensitivity + tornado chart
├── figure/                     # output folder (created at runtime)
└── requirements.txt
```

---

## Installation

Python ≥ 3.9 required. The solver (CBC) is bundled with PuLP — no separate installation needed.

```bash
pip install -r requirements.txt
```

---

## Usage

### Solve the model

```bash
python reverse_logistics_milp.py
```

Prints the optimal objective value, cost components, open/closed facility status, and main cell flows.

### Generate figures

```bash
python visualize_results.py
```

Saves PDFs to `figure/`:

| File | Content |
|------|---------|
| `01_facility_status.pdf` | Open/closed status of candidate facilities |
| `02_cost_breakdown.pdf` | Objective components (stacked bar) |
| `03_cell_flows.pdf` | L1/L2 flows per arc, diesel vs green |
| `04_disposal_flows.pdf` | L3 cells and residual waste to disposal |
| `05_transport_mix.pdf` | Overall diesel/green transport split |

### Run sensitivity analysis

```bash
python sensitivity_analysis.py
```

Saves to `figure/`:

| File | Content |
|------|---------|
| `06_sensitivity_comparison.pdf` | % objective change vs % parameter change |
| `07_tornado.pdf` | Parameter impact ranking |

Sensitivity is computed by fixing the baseline-optimal network and flows, then re-evaluating the objective at varied parameter values — avoiding solver re-runs and their numerical tolerances.

---

## Adapting the model to a different network

All numerical inputs live in **`parameters.dat`** — a plain text file with one `key = value` per line and inline comments. You do not need to touch the Python code to run a different scenario.

### What to change

**Demand** — batteries collected per centre per year:
```
QBi_Parma    = 575
QBi_Reggio   = 420
...
```
Add or remove entries to change the number of collection centres, then update `I_SET` in `reverse_logistics_milp.py`.

**Distances** — Euclidean or road distances in km between facility pairs:
```
D_Parma_Imola    = 138
D_Parma_Modena   = 61
...
```
One entry per candidate arc (I→J), (I→K) and (J→K).

**Facility capacities** (ton/year):
```
I  = 750     # collection centre
J  = 3000    # recycling/remanufacturing centre
K  = 125     # disposal centre
```

**Cell quality mix** — fraction of cells in each grade:
```
alpha1 = 0.75   # L1 (remanufacturing)
alpha2 = 0.22   # L2 (recycling)
alpha3 = 0.03   # L3 (disposal)
```

**Transport costs and emissions**:
```
CT_diesel  = 0.075    # EUR / cell·km
CT_green   = 0.105    # EUR / cell·km
te_diesel  = 0.834    # kg CO2 / km·container
te_green   = 0        # zero tailpipe CO2
perc_hydro = 0.30     # minimum green share (0–1)
```

**Carbon tax**:
```
carbon_tax_per_kg = 0.09968   # EUR / kg CO2
```

**Incentives** (EUR/cell) — set to 0 to disable:
```
s_L1 = 25      # remanufacturing
s_L2 = 10.75   # recycling
s_L3 = 0       # disposal
```

**Fixed and processing costs**:
```
FC_Parma = 76125    # EUR/year, collection centre
FC_j     = 721240   # EUR/year, recycling/remanufacturing centre
FC_k     = 1000000  # EUR/year, disposal centre

pcci = 7.7    # EUR/cell, collection processing
pcrj = 19     # EUR/cell, recycling
pcmj = 58     # EUR/cell, remanufacturing
pcwk = 0.075  # EUR/cell, disposal
```

### Adding or removing facilities

To change the candidate facility sets, edit the three lists at the top of `reverse_logistics_milp.py`:

```python
I_SET = ["Parma", "Reggio", "Forli", "Piacenza"]   # collection centres
J_SET = ["Imola", "Modena"]                          # recycling/remanufacturing
K_SET = ["Ferrara"]                                  # disposal
```

Then add the corresponding parameter entries in `parameters.dat` (demand `QBi_*`, fixed cost `FC_*`, distances `D_*`).

---

## Citation

This model is associated with a paper currently under review. If you use this code, please check the repository for an updated citation or contact the authors directly.

> Neri, A., Butturi, M. A., Rimini, B., & Gamberini, R.  
> *Optimization model for sustainable reverse logistics of electric vehicle batteries.*  
> (under review)

---

## License

This code is released under a **Creative Commons Attribution 4.0 International (CC BY 4.0)** license.

You are free to use, adapt, and redistribute this code for any purpose, including commercially, **provided that you give appropriate credit** to the original authors and cite the associated paper.

Full license text: <https://creativecommons.org/licenses/by/4.0/>
