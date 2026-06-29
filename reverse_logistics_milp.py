import os
import pulp

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parameters.dat")

I_SET = ["Parma", "Reggio", "Forli", "Piacenza"]
J_SET = ["Imola", "Modena"]
K_SET = ["Ferrara"]


# ---------------------------------------------------------------------
# 1. DATA LOADING
# ---------------------------------------------------------------------

def load_params(path=DEFAULT_DATA_PATH):
    """Parse a 'key = value' text file into a {key: float} dict."""
    params = {}
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            params[key.strip()] = float(value.strip())
    return params


# ---------------------------------------------------------------------
# 2. MODEL
# ---------------------------------------------------------------------

def build_model(P, include_f_AC=True):
    I, J, K = I_SET, J_SET, K_SET

    QB = {"Parma": P["QBi_Parma"], "Reggio": P["QBi_Reggio"],
          "Forli": P["QBi_Forli"], "Piacenza": P["QBi_Piacenza"]}

    bc = P["bc"]
    wb = P["wb"]                       # cell weight (kg)
    battery_w = P["battery_weight_kg"]
    omega = P["omega"]
    phi = P["phi"]
    p_green = P["perc_hydro"]

    alpha = {1: P["alpha1"], 2: P["alpha2"], 3: P["alpha3"]}
    ru = {1: P["ru_L1"], 2: P["ru_L2"], 3: P["ru_L3"]}
    s_inc = {1: P["s_L1"], 2: P["s_L2"], 3: P["s_L3"]}

    FC_i = {"Parma": P["FC_Parma"], "Reggio": P["FC_Reggio"],
            "Forli": P["FC_Forli"], "Piacenza": P["FC_Piacenza"]}
    FC_j = {j: P["FC_j"] for j in J}
    FC_k = {k: P["FC_k"] for k in K}

    I_cap = {i: P["I"] for i in I}      # ton/year
    J_cap = {j: P["J"] for j in J}
    K_cap = {k: P["K"] for k in K}

    pcc, pcr, pcm, pcw = P["pcci"], P["pcrj"], P["pcmj"], P["pcwk"]
    CT_d, CT_g = P["CT_diesel"], P["CT_green"]
    ctax = P["carbon_tax_per_kg"]
    fec, fer, fem, few = P["feci"], P["ferj"], P["femj"], P["fewk"]
    te_d, te_g = P["te_diesel"], P["te_green"]

    D_ij = {("Parma", "Imola"): P["D_Parma_Imola"], ("Reggio", "Imola"): P["D_Reggio_Imola"],
            ("Forli", "Imola"): P["D_Forli_Imola"], ("Piacenza", "Imola"): P["D_Piacenza_Imola"],
            ("Parma", "Modena"): P["D_Parma_Modena"], ("Reggio", "Modena"): P["D_Reggio_Modena"],
            ("Forli", "Modena"): P["D_Forli_Modena"], ("Piacenza", "Modena"): P["D_Piacenza_Modena"]}
    D_ik = {"Parma": P["D_Parma_Ferrara"], "Reggio": P["D_Reggio_Ferrara"],
            "Forli": P["D_Forli_Ferrara"], "Piacenza": P["D_Piacenza_Ferrara"]}
    D_jk = {"Imola": P["D_Imola_Ferrara"], "Modena": P["D_Modena_Ferrara"]}

    m = pulp.LpProblem("EOL_EV_battery_reverse_logistics", pulp.LpMinimize)

    # --- decision variables ---
    x = pulp.LpVariable.dicts("x", I, cat="Binary")
    y = pulp.LpVariable.dicts("y", J, cat="Binary")
    z = pulp.LpVariable.dicts("z", K, cat="Binary")

    R_d = pulp.LpVariable.dicts("R_diesel", D_ij.keys(), lowBound=0)
    R_g = pulp.LpVariable.dicts("R_green", D_ij.keys(), lowBound=0)
    M_d = pulp.LpVariable.dicts("M_diesel", D_ij.keys(), lowBound=0)
    M_g = pulp.LpVariable.dicts("M_green", D_ij.keys(), lowBound=0)
    W_d = pulp.LpVariable.dicts("W_diesel", I, lowBound=0)
    W_g = pulp.LpVariable.dicts("W_green", I, lowBound=0)
    V_d = pulp.LpVariable.dicts("V_diesel", J, lowBound=0)
    V_g = pulp.LpVariable.dicts("V_green", J, lowBound=0)

    def R(i, j): return R_d[(i, j)] + R_g[(i, j)]
    def M(i, j): return M_d[(i, j)] + M_g[(i, j)]
    def W(i): return W_d[i] + W_g[i]
    def V(j): return V_d[j] + V_g[j]

    arcs_j = {i: [j for j in J if (i, j) in D_ij] for i in I}

    # --- cell mass balance, per collection centre i ---
    for i in I:
        m += bc * alpha[1] * QB[i] * x[i] == pulp.lpSum(M(i, j) for j in arcs_j[i])
        m += bc * alpha[2] * QB[i] * x[i] == pulp.lpSum(R(i, j) for j in arcs_j[i])
        m += bc * alpha[3] * QB[i] * x[i] == W(i)

    # --- residual waste from recycling/remanufacturing centres j ---
    for j in J:
        inbound = pulp.lpSum(R(i, j) + M(i, j) for i in I if (i, j) in D_ij)
        m += V(j) == phi * wb * inbound

    # --- capacity constraints (kg, converted from ton/year) ---
    for i in I:
        m += QB[i] * battery_w <= I_cap[i] * 1000 * x[i]
    for j in J:
        inbound = pulp.lpSum(R(i, j) + M(i, j) for i in I if (i, j) in D_ij)
        m += wb * inbound <= J_cap[j] * 1000 * y[j]
    for k in K:
        m += wb * pulp.lpSum(W(i) for i in I) + pulp.lpSum(V(j) for j in J) <= K_cap[k] * 1000 * z[k]

    # --- minimum green transport share, per flow type ---
    m += pulp.lpSum(R_g[a] for a in D_ij) >= p_green * pulp.lpSum(R(i, j) for (i, j) in D_ij)
    m += pulp.lpSum(M_g[a] for a in D_ij) >= p_green * pulp.lpSum(M(i, j) for (i, j) in D_ij)
    m += pulp.lpSum(W_g[i] for i in I) >= p_green * pulp.lpSum(W(i) for i in I)
    m += pulp.lpSum(V_g[j] for j in J) >= p_green * pulp.lpSum(V(j) for j in J)

    # --- objective function ---
    total_cells_collected = pulp.lpSum(QB[i] * bc * x[i] for i in I)
    R_tot = pulp.lpSum(R(i, j) for (i, j) in D_ij)
    M_tot = pulp.lpSum(M(i, j) for (i, j) in D_ij)
    W_tot = pulp.lpSum(W(i) for i in I)

    f_AC = pulp.lpSum(x[i] * QB[i] for i in I) * sum(ru[u] * alpha[u] for u in (1, 2, 3))
    if not include_f_AC:
        f_AC = 0
    f_FC = pulp.lpSum(x[i] * FC_i[i] for i in I) + pulp.lpSum(y[j] * FC_j[j] for j in J) \
        + pulp.lpSum(z[k] * FC_k[k] for k in K)
    f_PC = pcc * total_cells_collected + pcr * R_tot + pcm * M_tot + pcw * W_tot

    f_TC = pulp.lpSum(D_ij[(i, j)] * (CT_d * R_d[(i, j)] + CT_g * R_g[(i, j)]
                                       + CT_d * M_d[(i, j)] + CT_g * M_g[(i, j)]) for (i, j) in D_ij) \
        + pulp.lpSum(D_ik[i] * (CT_d * W_d[i] + CT_g * W_g[i]) for i in I) \
        + pulp.lpSum(D_jk[j] * (CT_d * V_d[j] + CT_g * V_g[j]) for j in J)

    f_FEC_raw = fec * total_cells_collected + fer * R_tot + fem * M_tot + few * W_tot
    f_TEC_raw = pulp.lpSum(D_ij[(i, j)] * (te_d * R_d[(i, j)] + te_g * R_g[(i, j)]
                                            + te_d * M_d[(i, j)] + te_g * M_g[(i, j)]) / omega
                            for (i, j) in D_ij) \
        + pulp.lpSum(D_ik[i] * (te_d * W_d[i] + te_g * W_g[i]) / omega for i in I) \
        + pulp.lpSum(D_jk[j] * (te_d * V_d[j] + te_g * V_g[j]) / omega for j in J)
    f_co2 = ctax * (f_FEC_raw + f_TEC_raw)

    f_inc = s_inc[1] * M_tot + s_inc[2] * R_tot + s_inc[3] * W_tot

    m += f_AC + f_FC + f_PC + f_TC + f_co2 - f_inc

    variables = dict(x=x, y=y, z=z, R_d=R_d, R_g=R_g, M_d=M_d, M_g=M_g,
                      W_d=W_d, W_g=W_g, V_d=V_d, V_g=V_g)
    sets = dict(I=I, J=J, K=K, D_ij=D_ij, D_ik=D_ik, D_jk=D_jk)
    costs = dict(f_AC=f_AC, f_FC=f_FC, f_PC=f_PC, f_TC=f_TC, f_co2=f_co2, f_inc=f_inc)
    return m, variables, sets, costs


