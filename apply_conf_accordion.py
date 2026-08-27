#!/usr/bin/env python3
"""Rewrite the Confidence detail card into the accordion layout Jacob picked.

Must-replace guards. Does not touch DATA, prices, or predict().
Run from the EE repo root:

    python3 apply_conf_accordion.py
"""
from pathlib import Path

INDEX = Path("index.html")

CSS_NEEDLE = """  .meter{height:8px;background:var(--panel2);border-radius:5px;overflow:hidden;margin:7px 0 3px}
  .meter>div{height:100%;border-radius:5px}"""

CSS_ADD = """  .meter{height:8px;background:var(--panel2);border-radius:5px;overflow:hidden;margin:7px 0 3px}
  .meter>div{height:100%;border-radius:5px}
  .confbox{border:1px solid var(--accent);border-radius:12px;padding:4px 14px 8px;margin:2px 0 12px}
  .confbox .kv{padding:9px 0}
  .confico{width:18px;height:18px;flex:0 0 18px;stroke:var(--accent);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
  .kv.ico{align-items:center}
  .kv.ico span:first-child{display:flex;align-items:center;gap:8px;color:var(--text)}
  .acc{border:1px solid var(--line);border-radius:10px;margin:8px 0 0;background:var(--panel);overflow:hidden}
  .acc+ .acc{margin-top:8px}
  .acc>summary{list-style:none;cursor:pointer;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;gap:12px}
  .acc>summary::-webkit-details-marker,.acc>summary::marker{display:none}
  .acc .sum-l{display:flex;flex-direction:column;gap:2px;min-width:0}
  .acc .sum-l b{font-size:.92rem}
  .acc .sum-l em{color:var(--muted);font-style:normal;font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .acc .chev{color:var(--muted);font-size:.7rem;transition:transform .15s}
  .acc[open]>summary .chev{transform:rotate(180deg)}
  .acc .acc-body{padding:0 14px 8px;border-top:1px solid var(--panel2)}"""

OLD_PANEL = """    <div class=\"panel\">
      <h2>Confidence detail</h2>
      <div class=\"kv\"><span>Items priced</span><b>${r.matched} / ${r.work}</b></div>
      <div class=\"meter\"><div style=\"width:${(r.itemCov*100).toFixed(0)}%;background:var(--accent)\"></div></div>
      <div class=\"kv\" style=\"margin-top:10px\"><span>Track record — ${r.cat}</span><b>${r.acc.n} jobs</b></div>
      <div class=\"kv\"><span>Mean error (raw basis)</span><b>${r.acc.mae.toFixed(1)}%</b></div>
      <div class=\"kv\"><span>Median error</span><b>${r.acc.median.toFixed(1)}%</b></div>
      <div class=\"kv\"><span>Within ±5% / ±10%</span><b>${w5}% / ${w10}% of jobs</b></div>
      <div class=\"kv\"><span>Measured bias</span><b>${r.biasApplied ? \"applied\" : \"skipped\"} (${r.acc.bias > 0 ? \"+\" : \"\"}${r.acc.bias.toFixed(1)}%)</b></div>
      <div class=\"kv\"><span>Local price share</span><b>${locPct}% (${sc.county} co / ${sc.pod||0} pod / ${sc.district} dist / ${sc.state} state)</b></div>
      <div class=\"kv\"><span>County / district</span><b>${r.county ? (r.county+\" · D\"+r.district) : \"statewide (no county)\"}</b></div>
      <div class=\"kv\"><span>Letting month</span><b>${r.letKey}</b></div>
      <div class=\"kv\"><span>Binder index (KAPI)</span><b>$${kapiAt(r.letKey).v.toFixed(2)}/ton${kapiAt(r.letKey).est ? \" *\" : \"\"}</b></div>
      ${kapiAt(r.letKey).est ? `<div class=\"note\"><b>* Binder index carried forward.</b> KYTC has published
        KAPI through ${KAPI_LAST}; this letting is later, so the last published value is used. Re-download the
        Fuel & Asphalt spreadsheet and rebuild data.json when a newer month posts.</div>` : ``}
    </div>"""

