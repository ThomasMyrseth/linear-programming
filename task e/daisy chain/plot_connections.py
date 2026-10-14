"""Plot the task d connections (connections_solution.csv) with capacities, on top of the task c main line."""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # file output only, no window
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
OUT = HERE / "connections.png"
EXISTING = {("Radom", "Kielce"), ("Gliwice", "Opole")}
STATIONS = {"Warszawa": 2, "Kielce": 3, "Opole": 1}  # standard units per switching station
UNIT_CAP = 400  # TB/s per standard unit

STATION_COLOR = {"Warszawa": "#2a78d6", "Kielce": "#eb6834", "Opole": "#1baf7a"}
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
# Label offsets (points) for crowded cities; default is up-right
LABEL_POS = {
    "Gliwice": (-7, -12, "right"), "Katowice": (-7, -12, "right"), "Wodzislaw Slaski": (-7, 5, "right"),
    "Bielsko": (6, -12, "left"), "Skierniewice": (-6, 6, "right"), "Jelenia Gora": (0, -15, "center"),
    "Sieradz": (-7, -12, "right"), "Sosnowiec": (8, -12, "left"), "Jastrzebie-Zdroj": (-7, -12, "right"),
}
STATION_LABEL_POS = {"Warszawa": (9, 4, "left"), "Kielce": (9, 4, "left"), "Opole": (-10, -24, "right")}
# Bend for cables that would otherwise lie on top of each other (arc3 style, + bends right of travel)
BEND = {("Wodzislaw Slaski", "Kielce"): 0.25, ("Sosnowiec", "Kielce"): 0.12, ("Katowice", "Kielce"): -0.07}
# Capacity label: where along the cable (0 = from, 1 = to) and offset in points; default middle, no offset
LABEL_AT = {
    ("Lodz", "Warszawa"): (0.35, 0, 0), ("Lodz", "Kielce"): (0.6, 0, 0), ("Poznan", "Kielce"): (0.3, 0, 0),
    ("Czestochowa", "Warszawa"): (0.25, 0, 0), ("Katowice", "Kielce"): (0.4, 0, 0),
    ("Sosnowiec", "Kielce"): (0.65, 0, 0), ("Katowice", "Bytom"): (0.5, -22, 12),
    ("Katowice", "Sosnowiec"): (0.5, 10, -20), ("Lodz", "Sieradz"): (0.25, 0, 0),
}

with open(HERE.parent.parent / "distances.csv", encoding="utf-8") as f:
    coord = {r["city"]: (float(r["x"]), float(r["y"])) for r in csv.DictReader(f)}
with open(HERE.parent.parent / "task c" / "main_line_solution.csv", encoding="utf-8") as f:
    route = [r["city"] for r in csv.DictReader(f)]
with open(HERE / "connections_solution.csv", encoding="utf-8") as f:
    cables = [(r["from"], r["to"], float(r["capacity_tbps"]), float(r["cost_eur"])) for r in csv.DictReader(f)]
load = {s: sum(cap for _, j, cap, _ in cables if j == s) for s in STATIONS}
off_line = {i for i, *_ in cables}

fig, ax = plt.subplots(figsize=(11, 8.5), facecolor=SURFACE)
ax.set_facecolor(SURFACE)

# Main line in the background: solid = new, dashed = existing
for i, j in zip(route, route[1:]):
    (x0, y0), (x1, y1) = coord[i], coord[j]
    ax.plot([x0, x1], [y0, y1], color=AXIS, lw=2.5, ls="--" if (i, j) in EXISTING else "-", zorder=1)



def along(i, j, t):
    """Point at fraction t of the cable i -> j (quadratic Bezier, straight when not in BEND)."""
    (x0, y0), (x1, y1) = coord[i], coord[j]
    b = BEND.get((i, j), 0)
    cx, cy = (x0 + x1) / 2 + b * (y1 - y0), (y0 + y1) / 2 - b * (x1 - x0)
    return ((1 - t) ** 2 * x0 + 2 * t * (1 - t) * cx + t ** 2 * x1,
            (1 - t) ** 2 * y0 + 2 * t * (1 - t) * cy + t ** 2 * y1)


# Connection cables: color = switching station, dotted = relay to another city, width ~ capacity
for i, j, cap, _ in cables:
    color = STATION_COLOR.get(j, INK)
    xs, ys = zip(*(along(i, j, k / 40) for k in range(41)))
    ax.plot(xs, ys, color=color, lw=0.8 + 2.4 * cap / 200, ls="-" if j in STATIONS else ":",
            solid_capstyle="round", zorder=2)
    ax.annotate("", xy=along(i, j, 0.8), xytext=along(i, j, 0.7),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=0, mutation_scale=12), zorder=3)
    t, dx, dy = LABEL_AT.get((i, j), (0.5, 0, 0))
    ax.annotate(f"{cap:.1f}", along(i, j, t), xytext=(dx, dy), textcoords="offset points", fontsize=7,
                color=INK, ha="center", va="center", zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec=color, lw=0.8),
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8) if dx or dy else None)

# Cities: squares = switching stations, hollow = connected here, small grey = on the main line
for c, (x, y) in coord.items():
    if c in STATIONS:
        ax.scatter(x, y, s=170, marker="s", zorder=4, facecolor=STATION_COLOR[c], edgecolor=SURFACE, linewidths=2)
        cap = UNIT_CAP * STATIONS[c]
        dx, dy, ha = STATION_LABEL_POS[c]
        ax.annotate(f"{c}\n{load[c]:.0f} / {cap} TB/s ({load[c] / cap:.0%})", (x, y), xytext=(dx, dy),
                    textcoords="offset points", ha=ha, fontsize=8.5, fontweight="bold", color=INK, zorder=7)
        continue
    on = c not in off_line
    ax.scatter(x, y, s=40 if on else 80, zorder=4, linewidths=1.6,
               facecolor=AXIS if on else SURFACE, edgecolor=SURFACE if on else INK_2)
    dx, dy, ha = LABEL_POS.get(c, (6, 5, "left"))
    ax.annotate(c, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=8.5, zorder=5,
                color=INK if not on else MUTED)

ax.set_aspect("equal")
ax.margins(0.08)
ax.grid(color=GRID, lw=0.6, zorder=0)
for s in ax.spines.values():
    s.set_color(AXIS)
ax.tick_params(colors=MUTED, labelsize=8)
ax.set_xlabel("x (coordinate units)", color=INK_2)
ax.set_ylabel("y (coordinate units)", color=INK_2)
ax.set_title(f"Cities connected to switching stations: total cost {sum(c for *_, c in cables):,.0f} EUR"
             " (labels: capacity in TB/s)", color=INK, loc="left")

handles = [Line2D([], [], color=STATION_COLOR[s], lw=2.5, label=f"Cable to {s}") for s in STATIONS]
handles += [
    Line2D([], [], color=INK, lw=2, ls=":", label="Cable to another city (relay)"),
    Line2D([], [], color=AXIS, lw=2.5, label="Main line (task c)"),
    Line2D([], [], color=AXIS, lw=2.5, ls="--", label="Main line, existing cable"),
    Line2D([], [], ls="", marker="s", ms=10, color=INK_2, label="Switching station"),
    Line2D([], [], ls="", marker="o", ms=9, mfc=SURFACE, mec=INK_2, mew=1.6, label="City connected here"),
    Line2D([], [], ls="", marker="o", ms=7, color=AXIS, label="City on main line"),
]
ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8.5, labelcolor=INK_2)

fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor=SURFACE)
print(f"Saved {OUT.name}")
