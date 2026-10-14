"""Independent checker for the task e direct-link solution (connections_solution.csv).
Written by an AI from the case text and the solution file format only, without seeing the model.
Ends with its own LP of the case to compare the optimal cost."""
import csv, math, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = str(HERE.parent.parent)
SOL = HERE / "connections_solution.csv"
CLAIMED = 66_696_434.43
TOL = 1e-6
UNITS = {"Warszawa": 2, "Kielce": 3, "Opole": 1}
LODZ = "Lodz"

cities = {}
for r in csv.DictReader(open(ROOT + "/distances.csv", encoding="utf-8")):
    cities[r["city"]] = (float(r["x"]), float(r["y"]), float(r["demand_tbps"]) if r["demand_tbps"] else None)
main = {r["city"] for r in csv.DictReader(open(ROOT + "/task c/main_line_solution.csv", encoding="utf-8"))}
offline = {c for c, (_, _, d) in cities.items() if d is not None and c not in main}
dist = lambda a, b: math.hypot(cities[a][0] - cities[b][0], cities[a][1] - cities[b][1])
shannon = lambda d: 2 * math.pi * min(35, 70 - d)

errs = []
rows = list(csv.DictReader(open(SOL, encoding="utf-8")))
out = defaultdict(float); inflow = defaultdict(float); pairs = set(); total = 0.0
for r in rows:
    f, t, cap, L, cost = r["from"], r["to"], float(r["capacity_tbps"]), float(r["length"]), float(r["cost_eur"])
    tag = f"{f}->{t}"
    if f not in cities or t not in cities: errs.append(f"{tag}: unknown city"); continue
    if t not in UNITS: errs.append(f"{tag}: destination not a switching station (city-to-city)")
    if f not in offline: errs.append(f"{tag}: source not an off-line demand city")
    if (f, t) in pairs: errs.append(f"{tag}: parallel cable")
    pairs.add((f, t))
    if cap < -TOL: errs.append(f"{tag}: negative cap {cap}")
    if cap > 200 + TOL: errs.append(f"{tag}: cap {cap} > 200")
    d = dist(f, t)
    if abs(L - d) > 1e-6: errs.append(f"{tag}: length {L} != {d}")
    if cap > shannon(d) + TOL: errs.append(f"{tag}: cap {cap} > shannon {shannon(d)}")
    if abs(cost - 1000 * d * cap) > 1e-3: errs.append(f"{tag}: cost {cost} != {1000*d*cap}")
    out[f] += cap; inflow[t] += cap; total += cost

for c in offline:
    if abs(out[c] - cities[c][2]) > 1e-4: errs.append(f"{c}: sends {out[c]} != demand {cities[c][2]}")
for c in main:
    if out[c] > TOL: errs.append(f"main-line {c} sends {out[c]}")
for s, u in UNITS.items():
    if inflow[s] > 400 * u + 1e-4: errs.append(f"{s}: inflow {inflow[s]} > {400*u}")
for r in rows:
    if r["from"] == LODZ and float(r["capacity_tbps"]) > 0.4 * out[LODZ] + 1e-6:
        errs.append(f"Lodz cable {r['to']} {r['capacity_tbps']} > 40% of {out[LODZ]}")
recomputed = sum(1000 * dist(r["from"], r["to"]) * float(r["capacity_tbps"]) for r in rows)
if abs(total - CLAIMED) > 0.01 or abs(recomputed - CLAIMED) > 0.01:
    errs.append(f"total: csv sum {total:.2f}, recomputed {recomputed:.2f}, claimed {CLAIMED:.2f}")

print("off-line cities:", sorted(offline))
print("station inflow:", {s: round(inflow[s], 4) for s in UNITS})
print(f"total csv {total:.2f} recomputed {recomputed:.2f}")
print("\n".join(errs) if errs else "ALL CHECKS PASS")

# Independent LP: direct links only
import gurobipy as gp
from gurobipy import GRB
m = gp.Model(); m.Params.OutputFlag = 0
x = {(i, s): m.addVar(ub=min(200, max(0, shannon(dist(i, s)))), name=f"x_{i}_{s}") for i in offline for s in UNITS}
for i in offline: m.addConstr(gp.quicksum(x[i, s] for s in UNITS) == cities[i][2])
for s, u in UNITS.items(): m.addConstr(gp.quicksum(x[i, s] for i in offline) <= 400 * u)
for s in UNITS: m.addConstr(x[LODZ, s] <= 0.4 * cities[LODZ][2])
m.setObjective(gp.quicksum(1000 * dist(i, s) * x[i, s] for i, s in x), GRB.MINIMIZE)
m.optimize()
print("LP status", m.Status, "obj", f"{m.ObjVal:.2f}", "diff vs claimed", f"{m.ObjVal - CLAIMED:.4f}")
sys.exit(1 if errs else 0)
