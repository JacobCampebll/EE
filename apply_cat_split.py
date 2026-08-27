#!/usr/bin/env python3
"""Apply GD / SMALL / RECON work-type split to index.html + data.json.

Safe string replacements only. Refuses to run if an expected snippet is missing.
Does not invent LS ratios (SMALL copies GD). RECON copies BRIDGE accuracy.
"""
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
  "RECON":  {"n": 64,  "mae": 44.8, "median": 19.6, "bias": 21.3,  "w5": 8,   "w10": 18},
}

OPTIONS_OLD = """        <option value=\"PAVE\">Resurfacing / paving</option>
        <option value=\"GD\">Grade &amp; drain / new route</option>
        <option value=\"ALT\">Alternates (micro vs thinlay)</option>
        <option value=\"BRIDGE\">Bridge</option>"""
OPTIONS_NEW = """        <option value=\"PAVE\">Resurfacing / paving</option>
        <option value=\"GD\">Grade &amp; drain / new route</option>
        <option value=\"SMALL\">Guardrail / signing</option>
        <option value=\"RECON\">Reconstruction w/ structures</option>
        <option value=\"ALT\">Alternates (micro vs thinlay)</option>
        <option value=\"BRIDGE\">Bridge</option>"""

SUGGEST_OLD = """function suggestCat(items){
  let asph = 0, earth = 0, br = 0, alt = 0;
  for (const it of items){
    const d = (it.desc || \"\").toUpperCase();
    const c = it.code || \"\";
    if (/ALTERNATE|MICROSURFACING|THINLAY/.test(d)) alt++;
    if (/ASPH|PAVE MILLING|DGA BASE|LEVELING & WEDGING/.test(d)) asph += it.qty || 0;
    if (/EXCAVAT|EMBANKMENT|BORROW EXCAVATION/.test(d) || c === \"02200\" || c === \"02230\") earth += it.qty || 0;
    if (/^08/.test(c) || /BRIDGE|STRUCTURAL STEEL|REMOVE EXISTING DECK|GIRDER|ELASTOMERIC/.test(d)) br++;
  }
  if (alt >= 3) return { cat: \"ALT\", why: \"item text looks like micro/thinlay alternates\" };
  if (br >= 6 && asph < 200) return { cat: \"BRIDGE\", why: \"many structure / bridge bid codes\" };
  if (earth > 3000 && earth >= asph) return { cat: \"GD\", why: \"earthwork quantities dominate\" };
  return { cat: \"PAVE\", why: \"asphalt / resurfacing items dominate\" };
}"""

SUGGEST_NEW = """function suggestCat(items){
  let asph = 0, earth = 0, br = 0, alt = 0, rail = 0, sign = 0;
  for (const it of items){
    const d = (it.desc || \"\").toUpperCase();
    const c = it.code || \"\";
    if (/ALTERNATE|MICROSURFACING|THINLAY/.test(d)) alt++;
    if (/ASPH|PAVE MILLING|DGA BASE|LEVELING & WEDGING/.test(d)) asph += it.qty || 0;
    if (/EXCAVAT|EMBANKMENT|BORROW EXCAVATION/.test(d) || c === \"02200\" || c === \"02230\") earth += it.qty || 0;
    if (/^08/.test(c) || /BRIDGE|STRUCTURAL STEEL|REMOVE EXISTING DECK|GIRDER|ELASTOMERIC/.test(d)) br++;
    if (/^023(51|53|60|63|65|67|69|71|73|75|81|83|87|91|92|93)/.test(c) || /GUARDRAIL/.test(d)) rail++;
    if (/^064/.test(c) || /SHEET SIGN|SIGN POST|DELINEATOR|MILE POST/.test(d)) sign++;
  }
  if (alt >= 3) return { cat: \"ALT\", why: \"item text looks like micro/thinlay alternates\" };
  if ((rail + sign) >= 6 && earth < 1000 && br < 6) return { cat: \"SMALL\", why: \"guardrail / signing package\" };
  if (br >= 6 && earth > 3000) return { cat: \"RECON\", why: \"structures plus earthwork — uses bridge calibration\" };
  if (br >= 6 && asph < 200) return { cat: \"BRIDGE\", why: \"many structure / bridge bid codes\" };
  if (earth > 3000 && earth >= asph) return { cat: \"GD\", why: \"earthwork quantities dominate\" };
  return { cat: \"PAVE\", why: \"asphalt / resurfacing items dominate\" };
}"""