# ---------------------------------------------------------------------
# 3. SOLVE
# ---------------------------------------------------------------------

def solve(m):
    m.solve(pulp.PULP_CBC_CMD(msg=False))
    return pulp.LpStatus[m.status]


def evaluate_objective(P, sol, sets, include_f_AC=True):
    """Evaluate the objective at a FIXED solution (no solving) for a given
    parameter set P. Mirrors build_model()'s cost formula exactly, just
    using plain numbers from sol instead of pulp variables. This is what
    a "vary one parameter, keep the network/flows fixed" sensitivity
    analysis needs: re-solving a degenerate LP with every flow pinned by
    equality runs into floating-point feasibility-tolerance issues (the
    extracted solution values carry solver rounding noise that, chained
    through exact equality constraints such as mass balance or the
    boundary case of the 30% green-share constraint, can fall just
    outside CBC's tolerance) - direct evaluation has none of that."""
    I, J, K = sets["I"], sets["J"], sets["K"]
    D_ij, D_ik, D_jk = sets["D_ij"], sets["D_ik"], sets["D_jk"]

    QB = {"Parma": P["QBi_Parma"], "Reggio": P["QBi_Reggio"],
          "Forli": P["QBi_Forli"], "Piacenza": P["QBi_Piacenza"]}
    bc, wb, omega = P["bc"], P["wb"], P["omega"]
    alpha = {1: P["alpha1"], 2: P["alpha2"], 3: P["alpha3"]}
    ru = {1: P["ru_L1"], 2: P["ru_L2"], 3: P["ru_L3"]}
    s_inc = {1: P["s_L1"], 2: P["s_L2"], 3: P["s_L3"]}
    FC_i = {"Parma": P["FC_Parma"], "Reggio": P["FC_Reggio"],
            "Forli": P["FC_Forli"], "Piacenza": P["FC_Piacenza"]}
    pcc, pcr, pcm, pcw = P["pcci"], P["pcrj"], P["pcmj"], P["pcwk"]
    CT_d, CT_g = P["CT_diesel"], P["CT_green"]
    ctax = P["carbon_tax_per_kg"]
    fec, fer, fem, few = P["feci"], P["ferj"], P["femj"], P["fewk"]
    te_d, te_g = P["te_diesel"], P["te_green"]

    x, y, z = sol["x"], sol["y"], sol["z"]
    R, M, W, V = sol["R"], sol["M"], sol["W"], sol["V"]

    total_cells = sum(QB[i] * bc * x[i] for i in I)
    R_tot = sum(sum(R[a]) for a in D_ij)
    M_tot = sum(sum(M[a]) for a in D_ij)
    W_tot = sum(sum(W[i]) for i in I)

    f_AC = sum(x[i] * QB[i] for i in I) * sum(ru[u] * alpha[u] for u in (1, 2, 3)) if include_f_AC else 0
    f_FC = sum(x[i] * FC_i[i] for i in I) + sum(y[j] * P["FC_j"] for j in J) + sum(z[k] * P["FC_k"] for k in K)
    f_PC = pcc * total_cells + pcr * R_tot + pcm * M_tot + pcw * W_tot

    f_TC = sum(D_ij[a] * (CT_d * R[a][0] + CT_g * R[a][1] + CT_d * M[a][0] + CT_g * M[a][1]) for a in D_ij) \
        + sum(D_ik[i] * (CT_d * W[i][0] + CT_g * W[i][1]) for i in I) \
        + sum(D_jk[j] * (CT_d * V[j][0] + CT_g * V[j][1]) for j in J)

    f_FEC_raw = fec * total_cells + fer * R_tot + fem * M_tot + few * W_tot
    f_TEC_raw = sum(D_ij[a] * (te_d * R[a][0] + te_g * R[a][1] + te_d * M[a][0] + te_g * M[a][1]) / omega
                    for a in D_ij) \
        + sum(D_ik[i] * (te_d * W[i][0] + te_g * W[i][1]) / omega for i in I) \
        + sum(D_jk[j] * (te_d * V[j][0] + te_g * V[j][1]) / omega for j in J)
    f_co2 = ctax * (f_FEC_raw + f_TEC_raw)

    f_inc = s_inc[1] * M_tot + s_inc[2] * R_tot + s_inc[3] * W_tot

    return f_AC + f_FC + f_PC + f_TC + f_co2 - f_inc


