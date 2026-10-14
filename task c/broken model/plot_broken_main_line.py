"""Plot the task c main line (main_line_solution.csv) on the city coordinates."""
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # file output only, no window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
OUT = HERE / "BROKEN_main_line.png"
EXISTING = {("Radom", "Kielce"), ("Gliwice", "Opole")}

AREA_COLOR = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
# Label offsets (points) for crowded cities; default is up-right
LABEL_POS = {
    "Gliwice": (-7, -12, "right"), "Katowice": (6, -12, "left"), "Wodzislaw Slaski": (-7, 5, "right"),
    "Bielsko": (6, -12, "left"), "Skierniewice": (-6, 6, "right"), "Jelenia Gora": (0, -15, "center"),
}

with open(HERE.parent / "distances.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
area = {r["city"]: int(r["area"]) for r in rows}
coord = {r["city"]: (float(r["x"]), float(r["y"])) for r in rows}
with open(HERE / "BROKEN_main_line_solution.csv", encoding="utf-8") as f:
    route = [r["city"] for r in csv.DictReader(f)]
legs = list(zip(route, route[1:]))
length = sum(math.dist(coord[i], coord[j]) for i, j in legs)

fig, ax = plt.subplots(figsize=(10, 7.5), facecolor=SURFACE)
ax.set_facecolor(SURFACE)

# Cables: solid = new, dashed = existing; arrowhead at the midpoint shows direction
for i, j in legs:
    (x0, y0), (x1, y1) = coord[i], coord[j]
    ax.plot([x0, x1], [y0, y1], color=INK, lw=2, ls="--" if (i, j) in EXISTING else "-", zorder=2)
    ax.annotate("", xy=(x0 + 0.56 * (x1 - x0), y0 + 0.56 * (y1 - y0)),
                xytext=(x0 + 0.44 * (x1 - x0), y0 + 0.44 * (y1 - y0)),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0, mutation_scale=16), zorder=3)

# Cities: filled = on the main line, hollow = not on it
for c, (x, y) in coord.items():
    on = c in route
    ax.scatter(x, y, s=90, zorder=4, linewidths=2 if on else 1.6,
               facecolor=AREA_COLOR[area[c]] if on else SURFACE,
               edgecolor=SURFACE if on else AREA_COLOR[area[c]])
    dx, dy, ha = LABEL_POS.get(c, (6, 5, "left"))
    ax.annotate(c, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=8.5, zorder=5,
                color=INK if on else MUTED, fontweight="bold" if c in (route[0], route[-1]) else "normal")

ax.set_aspect("equal")
ax.margins(0.08)
ax.grid(color=GRID, lw=0.6, zorder=0)
for s in ax.spines.values():
    s.set_color(AXIS)
ax.tick_params(colors=MUTED, labelsize=8)
ax.set_xlabel("x (coordinate units)", color=INK_2)
ax.set_ylabel("y (coordinate units)", color=INK_2)
ax.set_title(f"Main line {route[0]} to {route[-1]}: length {length:.2f} ({len(route)} cities)",
             color=INK, loc="left")

handles = [Line2D([], [], ls="", marker="o", ms=9, color=AREA_COLOR[a], label=f"Area {a}") for a in AREA_COLOR]
handles += [
    Line2D([], [], ls="", marker="o", ms=9, mfc=SURFACE, mec=MUTED, mew=1.6, label="Not on main line"),
    Line2D([], [], color=INK, lw=2, label="New cable"),
    Line2D([], [], color=INK, lw=2, ls="--", label="Existing cable"),
]
ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=9, labelcolor=INK_2)

fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor=SURFACE)
print(f"Saved {OUT.name}")