def must_replace(s, old, new, label):
    if old not in s:
        if new in s:
            print(f\"ok already: {label}\")
            return s
        sys.exit(f\"refusing: missing snippet {label}\")
    return s.replace(old, new, 1)

def main():
    html = open(INDEX).read()
    if \"value=\\\"SMALL\\\"\" in html and \"rail + sign\" in html:
        print(\"index.html already split\")
    else:
        html = must_replace(html, OPTIONS_OLD, OPTIONS_NEW, \"dropdown\")
        html = must_replace(html,
            '  const acc = DATA.meta.accuracy[cat] || DATA.meta.accuracy.GD;',
            '  const acc = DATA.meta.accuracy[cat] || (cat === \"RECON\" ? DATA.meta.accuracy.BRIDGE : DATA.meta.accuracy.GD);',
            \"acc lookup\")
        html = must_replace(html,
            '    const lr = DATA.ls_ratios[code];\\n    if (it.unit === \"LS\" && lr && lr[cat] != null){\\n      matched++;\\n      if (!lsCounted[code]){ lsCounted[code] = true; ratioPct += lr[cat];\\n        rows.push({ line: it.line, code, desc, qty, unitName: it.unit, unit: null, ext: null, src: \"ls\", pct: lr[cat] }); }',
            '    const lr = DATA.ls_ratios[code];\\n    const lsKey = (cat === \"RECON\") ? \"BRIDGE\" : cat;\\n    if (it.unit === \"LS\" && lr && lr[lsKey] != null){\\n      matched++;\\n      if (!lsCounted[code]){ lsCounted[code] = true; ratioPct += lr[lsKey];\\n        rows.push({ line: it.line, code, desc, qty, unitName: it.unit, unit: null, ext: null, src: \"ls\", pct: lr[lsKey] }); }',
            \"ls key\")
        html = must_replace(html,
            '  if (cat === \"BRIDGE\") return [\"c-low\",\"LOW\"];',
            '  if (cat === \"BRIDGE\" || cat === \"RECON\") return [\"c-low\",\"LOW\"];',
            \"confOf\")
        html = must_replace(html, SUGGEST_OLD, SUGGEST_NEW, \"suggestCat\")
        open(INDEX, \"w\").write(html)
        print(\"wrote index.html engine/UI\")

    data = json.load(open(DATA))
    data[\"meta\"][\"accuracy\"] = ACC
    for rec in data.get(\"ls_ratios\", {}).values():
        if \"GD\" in rec:
            rec.setdefault(\"SMALL\", rec[\"GD\"])
        if \"BRIDGE\" in rec:
            rec.setdefault(\"RECON\", rec[\"BRIDGE\"])
    open(DATA, \"w\").write(json.dumps(data, separators=(\",\", \":\")))

    html = open(INDEX).read()
    start = html.find(\"const DATA = \")
    if start < 0:
        sys.exit(\"no DATA in index.html\")
    i = start + len(\"const DATA = \")
    depth = 0
    end = None
    for j in range(i, len(html)):
        if html[j] == \"{\":
            depth += 1
        elif html[j] == \"}\":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    inline = json.loads(html[i:end])
    inline[\"meta\"][\"accuracy\"] = ACC
    for rec in inline.get(\"ls_ratios\", {}).values():
        if \"GD\" in rec:
            rec.setdefault(\"SMALL\", rec[\"GD\"])
        if \"BRIDGE\" in rec:
            rec.setdefault(\"RECON\", rec[\"BRIDGE\"])
    open(INDEX, \"w\").write(html[:i] + json.dumps(inline, separators=(\",\", \":\")) + html[end:])
    print(\"accuracy\", ACC[\"GD\"][\"bias\"], ACC[\"SMALL\"][\"bias\"])
    print(\"done\")

if __name__ == \"__main__\":
    main()