def cost_value(term):
    """pulp.value() works on both LpAffineExpression and plain numbers
    (e.g. f_AC=0 when include_f_AC=False)."""
    return term.value() if hasattr(term, "value") else float(term)


def extract_solution(variables, sets):
    """Pull solved variable values into plain dicts (used by the
    visualization and sensitivity-analysis modules)."""
    val = lambda v: v.value() if v.value() is not None else 0.0
    x = {i: val(variables["x"][i]) for i in sets["I"]}
    y = {j: val(variables["y"][j]) for j in sets["J"]}
    z = {k: val(variables["z"][k]) for k in sets["K"]}
    R = {a: (val(variables["R_d"][a]), val(variables["R_g"][a])) for a in sets["D_ij"]}
    M = {a: (val(variables["M_d"][a]), val(variables["M_g"][a])) for a in sets["D_ij"]}
    W = {i: (val(variables["W_d"][i]), val(variables["W_g"][i])) for i in sets["I"]}
    V = {j: (val(variables["V_d"][j]), val(variables["V_g"][j])) for j in sets["J"]}
    return dict(x=x, y=y, z=z, R=R, M=M, W=W, V=V)


def solve_and_report(m, variables, sets, costs=None):
    status = solve(m)
    print("Status:", status)
    print(f"Objective: EUR {pulp.value(m.objective):,.2f}")

    if costs:
        print("\nCost components (EUR):")
        for name, term in costs.items():
            print(f"  {name}: {cost_value(term):,.2f}")

    sol = extract_solution(variables, sets)
    print("\nOpen collection centres (x_i):")
    for i in sets["I"]:
        print(f"  {i}: {int(round(sol['x'][i]))}")
    print("Open recycling/remanufacturing centres (y_j):")
    for j in sets["J"]:
        print(f"  {j}: {int(round(sol['y'][j]))}")
    print("Open disposal centre (z_k):")
    for k in sets["K"]:
        print(f"  {k}: {int(round(sol['z'][k]))}")

    print("\nMain cell flows, diesel / green:")
    for (i, j) in sets["D_ij"]:
        rd, rg = sol["R"][(i, j)]
        md, mg = sol["M"][(i, j)]
        if rd + rg + md + mg > 1e-6:
            print(f"  {i:9s} -> {j:7s}  R: {rd:9.1f} / {rg:9.1f}   M: {md:9.1f} / {mg:9.1f}")


if __name__ == "__main__":
    P = load_params()
    m, variables, sets, costs = build_model(P)
    solve_and_report(m, variables, sets, costs)
