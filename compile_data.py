#!/usr/bin/env python3
"""
KYTC EE Predictor — data compiler.
Reads the KYTC statewide average unit price files + the KAPI/OPIS index,
applies the year-fallback rule, and writes a single versioned data.json
for the single-file HTML app.

Re-run this after Cowork loads new lettings, then redeploy the app.
"""
import csv, json, datetime, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_PRICES = "/home/claude/state_avg_all.csv"      # year,bid_code,description,unit,statewide_quantity,avg_price,contract_occurrences
SRC_BINDER = "/home/claude/bidpred/binder_prices.csv"

# ---- engine constants (mirror bid_app_config in Supabase) --------------------
ESC_OTHER = {2023: 1.143, 2024: 0.942, 2025: 1.007, 2026: 1.073}   # non-asphalt YoY chain
ESC_ASPH  = {2023: 1.143, 2024: 0.942, 2025: 1.007, 2026: 1.156}   # asphalt residual chain
RULES = {"mob_cap": 0.05, "demob_floor": 0.015, "qty_min": 0.6, "qty_max": 2.5}

AC = {"ASPH SURF 0.38D": 0.060, "ASPH SURF 0.38B": 0.058,
      "ASPH BASE 1.00D": 0.047, "ASPH BASE 0.75D": 0.050,
      "LEVELING & WEDGING": 0.062}

LS_RATIOS = {
  "02650": {"PAVE": 0.0200, "GD": 0.0648, "ALT": 0.0321, "BRIDGE": 0.0648},
  "02676": {"PAVE": 0.0133, "GD": 0.0043, "ALT": 0.0117, "BRIDGE": 0.0043},
  "02726": {"PAVE": 0.0104, "GD": 0.0129, "ALT": 0.0104, "BRIDGE": 0.0129},
  "02545": {"GD": 0.0155, "BRIDGE": 0.0155},
  "26248EC": {"PAVE": 0.0016, "GD": 0.0009, "ALT": 0.0016, "BRIDGE": 0.0009},
  "26228EC": {"PAVE": 0.0017, "GD": 0.0017, "ALT": 0.0017, "BRIDGE": 0.0017},
}

CURVES_RAW = "00001:-0.148:1595.4,00003:-0.099:11615.5,00078:-0.185:6900.2,00100:-0.462:102.5,00212:-0.184:1944.3,00214:-0.159:5952.2,00301:-0.166:2574.5,00388:-0.135:4045.4,00462:-0.324:234.0,00522:-0.160:1050.5,01310:-0.371:96.5,02200:-0.206:49427.2,02230:-0.261:29514.7,02231:-0.212:546.7,02351:-0.103:1969.5,02381:-0.221:3891.9,02483:-0.114:1073.0,02602:-0.178:17390.7,02696:-0.724:27442.8,02697:-0.706:35299.4,02720:-0.336:997.1,03240:-0.217:608.5,05950:-0.305:10226.3,05985:-0.382:78353.0,06410:-0.141:719.8,06514:-0.271:35924.9,06515:-0.190:58903.5,06542:-0.167:33836.1,06543:-0.190:30278.5,06546:-0.126:1699.7,06547:-0.141:453.9,06556:-0.066:1618.3,06557:-0.061:1704.8,06566:-0.132:944.4,06568:-0.136:168.9,08002:-0.370:143.7,08019:-0.202:1076.5,08151:-0.094:70830.3,20071EC:-0.448:65232.7,20458ES403:-0.632:17358.1,21653ES403:-0.107:2363.2,23071EN:-0.224:10648.5,23378EC:-0.233:27567.3"

ACCURACY = {   # from bid_backtest_v6 (job-level qty curves, LS deduped), 620 projects
  "PAVE":   {"n": 358, "mae": 9.5,  "median": 7.5,  "bias": -7.2,  "w5": 130, "w10": 229},
  "ALT":    {"n": 79,  "mae": 7.7,  "median": 6.6,  "bias": -3.9,  "w5": 30,  "w10": 54},
  "GD":     {"n": 119, "mae": 16.8, "median": 15.1, "bias": -12.5, "w5": 15,  "w10": 35},
  "BRIDGE": {"n": 64,  "mae": 46.2, "median": 18.9, "bias": 32.0,  "w5": 5,   "w10": 11},
}
N_PROJECTS = 620

def ac_for(desc):
    for k, v in AC.items():
        if k in (desc or ""):
            return v
    return None

def main():
    curves = {}
    for part in CURVES_RAW.split(","):
        c, b, q = part.split(":")
        curves[c] = [float(b), float(q)]

    # --- prices: newest year wins, keep the year so the app can escalate ------
    best = {}
    for r in csv.DictReader(open(SRC_PRICES)):
        code, yr = r["bid_code"], int(r["year"])
        try:
            price = float(r["avg_price"]); occ = int(float(r["contract_occurrences"]))
        except (ValueError, TypeError):
            continue
        if price <= 0:
            continue
        if code not in best or yr > best[code]["yr"]:
            best[code] = {"p": round(price, 2), "n": occ, "yr": yr,
                          "d": (r["description"] or "")[:44], "u": r["unit"] or ""}

    prices = {}
    for code, v in best.items():
        e = {"p": v["p"], "n": v["n"], "yr": v["yr"], "d": v["d"], "u": v["u"]}
        a = ac_for(v["d"])
        if a: e["ac"] = a
        if code in curves:
            e["b"], e["q"] = curves[code][0], curves[code][1]
        prices[code] = e

    # --- KAPI monthly index + yearly means -----------------------------------
    kapi, byyear = {}, {}
    for r in csv.DictReader(open(SRC_BINDER)):
        if r["grade"] != "64-22":
            continue
        m, p = r["month"][:7], float(r["price_per_ton"])
        kapi[m] = p
        byyear.setdefault(int(m[:4]), []).append(p)
    kapi_year = {str(y): round(sum(v) / len(v), 2) for y, v in byyear.items()}

    data = {
        "meta": {
            "built": datetime.date.today().isoformat(),
            "version": 1,
            "source": "KYTC statewide average unit bid prices 2022-2025; KAPI binder index",
            "projects_backtested": N_PROJECTS,
            "accuracy": ACCURACY,
        },
        "rules": RULES,
        "escalation": {"other": {str(k): v for k, v in ESC_OTHER.items()},
                       "asphalt_resid": {str(k): v for k, v in ESC_ASPH.items()}},
        "ls_ratios": LS_RATIOS,
        "kapi": kapi,
        "kapi_year": kapi_year,
        "prices": prices,
    }

    out = os.path.join(HERE, "data.json")
    json.dump(data, open(out, "w"), separators=(",", ":"))
    print(f"codes: {len(prices)}  curves: {len(curves)}  kapi months: {len(kapi)}")
    print(f"wrote {out}  ({os.path.getsize(out):,} bytes)")

if __name__ == "__main__":
    main()
