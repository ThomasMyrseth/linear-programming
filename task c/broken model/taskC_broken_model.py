"""Task c: main line from Warszawa to Jelenia Gora (ILP, see lp_formulation.md)."""
import csv
import itertools
import math
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
DATA = HERE.parent.parent/ "distances.csv"
SOLUTION = HERE / "BROKEN_main_line_solution.csv"

START, END = "Warszawa", "Jelenia Gora"
EXISTING = [("Radom", "Kielce"), ("Gliwice", "Opole")]
FIXED_ON_LINE = ["Warszawa", "Radom", "Kielce", "Gliwice", "Opole", "Jelenia Gora"] #the cities we HAVE to visit
CITIES_PER_AREA = {1: 4, 2: 5, 3: 5}  # endpoints + 2 / 3 / 3 other cities

# --- Data ---
with open(DATA, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
cities = [r["city"] for r in rows]
area = {r["city"]: int(r["area"]) for r in rows}
coord = {r["city"]: (float(r["x"]), float(r["y"])) for r in rows}
A = sorted(set(area.values()))
C = {a: [c for c in cities if area[c] == a] for a in A}

# Arcs only for i != j in the same area, plus the two existing cross-area cables.
# This covers "no self loops" and "cables only within the same area".
arcs = [(i, j) for a in A for i in C[a] for j in C[a] if i != j] + EXISTING
d = {(i, j): math.dist(coord[i], coord[j]) for i, j in arcs}

# --- Model ---
m = gp.Model("main_line")
x = m.addVars(arcs, vtype=GRB.BINARY, name="x")
w = m.addVars(cities, vtype=GRB.BINARY, name="w")

m.setObjective(x.prod(d), GRB.MINIMIZE)

# Is city connected: one cable in and one cable out (also balances in/out)
for i in cities:
    if i not in (START, END):
        m.addConstr(w[i] == x.sum("*", i))
        m.addConstr(w[i] == x.sum(i, "*"))

# Area constraints
for c in FIXED_ON_LINE:
    m.addConstr(w[c] == 1)
for a in A:
    m.addConstr(gp.quicksum(w[c] for c in C[a]) == CITIES_PER_AREA[a])

# City coverage
m.addConstr(w["Konin"] + w["Kalisz"] >= 1)
m.addConstr(w["Poznan"] + w["Zielona Gora"] + w["Leszno"] >= 1)
m.addConstr(w["Bytom"] + w["Sosnowiec"] + w["Katowice"] <= 1)
m.addConstr(w["Wodzislaw Slaski"] + w["Jastrzebie-Zdroj"] <= 1)

# Must use existing cables
for e in EXISTING:
    m.addConstr(x[e] == 1)

# Must start in Warszawa, end in Jelenia Gora
m.addConstr(x.sum(START, "*") == 1)
m.addConstr(x.sum("*", START) == 0)
m.addConstr(x.sum("*", END) == 1)
m.addConstr(x.sum(END, "*") == 0)

# !!! BROKEN MODEL, WE REMOVE THE CONSTRAINT NOT ALLOWING FOR A TWO WAY CABLE
# # Not two-way cable
# for i, j in arcs:
#     if i < j and (j, i) in x:
#         m.addConstr(x[i, j] + x[j, i] <= 1)

# No cycles: a city set S inside one area holds at most |S|-1 cables.
# Per area is enough: cross-area arcs only go area 1 -> 2 -> 3, so no cycle spans areas.
for a in A:
    for k in range(3, len(C[a]) + 1): #!!!BROKEN MODEL: we only check cycles of lenght 3, so now we allow two way cables back and forth
        for S in itertools.combinations(C[a], k):
            m.addConstr(gp.quicksum(x[i, j] for i in S for j in S if i != j) <= k - 1)

m.optimize()
assert m.Status == GRB.OPTIMAL, f"Gurobi status {m.Status}"

# --- Output ---
succ = {i: j for i, j in arcs if x[i, j].X > 0.5}
route = [START]
while route[-1] in succ:
    route.append(succ[route[-1]])
# Every chosen cable lies on the Warszawa -> Jelenia Gora route (no side subtours)
# !!! BROKEN MODEL: we allow cycles
# assert route[-1] == END and len(succ) == len(route) - 1 == sum(CITIES_PER_AREA.values()) - 1, route

existing = sum(d[e] for e in EXISTING)
print(f"\nLength of main cable: {m.ObjVal:.3f}")
print(f"  existing cable (Radom-Kielce, Gliwice-Opole): {existing:.3f}")
print(f"  new cable to lay: {m.ObjVal - existing:.3f}")
print("Cities in order:", " -> ".join(route))

# !!! BROKEN MODEL: cables not on the route form loops (every off-route city has one cable in and one out)
loops = []
for i in succ:
    if i not in route and not any(i in loop for loop in loops):
        loop = [i]
        while succ[loop[-1]] != i:
            loop.append(succ[loop[-1]])
        loops.append(loop + [i])  # back to the start city
for k, loop in enumerate(loops, 1):
    print(f"Loop {k}:", " -> ".join(loop))

# One block per part (route, loop 1, loop 2, ...); cumulative_length runs over all parts, so it ends at the objective
rows, total = [], 0.0
for part, seq in [("route", route)] + [(f"loop {k}", loop) for k, loop in enumerate(loops, 1)]:
    for k, c in enumerate(seq, 1):
        leg = d[seq[k - 2], c] if k > 1 else 0.0  # cable length into this city
        total += leg
        rows.append((k, c, leg, total, part))
assert math.isclose(total, m.ObjVal), (total, m.ObjVal)
with open(SOLUTION, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(("order", "city", "leg_length", "cumulative_length", "part"))
    w.writerows(rows)
print(f"Solution written to {SOLUTION.name}")
