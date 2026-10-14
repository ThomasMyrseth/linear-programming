"""Independent checker for the task f sensitivity results (Konin demand and pi).
Rebuilds the task e direct-link LP itself; does not use sensitvity_analysis.py.
Konin: re-solves with demand[Konin] and all_connected both updated.
pi: keeps the base optimal basis fixed, x_B(pi) = B^-1 (b - N x_N(pi))."""
import csv
import math
import sys
from pathlib import Path

import gurobipy as gp
import numpy as np
from gurobipy import GRB

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "distances.csv"
MAIN_LINE = HERE.parent / "task c" / "main_line_solution.csv"

CLAIMED_KONIN_DELTA = {0.8: -1_721_729.51, 0.9: -893_623.54, 1.1: 893_623.54, 1.2: 1_787_247.08}  # EUR
CLAIMED_KONIN_SLOPE = 37_865.40  # EUR per TB/s
CLAIMED_KONIN_RANGE = (200.0, 295.1)  # TB/s
CLAIMED_PI_RANGE = (2.932617, 3.196822)
CLAIMED_PI_SLOPE = -384_444.67  # EUR per unit of pi
KONIN_BASE = 236
STATIONS = {"Warszawa": 2, "Kielce": 3, "Opole": 1}

with open(DATA, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
coord = {r["city"]: (float(r["x"]), float(r["y"])) for r in rows}
with open(MAIN_LINE, encoding="utf-8") as f:
    on_line = {r["city"] for r in csv.DictReader(f)}
demand0 = {r["city"]: float(r["demand_tbps"]) for r in rows if r["demand_tbps"] and r["city"] not in on_line}
assert demand0["Konin"] == KONIN_BASE
C = list(demand0)
arcs = [(c, s) for c in C for s in STATIONS]
d = {(i, j): math.dist(coord[i], coord[j]) for i, j in arcs}
ub = lambda a, p: min(200, 2 * p * min(35, 70 - d[a]))

ENV = gp.Env(empty=True)
ENV.setParam("OutputFlag", 0)
ENV.start()


def build(konin=KONIN_BASE, p=math.pi):
    dem = {**demand0, "Konin": konin}
    m = gp.Model(env=ENV)
    m.Params.Method = 0  # primal simplex, no presolve: gives the same base basis as the earlier check
    m.Params.Presolve = 0
    x = m.addVars(arcs, ub={a: ub(a, p) for a in arcs}, name="x")
    m.setObjective(gp.quicksum(1000 * d[a] * x[a] for a in arcs), GRB.MINIMIZE)
    for s in STATIONS:
        m.addConstr(x["Lodz", s] <= 0.4 * x.sum("Lodz", "*"), name=f"lodz[{s}]")
    m.addConstr(gp.quicksum(x.sum("*", s) for s in STATIONS) == sum(dem.values()), name="all_connected")
    for s, u in STATIONS.items():
        m.addConstr(x.sum("*", s) <= 400 * u, name=f"station[{s}]")
    for c in C:
        m.addConstr(x.sum(c, "*") == dem[c], name=f"demand[{c}]")
    m.optimize()
    return m


def bisect(ok, inside, outside, n=100):
    # ok(inside) holds, ok(outside) fails, and the ok-set is an interval
    assert ok(inside) and not ok(outside)
    for _ in range(n):
        mid = (inside + outside) / 2
        inside, outside = (mid, outside) if ok(mid) else (inside, mid)
    return inside


def cost(k):
    m = build(k)
    return m.ObjVal if m.Status == GRB.OPTIMAL else None


checks = []  # (name, computed, claimed, tol)

# --- Konin ---
base = cost(KONIN_BASE)
print(f"Base cost: {base:,.2f} EUR")
for fac, claimed in CLAIMED_KONIN_DELTA.items():
    k = KONIN_BASE * fac
    v = cost(k)
    delta = v - base
    print(f"Konin {k:6.1f} TB/s: cost {v:,.2f}, change {delta:+,.2f} EUR")
    checks.append((f"Konin x{fac} cost change", delta, claimed, 0.01))
slope = cost(KONIN_BASE + 0.5) - cost(KONIN_BASE - 0.5)
# LP value is convex in the RHS, so the set where it stays on the base line is an interval
linear = lambda k: (v := cost(k)) is not None and abs(v - (base + slope * (k - KONIN_BASE))) < 1e-3
lo, hi = bisect(linear, KONIN_BASE, 0.0), bisect(linear, KONIN_BASE, 1000.0)
print(f"Konin marginal cost {slope:,.4f} EUR per TB/s, holds for [{lo:.4f}, {hi:.4f}]")
checks += [("Konin marginal cost", slope, CLAIMED_KONIN_SLOPE, 0.01),
           ("Konin range low", lo, CLAIMED_KONIN_RANGE[0], 0.05),
           ("Konin range high", hi, CLAIMED_KONIN_RANGE[1], 0.05)]

# --- pi: fixed base basis ---
m = build()
V, R = m.getVars(), m.getConstrs()
assert all(c.Sense in "<=" for c in R)
A = np.zeros((len(R), len(V)))
for r, c in enumerate(R):
    row = m.getRow(c)
    for k in range(row.size()):
        A[r, row.getVar(k).index] += row.getCoeff(k)
b = np.array([c.RHS for c in R])
M = np.hstack([A, np.eye(len(R))])  # slack s = b - Ax for each row, s >= 0 ('<') or s = 0 ('=')
stat = np.array([v.VBasis for v in V] + [c.CBasis for c in R])
basic = np.flatnonzero(stat == 0)
assert len(basic) == len(R) and set(stat) <= {0, -1, -2}
cvec = np.array([1000 * d[a] for a in arcs])


def fixed_basis(p):
    hi = np.array([ub(a, p) for a in arcs] + [np.inf if c.Sense == "<" else 0.0 for c in R])
    z = np.where(stat == -2, hi, 0.0)  # nonbasics at upper or lower (0) bound
    z[basic] = np.linalg.solve(M[:, basic], b - M @ z)
    return z, hi


def feasible(p, tol=1e-9):
    z, hi = fixed_basis(p)
    return bool(np.all(z[basic] >= -tol) and np.all(z[basic] <= hi[basic] + tol))


obj = lambda p: cvec @ fixed_basis(p)[0][:len(V)]
print(f"\nFixed-basis cost at pi: {obj(math.pi):,.2f} EUR (Gurobi {m.ObjVal:,.2f})")
assert abs(obj(math.pi) - m.ObjVal) < 1e-3
plo, phi = bisect(feasible, math.pi, 2.0), bisect(feasible, math.pi, 5.0)
pslope = (obj(math.pi + 0.01) - obj(math.pi - 0.01)) / 0.02
print(f"Base basis primal feasible for pi in [{plo:.6f}, {phi:.6f}], slope {pslope:,.4f} EUR per unit of pi")
checks += [("pi range low", plo, CLAIMED_PI_RANGE[0], 1e-6),
           ("pi range high", phi, CLAIMED_PI_RANGE[1], 1e-6),
           ("pi slope", pslope, CLAIMED_PI_SLOPE, 0.01)]

print()
fails = 0
for name, got, claimed, tol in checks:
    ok = abs(got - claimed) <= tol
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}: computed {got:,.6f}, claimed {claimed:,.6f} (tol {tol})")
print(f"\n{len(checks) - fails}/{len(checks)} checks pass")
sys.exit(1 if fails else 0)
