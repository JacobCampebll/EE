#!/usr/bin/env python3
"""Merge pods.json (pod definitions + pod price tables) into data.json and re-inline DATA
in index.html.

Splices only the DATA object by brace matching, the way merge_geo.py does -- it never
rewrites the rest of index.html. Run again after pod price tables are generated from the
KYTC AUBP source; the definitions and the tables live in the same file.

  python3 merge_pods.py
"""
import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(HERE, "data.json")
INDEX = os.path.join(HERE, "index.html")
PODS = os.path.join(HERE, "pods.json")

data = json.load(open(DATA_JSON))
pods = json.load(open(PODS))

defs = pods.get("pods") or {}
tables = pods.get("pod") or {}
if not defs:
    raise SystemExit("refusing to run: pods.json has no pod definitions")

# A county in two pods would make localPrice() order-dependent on object key order.
seen = {}
for pid, spec in defs.items():
    for c in spec.get("counties") or []:
        if c in seen:
            raise SystemExit(f"refusing to run: {c} is in both {seen[c]} and {pid}")
        seen[c] = pid

# Every pod county should be one the app can map to a district, or the fall-through breaks.
ctd = (data.get("geo") or {}).get("county_to_district") or {}
unknown = sorted(c for c in seen if c not in ctd)
if unknown:
    raise SystemExit(f"refusing to run: not in county_to_district: {', '.join(unknown)}")

geo = data.setdefault("geo", {})
geo["pods"] = defs
geo.setdefault("pod", {}).update(tables)
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

cells = sum(len(v) for v in geo["pod"].values())
print(f"pods: {len(defs)} ({', '.join(defs)}); counties: {len(seen)}; price cells: {cells}")
if not cells:
    print("note: no pod price tables yet -- the tier will fall through to district until "
          "tables are built from the KYTC AUBP source.")
