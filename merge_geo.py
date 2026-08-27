#!/usr/bin/env python3
"""Merge geo_district.json into data.json and re-inline DATA in index.html."""
import json, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "data.json")))
geo = json.load(open(os.path.join(HERE, "geo_district.json")))
cur = data.setdefault("geo", {}).setdefault("district", {})
cur.update(geo)
data["geo"]["district"] = cur
data["meta"]["built"] = datetime.date.today().isoformat()
src = data["meta"].get("source", "")
if "AUBP" not in src:
    data["meta"]["source"] = src + "; KYTC UBER_AUBP_Data 20250610 district medians"
open(os.path.join(HERE, "data.json"), "w").write(json.dumps(data, separators=(",", ":")))
html = open(os.path.join(HERE, "index.html")).read()
start = html.find("const DATA = ")
assert start >= 0, "const DATA not found"
i = start + len("const DATA = ")
assert html[i] == "{"
depth = 0
end = None
for j in range(i, len(html)):
    if html[j] == "{":
        depth += 1
    elif html[j] == "}":
        depth -= 1
        if depth == 0:
            end = j + 1
            break
assert end, "unbalanced DATA braces"
s = json.dumps(data, separators=(",", ":"))
open(os.path.join(HERE, "index.html"), "w").write(html[:i] + s + html[end:])
print("merged", sum(len(v) for v in cur.values()), "district-code cells")
