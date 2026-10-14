"""Independent checker for the task e daisy-chain solution (connections_solution.csv).
Written by an AI from the case text and the solution file format only, without seeing the model."""
import csv, math, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
CLAIMED_TOTAL = 65_238_977.05
UNITS = {"Warszawa": 2, "Kielce": 3, "Opole": 1}
UNIT_CAP, CABLE_CAP, LODZ_SHARE = 400.0, 200.0, 0.4
TOL = 1e-6

pos, dem = {}, {}
with open(f"{BASE}/distances.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        pos[r["city"]] = (float(r["x"]), float(r["y"]))
        if r["demand_tbps"].strip():
            dem[r["city"]] = float(r["demand_tbps"])
with open(f"{BASE}/task c/main_line_solution.csv", encoding="utf-8") as f:
    main = {r["city"] for r in csv.DictReader(f)}
with open(HERE / "connections_solution.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

stations = set(UNITS)
offline = {c for c in dem if c not in main}
dist = lambda a, b: math.dist(pos[a], pos[b])
cap = lambda d: min(CABLE_CAP, 2 * math.pi * min(35.0, 70.0 - d))

errors = []
def check(cond, msg):
    if not cond:
        errors.append(msg)

out, inn = defaultdict(float), defaultdict(float)
pairs, total = {}, 0.0
for r in rows:
    a, b = r["from"], r["to"]
    x, L, c = float(r["capacity_tbps"]), float(r["length"]), float(r["cost_eur"])
    check(a in pos and b in pos, f"unknown city in row {a}->{b}")
    if a not in pos or b not in pos:
        continue
    check(a != b, f"self loop {a}")
    check((a, b) not in pairs, f"duplicate row {a}->{b}")
    check((b, a) not in pairs, f"both directions {a}<->{b}")
    pairs[(a, b)] = x
    check(x > TOL, f"non-positive flow {a}->{b}: {x}")
    d = dist(a, b)
    check(abs(L - d) < 1e-3, f"length {a}->{b}: file {L} vs euclid {d:.6f}")
    check(x <= CABLE_CAP + TOL, f"cable > 200 {a}->{b}: {x}")
    check(x <= cap(d) + 1e-3, f"Shannon cap {a}->{b}: {x} > {cap(d):.4f}")
    check(abs(c - 1000 * d * x) < 1.0, f"cost {a}->{b}: file {c} vs {1000*d*x:.2f}")
    check(a in offline, f"sender {a} is not an off-line demand city")
    check(b in stations or b in offline, f"receiver {b} is neither station nor off-line city")
    out[a] += x
    inn[b] += x
    total += c

for c in offline:  # net outflow = demand
    check(abs(out[c] - inn[c] - dem[c]) < 1e-3, f"{c}: net out {out[c]-inn[c]:.4f} != demand {dem[c]}")
for c in main | stations:
    check(out[c] < TOL, f"main-line/station {c} sends {out[c]}")
for c in main - stations:
    check(inn[c] < TOL, f"non-station main-line {c} receives {inn[c]}")
for s, u in UNITS.items():
    check(inn[s] <= UNIT_CAP * u + 1e-3, f"station {s} inflow {inn[s]:.4f} > {UNIT_CAP*u}")
    print(f"station {s}: inflow {inn[s]:.4f} / {UNIT_CAP*u:.0f}")
lodz = "Lodz"
for (a, b), x in pairs.items():
    if a == lodz:
        check(x <= LODZ_SHARE * out[lodz] + 1e-3, f"Lodz cable {a}->{b} {x} > 40% of {out[lodz]}")
print(f"Lodz outflow {out[lodz]:.4f}, inflow {inn[lodz]:.4f}, max cable {max(x for (a,b),x in pairs.items() if a==lodz):.4f}")
# all flow ends at a station: total station inflow == total demand of off-line cities
tot_dem = sum(dem[c] for c in offline)
st_in = sum(inn[s] for s in stations)
check(abs(st_in - tot_dem) < 1e-3, f"station inflow {st_in} != off-line demand {tot_dem}")
# no relay cycles (directed graph of rows acyclic)
adj = defaultdict(list)
for (a, b) in pairs:
    adj[a].append(b)
state = {}
def dfs(u):
    state[u] = 1
    for v in adj[u]:
        if state.get(v) == 1:
            errors.append(f"cycle through {u}->{v}")
        elif v not in state:
            dfs(v)
    state[u] = 2
for u in list(adj):
    if u not in state:
        dfs(u)
check(abs(total - CLAIMED_TOTAL) < 1.0, f"sum of costs {total:.2f} != claimed {CLAIMED_TOTAL}")
# recompute from exact distances
exact = sum(1000 * dist(a, b) * x for (a, b), x in pairs.items())
print(f"off-line cities ({len(offline)}): {sorted(offline)}; demand {tot_dem}")
print(f"sum cost_eur column = {total:.2f}; recomputed exact = {exact:.2f}; claimed = {CLAIMED_TOTAL:.2f}")
print("ERRORS:" if errors else "ALL CHECKS PASSED")
for e in errors:
    print("  -", e)
sys.exit(1 if errors else 0)
