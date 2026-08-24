#!/usr/bin/env python3
"""Apply geo_district.json + calibration-gate engine tail to data.json / index.html."""
import json, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
TAIL_PATH = os.path.join(HERE, "index_engine_tail.js.txt")
assert os.path.exists(TAIL_PATH), "missing index_engine_tail.js.txt"
assert os.path.exists(os.path.join(HERE, "geo_district.json")), "missing geo_district.json"

# Guard added by Claude 2026-08-24, checked BEFORE any write. This script
# REPLACES everything after "const DATA = " with the contents of TAIL_PATH. The
# committed index_engine_tail.js.txt is a placeholder saying the real tail lives
# only in a local working tree, so running this on a fresh clone truncates
# index.html from ~200 KB to a comment block. Checked up front so a refusal
# leaves data.json and index.html both untouched -- aborting mid-run desyncs them.
TAIL = open(TAIL_PATH).read()
if "function predict(" not in TAIL or len(TAIL) < 5000:
    raise SystemExit(
        f"refusing to run: {os.path.basename(TAIL_PATH)} is {len(TAIL)} bytes and has no "
        "engine code in it -- it is the placeholder, not the real tail. Running would "
        "truncate index.html to prefix + DATA + this stub. Restore the real tail first."
    )

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
assert start >= 0
i = start + len("const DATA = ")
prefix = html[:i]
tail = TAIL
open(os.path.join(HERE, "index.html"), "w").write(prefix + json.dumps(data, separators=(",", ":")) + tail)
print("applied geo + calibration gate; district cells", sum(len(v) for v in cur.values()))
