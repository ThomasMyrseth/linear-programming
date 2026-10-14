"""Task d: connect cities not on the main line to the switching stations (LP, see lp-formulation-daisy-chain.md)."""
import csv
import math
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent / "distances.csv"
MAIN_LINE = HERE.parent.parent / "task c" / "main_line_solution.csv"
SOLUTION = HERE / "connections_solution.csv"

STATIONS = {"Warszawa": 2, "Kielce": 3, "Opole": 1}  # standard units per switching station
UNIT_CAP = 400  # TB/s per standard unit
MAX_CABLE = 200  # TB/s, max for one copper cable
COST = 1000  # EUR per coordinate unit per TB/s
LODZ_SHARE = 0.4  # max share of Lodz' outflow in one cable
RELAY = True  # False: only direct city -> station cables

# --- Data ---
with open(DATA, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
coord = {r["city"]: (float(r["x"]), float(r["y"])) for r in rows}
with open(MAIN_LINE, encoding="utf-8") as f:
    on_line = {r["city"] for r in csv.DictReader(f)}
# Cities not on the main line; switching stations have no demand
demand = {r["city"]: float(r["demand_tbps"]) for r in rows if r["demand_tbps"] and r["city"] not in on_line}
C = list(demand)

# City -> station cables, plus city -> city cables if cities may relay flow.
# i != j covers "no self loops".
arcs = [(c, s) for c in C for s in STATIONS] + ([(i, j) for i in C for j in C if i != j] if RELAY else [])
d = {(i, j): math.dist(coord[i], coord[j]) for i, j in arcs}

# --- Model ---
m = gp.Model("connections")
# Upper bound: max cable capacity and capacity loss over distance, x <= 2*pi*min(35, 70 - d)
x = m.addVars(arcs, ub={a: min(MAX_CABLE, 2 * math.pi * min(35, 70 - d[a])) for a in arcs}, name="x")

m.setObjective(gp.quicksum(COST * d[a] * x[a] for a in arcs), GRB.MINIMIZE)

# Balance: flow out of a city = flow in + its own demand
for i in C:
    m.addConstr(x.sum(i, "*") == x.sum("*", i) + demand[i], name=f"balance[{i}]")

# Switching station capacity
for s, units in STATIONS.items():
    m.addConstr(x.sum("*", s) <= UNIT_CAP * units, name=f"station[{s}]")

# All demand ends up at a switching station
m.addConstr(gp.quicksum(x.sum("*", s) for s in STATIONS) == sum(demand.values()), name="all_connected")

# Lodz: at most 40 % of its outflow in one cable
if "Lodz" in demand:
    for j in (j for i, j in arcs if i == "Lodz"):
        m.addConstr(x["Lodz", j] <= LODZ_SHARE * x.sum("Lodz", "*"), name=f"lodz[{j}]")

m.optimize()
assert m.Status == GRB.OPTIMAL, f"Gurobi status {m.Status}"

# --- Output ---
cables = [(i, j, x[i, j].X, d[i, j], COST * d[i, j] * x[i, j].X) for i, j in arcs if x[i, j].X > 1e-6]

print(f"\nCities not on the main line: {', '.join(C)}")
print(f"Total cost to connect them: {m.ObjVal:,.2f} EUR")
print(f"\n{'From':<18}{'To':<18}{'TB/s':>8}{'Length':>8}{'Cost (EUR)':>16}")
for i, j, cap, length, cost in cables:
    print(f"{i:<18}{j:<18}{cap:>8.2f}{length:>8.2f}{cost:>16,.2f}")

print("\nSwitching station usage:")
for s, units in STATIONS.items():
    used = x.sum("*", s).getValue()
    print(f"  {s:<10}{used:8.2f} / {UNIT_CAP * units} TB/s ({used / (UNIT_CAP * units):.1%})")

with open(SOLUTION, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(("from", "to", "capacity_tbps", "length", "cost_eur"))
    w.writerows(cables)
print(f"Solution written to {SOLUTION.name}")