NEW_PANEL = r"""    <div class=\"panel\">
      <h2>Confidence detail</h2>
      <div class=\"confbox\">
        <div class=\"kv ico\"><span><svg class=\"confico\" viewBox=\"0 0 24 24\"><path d=\"M6 7h15l-1.4 8.2A2 2 0 0 1 17.6 17H8.4A2 2 0 0 1 6.5 15.2L4 4H2\"/><circle cx=\"9\" cy=\"20\" r=\"1.2\"/><circle cx=\"17\" cy=\"20\" r=\"1.2\"/></svg>Items priced</span><b>${r.matched} / ${r.work}</b></div>
        <div class=\"meter\"><div style=\"width:${(r.itemCov*100).toFixed(0)}%;background:var(--accent)\"></div></div>
        <div class=\"kv ico\"><span><svg class=\"confico\" viewBox=\"0 0 24 24\"><path d=\"M12 21s7-4.4 7-11a7 7 0 1 0-14 0c0 6.6 7 11 7 11z\"/><circle cx=\"12\" cy=\"10\" r=\"2.2\"/></svg>Local share</span><b>${locPct}% — bias ${r.biasApplied ? \"applied\" : \"skipped\"}</b></div>
        <div class=\"kv ico\"><span><svg class=\"confico\" viewBox=\"0 0 24 24\"><path d=\"M12 3l7 3v6c0 5-3.2 8.2-7 9.5C8.2 20.2 5 17 5 12V6z\"/></svg>Confidence</span><b><span class=\"conf ${cls}\">${lbl}</span></b></div>
        <div class=\"kv ico\"><span><svg class=\"confico\" viewBox=\"0 0 24 24\"><path d=\"M4 19V9m6 10V5m6 14v-7m6 7V8\"/></svg>Mean error on ${r.cat}</span><b>${r.acc.mae.toFixed(1)}% (${r.acc.n} jobs)</b></div>
      </div>
      <details class=\"acc\">
        <summary><span class=\"sum-l\"><b>Track record details</b><em>median, ±5 / ±10, measured bias, source mix</em></span><span class=\"chev\">▾</span></summary>
        <div class=\"acc-body\">
          <div class=\"kv\"><span>Median error</span><b>${r.acc.median.toFixed(1)}%</b></div>
          <div class=\"kv\"><span>Within ±5% / ±10%</span><b>${w5}% / ${w10}% of jobs</b></div>
          <div class=\"kv\"><span>Measured bias</span><b>${r.biasApplied ? \"applied\" : \"skipped\"} (${r.acc.bias > 0 ? \"+\" : \"\"}${r.acc.bias.toFixed(1)}%)</b></div>
          <div class=\"kv\"><span>Source mix</span><b>${sc.county} co / ${sc.pod||0} pod / ${sc.district} dist / ${sc.state} state</b></div>
        </div>
      </details>
      <details class=\"acc\">
        <summary><span class=\"sum-l\"><b>Job inputs</b><em>${r.county ? (r.county+\" · D\"+r.district) : \"statewide\"}, letting ${r.letKey}, KAPI $${kapiAt(r.letKey).v.toFixed(2)}</em></span><span class=\"chev\">▾</span></summary>
        <div class=\"acc-body\">
          <div class=\"kv\"><span>County / district</span><b>${r.county ? (r.county+\" · D\"+r.district) : \"statewide (no county)\"}</b></div>
          <div class=\"kv\"><span>Letting month</span><b>${r.letKey}</b></div>
          <div class=\"kv\"><span>Binder index (KAPI)</span><b>$${kapiAt(r.letKey).v.toFixed(2)}/ton${kapiAt(r.letKey).est ? \" *\" : \"\"}</b></div>
          ${kapiAt(r.letKey).est ? `<div class=\"note\"><b>* Binder index carried forward.</b> KYTC has published
        KAPI through ${KAPI_LAST}; this letting is later, so the last published value is used. Re-download the
        Fuel & Asphalt spreadsheet and rebuild data.json when a newer month posts.</div>` : ``}
        </div>
      </details>
    </div>"""


def must_replace(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


def main():
    html = INDEX.read_text()
    if "class=\"confbox\"" in html or "Track record details" in html:
        print("already applied")
        return
    html = must_replace(html, CSS_NEEDLE, CSS_ADD, "css")
    html = must_replace(html, OLD_PANEL, NEW_PANEL, "panel")
    INDEX.write_text(html)
    print("wrote accordion Confidence detail card")


if __name__ == "__main__":
    main()
