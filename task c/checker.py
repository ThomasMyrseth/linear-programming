"""Independent checker for the task c main line, written from the case text only (not from the model)."""
import csv
import math
import sys
from itertools import permutations, product
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "distances.csv"
SOLUTION = HERE / "main_line_solution.csv"

START, END = "Warszawa", "Jelenia Gora"
# Read as legs in the direction of the line (Warszawa -> Jelenia Gora): Radom then Kielce, Gliwice then Opole.
EXISTING = [("Radom", "Kielce"), ("Gliwice", "Opole")]
# (area, first city, last city, other cities). "Two/three more cities" read literally as exactly that many.
AREAS = [(1, "Warszawa", "Radom", 2), (2, "Kielce", "Gliwice", 3), (3, "Opole", "Jelenia Gora", 3)]
AT_LEAST_ONE = [("Konin", "Kalisz"), ("Poznan", "Zielona Gora", "Leszno")]
AT_MOST_ONE = [("Bytom", "Sosnowiec", "Katowice"), ("Wodzislaw Slaski", "Jastrzebie-Zdroj")]
# Appendix 2 typed in by hand, so a typo in distances.csv is caught instead of shared with the model.
CASE_TABLE = {
    "Warszawa": (1, 100, 65), "Skierniewice": (1, 92, 62), "Lodz": (1, 85, 58), "Konin": (1, 68, 64),
    "Sieradz": (1, 72, 55), "Piotrkow": (1, 89, 51), "Radom": (1, 102, 50),
    "Kielce": (2, 98, 42), "Czestochowa": (2, 79, 40), "Bytom": (2, 76, 31), "Gliwice": (2, 73, 30),
    "Sosnowiec": (2, 80, 29), "Krakow": (2, 89, 25), "Bielsko": (2, 79, 20), "Katowice": (2, 78, 28),
    "Jastrzebie-Zdroj": (2, 74, 23), "Wodzislaw Slaski": (2, 71, 23),
    "Poznan": (3, 54, 68), "Zielona Gora": (3, 39, 60), "Leszno": (3, 51, 58), "Kalisz": (3, 65, 58),
    "Legnica": (3, 45, 47), "Wroclaw": (3, 54, 45), "Jelenia Gora": (3, 40, 42), "Walbrzych": (3, 46, 39),
    "Opole": (3, 67, 37),
}


def length(route, xy):
    return sum(math.dist(xy[a], xy[b]) for a, b in zip(route, route[1:]))


def route_checks(route, area):
    legs = list(zip(route, route[1:]))
    areas = [area[c] for c in route]
    checks = [
        (f"starts in {START}", route[0] == START),
        (f"ends in {END}", route[-1] == END),
        ("no city visited twice", len(set(route)) == len(route)),
    ]
    checks += [(f"uses existing {a}-{b} link as a leg", (a, b) in legs) for a, b in EXISTING]
    checks += [
        ("areas visited in order 1 -> 2 -> 3", areas == sorted(areas)),
        # Literal reading: new cable is laid inside one area; only the existing links cross area borders.
        ("only the existing links cross area borders",
         sorted(leg for leg in legs if area[leg[0]] != area[leg[1]]) == sorted(EXISTING)),
    ]
    for a, first, last, extra in AREAS:
        block = [c for c in route if area[c] == a]
        checks.append((f"area {a} starts in {first} and ends in {last}", block[:1] == [first] and block[-1:] == [last]))
        checks.append((f"area {a} has exactly {extra} cities besides {first} and {last}",
                       len([c for c in block if c not in (first, last)]) == extra))
    checks.append(("no pair of cities connected more than once (A->B and B->A)",
                   len({frozenset(leg) for leg in legs}) == len(legs)))
    checks += [(f"at least one of {', '.join(g)}", any(c in route for c in g)) for g in AT_LEAST_ONE]
    checks += [(f"at most one of {', '.join(g)}", sum(c in route for c in g) <= 1) for g in AT_MOST_ONE]
    return checks


def shortest_feasible(area, xy):
    # Side constraints only ask which cities are used, so per area keep the shortest order of each city set.
    blocks = []
    for a, first, last, extra in AREAS:
        others = [c for c in area if area[c] == a and c not in (first, last)]
        best = {}
        for mid in permutations(others, extra):
            seg = [first, *mid, last]
            if frozenset(mid) not in best or length(seg, xy) < length(best[frozenset(mid)], xy):
                best[frozenset(mid)] = seg
        blocks.append(list(best.values()))
    routes = (b1 + b2 + b3 for b1, b2, b3 in product(*blocks))
    feasible = (r for r in routes if all(ok for _, ok in route_checks(r, area)))
    return min(feasible, key=lambda r: length(r, xy))


def main():
    with open(DATA, newline="") as f:
        rows = list(csv.DictReader(f))
    area = {r["city"]: int(r["area"]) for r in rows}
    xy = {r["city"]: (float(r["x"]), float(r["y"])) for r in rows}
    with open(SOLUTION, newline="") as f:
        sol = sorted(csv.DictReader(f), key=lambda r: int(r["order"]))
    route = [r["city"].strip() for r in sol]

    unknown = [c for c in route if c not in area]
    checks = [
        ("distances.csv matches the case table (area, x, y)", {c: (area[c], *xy[c]) for c in area} == CASE_TABLE),
        ("order column runs 1..n without gaps", [int(r["order"]) for r in sol] == list(range(1, len(sol) + 1))),
        ("every city is in the case data", not unknown),
    ]
    if unknown:
        print("Unknown cities:", ", ".join(unknown))
    else:
        checks += route_checks(route, area)
        best = shortest_feasible(area, xy)
        checks.append(("length is minimal among all routes passing the checks above",
                       length(route, xy) <= length(best, xy) + 1e-6))

    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    if not unknown:
        legs = list(zip(route, route[1:]))
        existing = {frozenset(e) for e in EXISTING}
        old = sum(math.dist(xy[a], xy[b]) for a, b in legs if frozenset((a, b)) in existing)
        total = length(route, xy)
        print()
        print("Main line:", " -> ".join(route))
        print(f"Total length:    {total:.4f}")
        print(f"  existing cable: {old:.4f}")
        print(f"  new cable:      {total - old:.4f}")
        print(f"Checker optimum: {length(best, xy):.4f}  ({' -> '.join(best)})")

    failed = sum(not ok for _, ok in checks)
    print()
    print(f"{len(checks) - failed}/{len(checks)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
