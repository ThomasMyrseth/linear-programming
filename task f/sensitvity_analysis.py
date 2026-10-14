"""Task f: sensitivity analysis of the direct-link model (task e).

Both questions are right-hand-side changes: Konin's demand is the RHS of demand[Konin], and pi sits in the
upper bounds x <= 2*pi*min(35, 70 - d). An RHS change does not touch the reduced costs, so the basis stays
optimal exactly as long as it stays primal feasible, which is what Gurobi's RHS ranging (SARHSLow/SARHSUp) gives.
"""
import csv
import math
from pathlib import Path

import gurobipy as gp
from gurobipy import GRB
import matplotlib

matplotlib.use("Agg")  # file output only, no window
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "distances.csv"
MAIN_LINE = HERE.parent / "task c" / "main_line_solution.csv"
OUT = HERE / "sensitivity.png"

STATIONS = {"Warszawa": 2, "Kielce": 3, "Opole": 1}  # standard units per switching station
UNIT_CAP = 400  # TB/s per standard unit
MAX_CABLE = 200  # TB/s, max for one copper cable
COST = 1000  # EUR per coordinate unit per TB/s
LODZ_SHARE = 0.4  # max share of Lodz' outflow in one cable
KONIN_ERRORS = [-0.2, -0.1, 0.1, 0.2]  # possible miscalculation of Konin's demand

SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, ORANGE = "#2a78d6", "#eb6834"

