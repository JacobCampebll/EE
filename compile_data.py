#!/usr/bin/env python3
"""
KYTC EE Predictor — data compiler.
Reads the KYTC statewide average unit price files + the KAPI/OPIS index,
applies the year-fallback rule, and writes a single versioned data.json
for the single-file HTML app.

Re-run this after Cowork loads new lettings, then redeploy the app.

Source CSVs are not in the repo. Pass them with flags or env vars:

  python3 compile_data.py --prices state_avg_all.csv --binder binder_prices.csv
  EE_PRICES=... EE_BINDER=... python3 compile_data.py

Legacy /home/claude/... paths are still checked as a last-resort default so
existing sessions keep working. Missing files exit 1 with a path list.
"""
import argparse
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Last-resort defaults (Claude's original session layout). Prefer --prices /
# --binder or EE_PRICES / EE_BINDER so a fresh clone can actually run.
LEGACY_PRICES = "/home/claude/state_avg_all.csv"      # year,bid_code,description,unit,statewide_quantity,avg_price,contract_occurrences
LEGACY_BINDER = "/home/claude/bidpred/binder_prices.csv"

PRICE_COLS = (
    "year", "bid_code", "description", "unit",
    "statewide_quantity", "avg_price", "contract_occurrences",
)
BINDER_COLS = ("grade", "month", "price_per_ton")

# ---- engine constants (mirror bid_app_config in Supabase) --------------------
ESC_OTHER = {2023: 1.143, 2024: 0.942, 2025: 1.007, 2026: 1.073}   # non-asphalt YoY chain
ESC_ASPH  = {2023: 1.143, 2024: 0.942, 2025: 1.007, 2026: 1.156}   # asphalt residual chain
RULES = {"mob_cap": 0.05, "demob_floor": 0.015, "qty_min": 0.6, "qty_max": 2.5, "geo_min_n": 3}

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

COUNTY_TO_DISTRICT = {
  "ADAIR": "08",
  "ALLEN": "03",
  "ANDERSON": "07",
  "BALLARD": "01",
  "BARREN": "03",
  "BATH": "09",
  "BELL": "11",
  "BOONE": "06",
  "BOURBON": "07",
  "BOYD": "09",
  "BOYLE": "07",
  "BRACKEN": "06",
  "BREATHITT": "10",
  "BRECKINRIDGE": "04",
  "BULLITT": "05",
  "BUTLER": "03",
  "CALDWELL": "02",
  "CALLOWAY": "01",
  "CAMPBELL": "06",
  "CARLISLE": "01",
  "CARROLL": "06",
  "CARTER": "09",
  "CASEY": "08",
  "CHRISTIAN": "02",
  "CLARK": "07",
  "CLAY": "11",
  "CLINTON": "08",
  "CRITTENDEN": "01",
  "CUMBERLAND": "08",
  "DAVIESS": "02",
  "EDMONSON": "03",
  "ELLIOTT": "09",
  "ESTILL": "10",
  "FAYETTE": "07",
  "FLEMING": "09",
  "FLOYD": "12",
  "FRANKLIN": "05",
  "FULTON": "01",
  "GALLATIN": "06",
  "GARRARD": "07",
  "GRANT": "06",
  "GRAVES": "01",
  "GRAYSON": "04",
  "GREEN": "04",
  "GREENUP": "09",
  "HANCOCK": "02",
  "HARDIN": "04",
  "HARLAN": "11",
  "HARRISON": "06",
  "HART": "04",
  "HENDERSON": "02",
  "HENRY": "05",
  "HICKMAN": "01",
  "HOPKINS": "02",
  "JACKSON": "11",
  "JEFFERSON": "05",
  "JESSAMINE": "07",
  "JOHNSON": "12",
  "KENTON": "06",
  "KNOTT": "12",
  "KNOX": "11",
  "LARUE": "04",
  "LAUREL": "11",
  "LAWRENCE": "12",
  "LEE": "10",
  "LESLIE": "11",
  "LETCHER": "12",
  "LEWIS": "09",
  "LINCOLN": "08",
  "LIVINGSTON": "01",
  "LOGAN": "03",
  "LYON": "01",
  "MADISON": "07",
  "MAGOFFIN": "10",
  "MARION": "04",
  "MARSHALL": "01",
  "MARTIN": "12",
  "MASON": "09",
  "MCCRACKEN": "01",
  "MCCREARY": "08",
  "MCLEAN": "02",
  "MEADE": "04",
  "MENIFEE": "10",
  "MERCER": "07",
  "METCALFE": "03",
  "MONROE": "03",
  "MONTGOMERY": "07",
  "MORGAN": "10",
  "MUHLENBERG": "02",
  "NELSON": "04",
  "NICHOLAS": "09",
  "OHIO": "02",
  "OLDHAM": "05",
  "OWEN": "06",
  "OWSLEY": "10",
  "PENDLETON": "06",
  "PERRY": "10",
  "PIKE": "12",
  "POWELL": "10",
  "PULASKI": "08",
  "ROBERTSON": "06",
  "ROCKCASTLE": "08",
  "ROWAN": "09",
  "RUSSELL": "08",
  "SCOTT": "07",
  "SHELBY": "05",
  "SIMPSON": "03",
  "SPENCER": "05",
  "TAYLOR": "04",
  "TODD": "03",
  "TRIGG": "01",
  "TRIMBLE": "05",
  "UNION": "02",
  "WARREN": "03",
  "WASHINGTON": "04",
  "WAYNE": "08",
  "WEBSTER": "02",
  "WHITLEY": "11",
  "WOLFE": "10",
  "WOODFORD": "07",
}

def ac_for(desc):
    for k, v in AC.items():
        if k in (desc or ""):
            return v
    return None

def die(msg, code=1):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)

