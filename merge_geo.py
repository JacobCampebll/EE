#!/usr/bin/env python3
"""Merge geo_district.json into data.json and re-inline DATA in index.html."""
import json, re, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "data.json"))
geo = json.load(open(os.path.join(HERE, "geo_district.json"))
# preserve any existing district keys, overlay file
cur = data.setdefault("geo", {}).setdefault("district", {})
cur.update(geo)
data["geo"]["district"] = cur
data["meta"]["built"] = datetime.date.today().isoformat()
src = data["meta"].get("source", "")
if "AUBP" not in src:
    data["meta"]["source"] = src + "; KYTC UBER_AUBP_Data 20250610 district medians"
open(os.path.join(HERE, "data.json"), "w").write(json.dumps(data, separators=(",", ":")))
html = open(os.path.join(HERE, "index.html")).read()
m = re.search(r"const DATA = (\{.*?\n\});\n\n/\* ===", html, re.S)
if not m:
    m = re.search(r"const DATA = (\{.*?\});\s*\n", html, re.S)
assert m, "DATA block not found in index.html"
s = json.dumps(data, separators=(",", ":"))
open(os.path.join(HERE, "index.html"), "w").write(html[:m.start(1)] + s + html[m.end(1):])
print("merged", sum(len(v) for v in cur.values()), "district-code cells")
