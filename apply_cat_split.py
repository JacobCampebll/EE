#!/usr/bin/env python3
"""Apply GD / SMALL / RECON work-type split to index.html + data.json."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
DATA = os.path.join(HERE, "data.json")

ACC = {
  "PAVE":   {"n": 358, "mae": 8.9,  "median": 6.2,  "bias": -0.3,  "w5": 146, "w10": 247},
  "ALT":    {"n": 79,  "mae": 8.8,  "median": 7.6,  "bias": -5.4,  "w5": 28,  "w10": 47},
  "GD":     {"n": 55,  "mae": 15.9, "median": 13.7, "bias": -12.9, "w5": 10,  "w10": 22},
  "SMALL":  {"n": 54,  "mae": 16.6, "median": 13.9, "bias": -16.2, "w5": 5,   "w10": 18},
  "BRIDGE": {"n": 64,  "mae": 44.8, "median": 19.6, "bias": 21.3,  "w5": 8,   "w10": 18},
  # RECON measured from bid_backtest_v7 (work_type = RECONSTRUCTION / GRADE-DRAIN-SURFACE
  # W/ STRUCTURES), not copied from BRIDGE. n=10 is thin, so confOf still rates it LOW on
  # sample size -- but the band and bias must be its own. Reconstruction predicts BETTER
  # than grade-and-drain (mae 14.0 vs 15.9, median 5.2), so shipping bridge's 44.8 / +21.3
  # would have over-corrected these jobs down ~9 points and mislabelled the range.
  "RECON":  {"n": 10,  "mae": 14.0, "median": 5.2,  "bias": 12.5,  "w5": 5,   "w10": 7},
}

def must_replace(s, old, new, label):
    if old not in s:
        if new in s:
            print("ok already:", label)
            return s
        raise SystemExit("refusing: missing snippet " + label)
    return s.replace(old, new, 1)

def splice_dropdown(html):
    if 'value="SMALL"' in html:
        print("ok already: dropdown")
        return html
    needle = '<option value="ALT">Alternates (micro vs thinlay)</option>'
    insert = (
        '<option value="SMALL">Guardrail / signing</option>\n'
        '        <option value="RECON">Reconstruction w/ structures</option>\n'
        '        <option value="ALT">Alternates (micro vs thinlay)</option>'
    )
    return must_replace(html, needle, insert, "dropdown")

def main():
    html = open(INDEX).read()
    html = splice_dropdown(html)
    html = must_replace(
        html,
        '  const acc = DATA.meta.accuracy[cat] || DATA.meta.accuracy.GD;',
        '  const acc = DATA.meta.accuracy[cat] || (cat === "RECON" ? DATA.meta.accuracy.BRIDGE : DATA.meta.accuracy.GD);',
        "acc lookup",
    )
    html = must_replace(
        html,
        '    const lr = DATA.ls_ratios[code];\n    if (it.unit === "LS" && lr && lr[cat] != null){\n      matched++;\n      if (!lsCounted[code]){ lsCounted[code] = true; ratioPct += lr[cat];\n        rows.push({ line: it.line, code, desc, qty, unitName: it.unit, unit: null, ext: null, src: "ls", pct: lr[cat] }); }',
        '    const lr = DATA.ls_ratios[code];\n    const lsKey = (cat === "RECON") ? "BRIDGE" : cat;\n    if (it.unit === "LS" && lr && lr[lsKey] != null){\n      matched++;\n      if (!lsCounted[code]){ lsCounted[code] = true; ratioPct += lr[lsKey];\n        rows.push({ line: it.line, code, desc, qty, unitName: it.unit, unit: null, ext: null, src: "ls", pct: lr[lsKey] }); }',
        "ls key",
    )
    html = must_replace(
        html,
        '  if (cat === "BRIDGE") return ["c-low","LOW"];',
        '  if (cat === "BRIDGE" || cat === "RECON") return ["c-low","LOW"];',
        "confOf",
    )
    old_sug = '  let asph = 0, earth = 0, br = 0, alt = 0;'
    new_sug = '  let asph = 0, earth = 0, br = 0, alt = 0, rail = 0, sign = 0;'
    html = must_replace(html, old_sug, new_sug, "suggest locals")
    old_loop_end = '    if (/^08/.test(c) || /BRIDGE|STRUCTURAL STEEL|REMOVE EXISTING DECK|GIRDER|ELASTOMERIC/.test(d)) br++;\n  }'
    new_loop_end = (
        '    if (/^08/.test(c) || /BRIDGE|STRUCTURAL STEEL|REMOVE EXISTING DECK|GIRDER|ELASTOMERIC/.test(d)) br++;\n'
        '    if (/^023(51|53|60|63|65|67|69|71|73|75|81|83|87|91|92|93)/.test(c) || /GUARDRAIL/.test(d)) rail++;\n'
        '    if (/^064/.test(c) || /SHEET SIGN|SIGN POST|DELINEATOR|MILE POST/.test(d)) sign++;\n'
        '  }'
    )
    html = must_replace(html, old_loop_end, new_loop_end, "suggest counts")
    old_dec = (
        '  if (alt >= 3) return { cat: "ALT", why: "item text looks like micro/thinlay alternates" };\n'
        '  if (br >= 6 && asph < 200) return { cat: "BRIDGE", why: "many structure / bridge bid codes" };'
    )
    new_dec = (
        '  if (alt >= 3) return { cat: "ALT", why: "item text looks like micro/thinlay alternates" };\n'
        '  if ((rail + sign) >= 6 && earth < 1000 && br < 6) return { cat: "SMALL", why: "guardrail / signing package" };\n'
        '  if (br >= 6 && earth > 3000) return { cat: "RECON", why: "structures plus earthwork \u2014 own calibration, n=10" };\n'
        '  if (br >= 6 && asph < 200) return { cat: "BRIDGE", why: "many structure / bridge bid codes" };'
    )
    html = must_replace(html, old_dec, new_dec, "suggest decisions")
    open(INDEX, "w").write(html)
    print("wrote index.html engine/UI")

    data = json.load(open(DATA))
    data["meta"]["accuracy"] = ACC
    for rec in data.get("ls_ratios", {}).values():
        if "GD" in rec:
            rec.setdefault("SMALL", rec["GD"])
        if "BRIDGE" in rec:
            rec.setdefault("RECON", rec["BRIDGE"])
    open(DATA, "w").write(json.dumps(data, separators=(",", ":")))

    html = open(INDEX).read()
    start = html.find("const DATA = ")
    if start < 0:
        raise SystemExit("no DATA in index.html")
    i = start + len("const DATA = ")
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
    inline = json.loads(html[i:end])
    inline["meta"]["accuracy"] = ACC
    for rec in inline.get("ls_ratios", {}).values():
        if "GD" in rec:
            rec.setdefault("SMALL", rec["GD"])
        if "BRIDGE" in rec:
            rec.setdefault("RECON", rec["BRIDGE"])
    open(INDEX, "w").write(html[:i] + json.dumps(inline, separators=(",", ":")) + html[end:])
    print("accuracy GD", ACC["GD"]["bias"], "SMALL", ACC["SMALL"]["bias"])
    print("done")

if __name__ == "__main__":
    main()