def _candidates(filename, extra):
    cwd = os.getcwd()
    out = [
        os.path.join(cwd, filename),
        os.path.join(HERE, filename),
        os.path.join(HERE, "data", filename),
    ]
    out.extend(extra)
    # de-dupe, keep order
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq

def resolve_source(cli_value, env_name, candidates, label, flag, cols, hint):
    """Return an existing path, or exit 1 with a usable error."""
    tried = []

    def check(path, via):
        if not path:
            return None
        tried.append(f"{path}  ({via})")
        if os.path.isfile(path):
            return os.path.abspath(path)
        return None

    def fail():
        looked = "\n".join(f"  {t}" for t in tried) or (
            f"  (nothing — pass --{flag} or set {env_name})"
        )
        die(
            f"error: {label} not found.\n\n"
            f"Pass it with --{flag} PATH, or set the {env_name} environment variable.\n\n"
            f"Looked in:\n{looked}\n\n"
            f"Expected columns: {','.join(cols)}\n"
            f"{hint}"
        )

    # Explicit flag or env var: that path must exist. Do not silently
    # fall through to search — the user named a file on purpose.
    if cli_value:
        found = check(cli_value, f"--{flag}")
        if not found:
            fail()
        return found
    env_val = os.environ.get(env_name, "")
    if env_val:
        found = check(env_val, f"env {env_name}")
        if not found:
            fail()
        return found
    for c in candidates:
        found = check(c, "search")
        if found:
            return found
    fail()

def require_columns(path, required, label):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        have = reader.fieldnames or []
    missing = [c for c in required if c not in have]
    if missing:
        die(
            f"error: {label} is missing columns: {', '.join(missing)}\n"
            f"  file: {path}\n"
            f"  have: {', '.join(have)}\n"
            f"  need: {', '.join(required)}"
        )

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Compile KYTC statewide averages + KAPI index into data.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 compile_data.py --prices state_avg_all.csv --binder binder_prices.csv\n"
            "  EE_PRICES=state_avg_all.csv EE_BINDER=binder_prices.csv python3 compile_data.py\n"
            "\n"
            "Do not invent the tuning constants at the top of this file — they come from\n"
            "Supabase project allen-qc, view bid_backtest_v6. Regenerating with the same\n"
            "source CSVs must not change a number in data.json except meta.built.\n"
        ),
    )
    p.add_argument(
        "--prices",
        default=None,
        help="Statewide average unit-price CSV. Env: EE_PRICES. "
             "Columns: year,bid_code,description,unit,statewide_quantity,avg_price,contract_occurrences",
    )
    p.add_argument(
        "--binder",
        default=None,
        help="KAPI/OPIS binder index CSV. Env: EE_BINDER. Columns: grade,month,price_per_ton",
    )
    p.add_argument(
        "--out",
        default=None,
        help="Output JSON path. Env: EE_OUT. Default: data.json next to this script.",
    )
    return p.parse_args(argv)

def main(argv=None):
    args = parse_args(argv)

    prices_path = resolve_source(
        args.prices, "EE_PRICES",
        _candidates("state_avg_all.csv", [LEGACY_PRICES]),
        "statewide average unit-price CSV", "prices", PRICE_COLS,
        "KYTC publishes yearly .xlsx files at:\n"
        "https://transportation.ky.gov/Construction-Procurement/Pages/Average-Unit-Bid-Prices.aspx\n"
        "Convert/combine them to the CSV above before compiling.",
    )
    binder_path = resolve_source(
        args.binder, "EE_BINDER",
        _candidates("binder_prices.csv", [
            os.path.join(HERE, "bidpred", "binder_prices.csv"),
            LEGACY_BINDER,
        ]),
        "KAPI/OPIS binder index CSV", "binder", BINDER_COLS,
        "KYTC \"Fuel and Asphalt Spreadsheet LET DT SEPT 2020 FORWARD\":\n"
        "https://transportation.ky.gov/Construction/Pages/Fuel-and-Asphalt-Adjustments.aspx",
    )
    out = args.out or os.environ.get("EE_OUT") or os.path.join(HERE, "data.json")

    require_columns(prices_path, PRICE_COLS, "prices CSV")
    require_columns(binder_path, BINDER_COLS, "binder CSV")
    print(f"prices: {prices_path}")
    print(f"binder: {binder_path}")

    curves = {}
    for part in CURVES_RAW.split(","):
        c, b, q = part.split(":")
        curves[c] = [float(b), float(q)]

    # --- prices: newest year wins, keep the year so the app can escalate ------
    best = {}
    with open(prices_path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
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
    with open(binder_path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
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
        "geo": {
            "county_to_district": COUNTY_TO_DISTRICT,
            "district": {},   # filled later from bid tabs / Supabase; empty => statewide fallback
            "county": {},
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"codes: {len(prices)}  curves: {len(curves)}  kapi months: {len(kapi)}")
    print(f"wrote {out}  ({os.path.getsize(out):,} bytes)")

if __name__ == "__main__":
    main()