# --- Data ---
with open(DATA, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
coord = {r["city"]: (float(r["x"]), float(r["y"])) for r in rows}
with open(MAIN_LINE, encoding="utf-8") as f:
    on_line = {r["city"] for r in csv.DictReader(f)}
# Cities not on the main line; switching stations have no demand
demand = {r["city"]: float(r["demand_tbps"]) for r in rows if r["demand_tbps"] and r["city"] not in on_line}
C = list(demand)

# Only city -> station cables. This also covers "no self loops", since no city is a station.
arcs = [(c, s) for c in C for s in STATIONS]
d = {(i, j): math.dist(coord[i], coord[j]) for i, j in arcs}

# --- Model ---
m = gp.Model("direct_links_sensitivity")
m.Params.OutputFlag = 0
x = m.addVars(arcs, ub=MAX_CABLE, name="x")
# pi as a variable fixed by one constraint, so changing pi is a change of one RHS instead of many bounds
p = m.addVar(lb=-GRB.INFINITY, name="p")
pi_con = m.addConstr(p == math.pi, name="pi")

m.setObjective(gp.quicksum(COST * d[a] * x[a] for a in arcs), GRB.MINIMIZE)

# Capacity loss over distance, x <= 2*pi*min(35, 70 - d), written with p
for c, s in arcs:
    m.addConstr(x[c, s] <= 2 * min(35, 70 - d[c, s]) * p, name=f"shannon[{c},{s}]")

# Lodz: at most 40 % of its outflow in one cable
if "Lodz" in demand:
    for s in STATIONS:
        m.addConstr(x["Lodz", s] <= LODZ_SHARE * x.sum("Lodz", "*"), name=f"lodz[{s}]")

# Switching station capacity
for s, units in STATIONS.items():
    m.addConstr(x.sum("*", s) <= UNIT_CAP * units, name=f"station[{s}]")

# Each city sends exactly its demand.
# The task e constraint "all demand ends up at a switching station" is left out: it is the sum of these, so it
# only splits Konin's dual between two constraints and makes Konin's RHS range collapse to [236, 236].
dem = {c: m.addConstr(x.sum(c, "*") == demand[c], name=f"demand[{c}]") for c in C}

m.optimize()
assert m.Status == GRB.OPTIMAL, f"Gurobi status {m.Status}"
base = m.ObjVal
print(f"Total cost (base): {base:,.2f} EUR")

# --- Sensitivity: Konin demand ---
konin = dem["Konin"]
dual, low, up = konin.Pi, konin.SARHSLow, konin.SARHSUp
print(f"\nKonin demand {demand['Konin']:.0f} TB/s: dual {dual:,.2f} EUR per TB/s, valid for demand in [{low:.1f}, {up:.1f}]")
print(f"{'Change':>7}{'Demand':>9}{'In range':>10}{'Δ dual (EUR)':>16}{'Δ re-solved (EUR)':>20}{'New cost (EUR)':>18}")
scenarios = []
for e in KONIN_ERRORS:
    new = demand["Konin"] * (1 + e)
    konin.RHS = new
    m.optimize()
    assert m.Status == GRB.OPTIMAL, f"Gurobi status {m.Status}"
    est, real = dual * (new - demand["Konin"]), m.ObjVal - base
    scenarios.append((e, new, low <= new <= up, est, real))
    print(f"{e:>+7.0%}{new:>9.1f}{'yes' if low <= new <= up else 'no':>10}{est:>16,.2f}{real:>20,.2f}{m.ObjVal:>18,.2f}")
konin.RHS = demand["Konin"]
m.optimize()
assert m.Status == GRB.OPTIMAL, f"Gurobi status {m.Status}"

# --- Sensitivity: pi ---
pi_low, pi_up = pi_con.SARHSLow, pi_con.SARHSUp
print(f"\npi: dual {pi_con.Pi:,.2f} EUR per unit of pi; the basis stays optimal for pi in [{pi_low:.6f}, {pi_up:.6f}]")

# --- Plot ---
fig, (ax, ax_pi) = plt.subplots(1, 2, figsize=(12, 4.8), facecolor=SURFACE, gridspec_kw={"width_ratios": [3, 2]})
for a in (ax, ax_pi):
    a.set_facecolor(SURFACE)
    for side, spine in a.spines.items():
        spine.set_visible(side == "bottom")
        spine.set_color(AXIS)
    a.tick_params(colors=MUTED, labelsize=8.5)

# Konin: cost change per scenario, re-solved next to the dual estimate
w = 0.36
for k, (e, new, inside, est, real) in enumerate(scenarios):
    for dx, val, color in ((-w / 2, real, BLUE), (w / 2, est, ORANGE)):
        ax.bar(k + dx, val / 1e6, w, color=color, edgecolor=SURFACE, lw=1.5, zorder=2)
        ax.annotate(f"{val / 1e6:+.2f}", (k + dx, val / 1e6), xytext=(0, 4 if val > 0 else -4),
                    textcoords="offset points", ha="center", va="bottom" if val > 0 else "top", fontsize=8, color=INK)
    if not inside:
        ax.annotate(f"outside RHS range\n[{low:.1f}, {up:.1f}] TB/s", (k, 0), xytext=(0, 8), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color=INK_2)
ax.axhline(0, color=AXIS, lw=1, zorder=1)
ax.set_xticks(range(len(scenarios)), [f"{e:+.0%}\n{new:.1f} TB/s" for e, new, *_ in scenarios])
ax.set_ylabel("Change in total cost (M EUR)", color=INK_2)
ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
ax.margins(y=0.15)
ax.set_title(f"Konin demand error (base {demand['Konin']:.0f} TB/s)", color=INK, loc="left")
ax.bar(0, 0, color=BLUE, label="Re-solved")
ax.bar(0, 0, color=ORANGE, label=f"Dual estimate ({dual:,.0f} EUR per TB/s)")
ax.legend(loc="upper left", frameon=False, fontsize=8.5, labelcolor=INK_2)

# pi: interval where the current basis stays optimal
ax_pi.barh(0, pi_up - pi_low, 0.35, left=pi_low, color=BLUE, zorder=2)
ax_pi.plot([math.pi] * 2, [-0.3, 0.3], color=INK, lw=2, zorder=3)
ax_pi.annotate(f"π = {math.pi:.5f}", (math.pi, 0.3), xytext=(0, 4), textcoords="offset points", ha="center",
               va="bottom", fontsize=8.5, color=INK)
for v, ha in ((pi_low, "right"), (pi_up, "left")):
    ax_pi.annotate(f"{v:.4f}", (v, 0), xytext=(-5 if ha == "right" else 5, 0), textcoords="offset points",
                   ha=ha, va="center", fontsize=8.5, color=INK)
ax_pi.set_xlim(pi_low - 0.08, pi_up + 0.08)
ax_pi.set_ylim(-1, 1)
ax_pi.set_yticks([])
ax_pi.set_xlabel("π", color=INK_2)
ax_pi.grid(axis="x", color=GRID, lw=0.6, zorder=0)
ax_pi.set_title("π range where the basis stays optimal", color=INK, loc="left")

fig.suptitle(f"Sensitivity of the direct-link model (base cost {base:,.0f} EUR)", color=INK, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor=SURFACE)
print(f"\nSaved {OUT.name}")
