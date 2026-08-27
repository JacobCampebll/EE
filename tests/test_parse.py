#!/usr/bin/env python3
"""Layout fixtures from August 2026 proposals. Quantities are public bid items,
not Engineer's Estimates — do not add EE/bid/award dollars here."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UNITS = ["TON","SQYD","CUYD","SQFT","MGAL","EACH","DOLL","MILE","HOUR","MONT","CUFT","GAL","LS","LF","LB","SF"]
U = "|".join(UNITS)
FULL = re.compile(rf"^(\d{{4}})\s+([0-9A-Z]{{5,12}})\s+(.*?)\s+([\d,]+\.?\d*)\s+({U})\b(.*)$")
CONT = re.compile(rf"^(.*?)\s+([\d,]+\.?\d*)\s+({U})\b(.*)$")
HEAD = re.compile(r"^(\d{4})\s+([0-9A-Z]{5,12})\s*(.*)$")

def parse_bid_items(lines):
    out, pending, section = [], None, None
    has_pbi = any(re.search(r"PROPOSAL BID ITEMS", l, re.I) for l in lines)
    in_pbi = not has_pbi
    def push(line, code, desc, qty, unit, tail):
        q = float(str(qty).replace(",", ""))
        desc = re.sub(r"\s+", " ", desc).replace("$", "").strip()
        if not desc:
            return
        if code.isdigit():
            code = code.zfill(5)
        out.append({"line": line, "code": code, "desc": desc, "qty": q, "unit": unit, "section": section})
    for raw in lines:
        ln = raw.replace("\xa0", " ").strip()
        if not ln:
            continue
        if re.search(r"PROPOSAL BID ITEMS", ln, re.I):
            in_pbi, pending = True, None
            continue
        if re.search(r"MATERIAL SUMMARY", ln, re.I):
            in_pbi, pending = False, None
            continue
        if not in_pbi:
            continue
        if re.match(r"^(Report Date|Page \d|LINE BID CODE|Contract ID|ADDENDUM)", ln, re.I):
            continue
        sec = re.match(r"^Section:\s*(\S+)\s*-?\s*(.*)$", ln, re.I)
        if sec:
            section = (sec.group(1) + " " + (sec.group(2) or "")).strip()
            pending = None
            continue
        m = FULL.match(ln)
        if m:
            pending = None
            push(*m.groups())
            continue
        if pending:
            m = CONT.match(ln)
            if m:
                push(pending["line"], pending["code"], pending["desc"] + " " + m.group(1),
                     m.group(2), m.group(3), m.group(4))
                pending = None
                continue
            pending["desc"] += " " + ln
            continue
        m = HEAD.match(ln)
        if m and not re.match(r"^\d{4}\s+\d{4}\b", ln):
            pending = {"line": m.group(1), "code": m.group(2), "desc": m.group(3) or ""}
    by = {i["line"]: i for i in out}
    return [by[k] for k in sorted(by)]

EXPECT = {
    "clark-262155.pbi.txt": {"n": 31, "ls": {"02650": 2, "02676": 2, "02569": 1}, "q": {"00301": 2390.0, "00190": 655.0}},
    "jackson-263024.pbi.txt": {"n": 14, "ls": {"02650": 2, "02676": 2, "02569": 1}, "q": {"00301": 1820.0, "00190": 362.0}},
    "lincoln-262234.pbi.txt": {"n": 32, "ls": {"02650": 2, "02676": 2, "02569": 1}, "q": {"00301": 1400.0, "00388": 4300.0}},
}

def main():
    failed = 0
    for fname, exp in EXPECT.items():
        items = parse_bid_items((ROOT / "fixtures" / fname).read_text().splitlines())
        ok = len(items) == exp["n"]
        for code, n in exp["ls"].items():
            got = sum(1 for i in items if i["code"] == code)
            if got != n:
                ok = False
                print(f"FAIL {fname} {code} count {got} != {n}")
        for code, q in exp["q"].items():
            got = sum(i["qty"] for i in items if i["code"] == code)
            if got != q:
                ok = False
                print(f"FAIL {fname} {code} qty {got} != {q}")
        if not any(i["section"] and "DEMOBILIZATION" in i["section"].upper() for i in items):
            ok = False
            print(f"FAIL {fname} demob section not tagged")
        print(("OK  " if ok else "FAIL") + f" {fname} {len(items)} items")
        failed += not ok
    sys.exit(failed)

if __name__ == "__main__":
    main()
