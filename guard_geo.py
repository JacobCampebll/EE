#!/usr/bin/env python3
"""Apply the pod build's sanity guard to the district price tables, then re-inline DATA.

The pod tables reject a cell whose median is below $0.05 or outside 0.25x-4x the
statewide average. The district tables were built from a different source
(UBER_AUBP_Data 20250610) and never had that guard, so they still carry penny bids
and wild outliers -- D11 06510 at $0.01 against $0.14 statewide, D11 02677 at $95.00
against $20.73. A dropped cell is not a hole: the cascade falls through to the
statewide row, which is a better number than a penny bid in every case here.

Drops cells, never rewrites values, and never touches the pod tables. Splices only the
DATA object in index.html by brace matching, the way merge_pods.py does.

  python3 guard_geo.py            # report and write
  python3 guard_geo.py --dry-run  # report only
"""
import json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(HERE, "data.json")
INDEX = os.path.join(HERE, "index.html")

P_FLOOR, LO, HI = 0.05, 0.25, 4.0
DRY = "--dry-run" in sys.argv

data = json.load(open(DATA_JSON))
prices = data["prices"]
geo = data.get("geo") or {}
district = geo.get("district") or {}
if not district:
    raise SystemExit("refusing to run: no district tables in data.json")

# Codes the engine never prices off a table: mobilisation and demobilisation are
# computed as percentages of the subtotal (predict() `continue`s past both), and
# lump-sum ratio codes are priced by ratio whenever their unit is LS.
#
# These are RETAINED even when they fail the guard, deliberately. They fail only
# because they are size-scaling lump sums measured against a statewide weighted
# average drawn from much larger jobs -- D11 02650 at $9,500 against $71,414
# statewide is a plausible district-sized number, not a defect. Dropping them
# would change nothing today, and in the one case where it could ever matter (a
# 02650 line whose unit is not LS, which falls through to unitPrice) the district
# figure is the better of the two. So the guard reports them and leaves them.
INERT = {"02568", "02569"} | set(data.get("ls_ratios") or {})

def verdict(code, cell):
    p = cell.get("p")
    if p is None:
        return "no price"
    if p < P_FLOOR:
        return f"${p:,.2f} below ${P_FLOOR:.2f} floor"
    sa = (prices.get(code) or {}).get("p")
    if sa and not (LO * sa <= p <= HI * sa):
        return f"${p:,.2f} is {p/sa:.2f}x statewide ${sa:,.2f}"
    return None

dropped, kept = [], 0
for dist in sorted(district):
    for code in sorted(district[dist]):
        why = verdict(code, district[dist][code])
        if why:
            dropped.append((dist, code, district[dist][code], why))
        else:
            kept += 1

if not dropped:
    print("nothing to drop: every district cell already passes the guard")
    raise SystemExit(0)

flagged = dropped
dropped = [d for d in flagged if d[1] not in INERT]
retained = [d for d in flagged if d[1] in INERT]
live = dropped
inert = retained

def show(rows, label):
    if not rows:
        return
    print(f"\n{label} ({len(rows)}):")
    for dist, code, cell, why in rows:
        desc = (prices.get(code) or {}).get("d", "")[:34]
        print(f"  D{dist}  {code:10} n={cell['n']:<3} {desc:34}  {why}")

show(live, "DROPPING -- live cells the cascade can reach")
show(inert, "flagged but RETAINED -- size-scaling lump sums the engine never prices off a table")
total = kept + len(flagged)
print(f"\ndistrict cells: {total} -> {total - len(dropped)}   "
      f"({len(flagged)} flagged: {len(dropped)} dropped, {len(retained)} retained)")

if DRY:
    print("\n--dry-run: nothing written")
    raise SystemExit(0)

if not dropped:
    # Only retained (inert) cells are still flagged -- already applied, nothing to do.
    print("\nalready applied: no live cell fails the guard, nothing written")
    raise SystemExit(0)

for dist, code, _cell, _why in dropped:
    del district[dist][code]

data["meta"]["built"] = datetime.date.today().isoformat()
open(DATA_JSON, "w").write(json.dumps(data, separators=(",", ":")))

html = open(INDEX).read()
start = html.find("const DATA = ")
if start < 0:
    raise SystemExit("refusing to run: 'const DATA = ' not found in index.html")
i = start + len("const DATA = ")
if html[i] != "{":
    raise SystemExit("refusing to run: DATA is not an object literal")
depth, end = 0, None
for j in range(i, len(html)):
    if html[j] == "{":
        depth += 1
    elif html[j] == "}":
        depth -= 1
        if depth == 0:
            end = j + 1
            break
if end is None:
    raise SystemExit("refusing to run: unbalanced braces in DATA")

open(INDEX, "w").write(html[:i] + json.dumps(data, separators=(",", ":")) + html[end:])
print("\nwrote data.json and re-inlined DATA in index.html")
