r"""
Side-by-side: bid_backtest_v7 vs the Stage A1+B baseline, on ONE identical holdout.

Run:
    py compare_v7.py            (after train_baseline.py has written pred_baseline.csv)

Reports three columns, because two of them are not comparable to each other:

  v7 as published   - the numbers in bid_backtest_v7 today, restricted to the
                      holdout contracts. NOT a holdout measurement: every price
                      table it reads was built from all 620 contracts, the
                      holdout included, and it allows same-year aggregates.
                      Shown so the published figure can be traced.

  v7 leak-free      - v7's pricing rules re-implemented exactly, but with the
                      statewide / pod / district price tables rebuilt from TRAIN
                      contracts only and restricted to strictly prior years.
                      This is the honest baseline.

  A1+B              - the LightGBM two-stage model, same holdout.

Still full-history-fitted inside "v7 leak-free", and therefore still generous to
v7: bid_qty_curves (beta/q_ref), bid_ls_ratios, bid_ac_content and the four
escalation constants. Those are ~80 scalars against 21k lines, so the residual
advantage is small, but it is an advantage and it is not zero.
"""
import os
import numpy as np
import pandas as pd

DATA_DIR = os.environ.get("EE_ML_DIR", r"C:\EE\ml\data")
HOLDOUT_FRAC = 0.25

MOB, DEMOB = "02568", "02569"
ADJ = ("10020NS", "10030NS")
SKIP = set(ADJ) | {MOB, DEMOB}

ESC_OTHER = {2023: 1.143, 2024: 0.942, 2025: 1.007, 2026: 1.073}
ESC_ASPH = {2023: 1.143, 2024: 0.942, 2025: 1.007, 2026: 1.156}


def v7_cat(work_type):
    w = (work_type or "").upper()
    if "BRIDGE" in w:
        return "BRIDGE"
    if "ALTERNATE" in w:
        return "ALT"
    if any(k in w for k in ("RESURF", "PAVEMENT", "MICRO", "THINLAY", "SEAL")):
        return "PAVE"
    return "GD"


def esc(from_yr, to_yr, chain):
    """v7's escalation: only fires when the source year is older than the letting year."""
    if from_yr is None or np.isnan(from_yr) or from_yr >= to_yr:
        return 1.0
    f = 1.0
    for y, m in chain.items():
        if from_yr < y <= to_yr:
            f *= m
    return f


def load():
    con = pd.read_csv(os.path.join(DATA_DIR, "contracts.tsv"), sep="\t", header=None,
                      names=["ci", "contract_id", "letting_date", "work_type", "county",
                             "dist", "pod", "n_items", "length_miles", "n_bidders",
                             "engineer_estimate", "low_bid"],
                      dtype={"contract_id": str, "dist": str, "pod": str})
    con["letting_date"] = pd.to_datetime(con["letting_date"])
    con["pod"] = con["pod"].fillna("")
    con["cat"] = con["work_type"].fillna("").map(v7_cat)
    con["ly"] = con["letting_date"].dt.year
    con["month"] = con["letting_date"].dt.strftime("%Y-%m")

    ln = pd.read_csv(os.path.join(DATA_DIR, "lines.tsv"), sep="\t", header=None,
                     names=["ci", "bid_code", "quantity", "unit", "section",
                            "binder_grade", "fixed_price", "price", "description"],
                     dtype={"bid_code": str, "unit": str, "section": str,
                            "binder_grade": str, "description": str}, quoting=3)
    for c in ("unit", "section", "binder_grade", "description"):
        ln[c] = ln[c].fillna("")

    pr = pd.read_csv(os.path.join(DATA_DIR, "prices.psv"), sep="|", header=None,
                     names=["kind", "month", "grade", "value"])
    binder = pr[(pr.kind == "B") & (pr.grade == "64-22")][["month", "value"]]
    binder = binder.rename(columns={"value": "binder"}).sort_values("month")

    rules = pd.read_csv(os.path.join(DATA_DIR, "rules.psv"), sep="|", header=None,
                        names=["kind", "a", "b", "c"])
    ac = [(r.a.strip("%"), float(r.b)) for r in rules[rules.kind == "AC"].itertuples()]
    qc = {r.a: (float(r.b), float(r.c)) for r in rules[rules.kind == "QC"].itertuples()}
    ls = {(r.a, r.b): float(r.c) for r in rules[rules.kind == "LS"].itertuples()}

    v7 = pd.read_csv(os.path.join(DATA_DIR, "v7_pred.tsv"), sep="\t", header=None,
                     names=["contract_id", "cat", "ee", "pred"], dtype={"contract_id": str})
    return con, ln, binder, ac, qc, ls, v7


def ac_pct_for(desc, ac):
    d = (desc or "").upper()
    for pat, pct in ac:
        if pat in d:
            return pct
    return None


def build_price_tables(train_lines, train_con):
    """Rebuild v7's three price tiers from TRAIN contracts only.

    state:    (bid_code, year) -> quantity-weighted average, matching how
              bid_state_avg_prices is built. Looked up with year < ly (strict).
    pod/dist: (key, bid_code)  -> median, n>=3, tagged with the newest train year
              that contributed, which is what v7's `yr` column means.
    """
    t = train_lines.merge(train_con[["ci", "ly", "dist", "pod"]], on="ci", how="left")

    st = (t.groupby(["bid_code", "ly"])
            .apply(lambda g: pd.Series({
                "p": (g["price"] * g["quantity"]).sum() / max(g["quantity"].sum(), 1e-9)}),
                   include_groups=False)
            .reset_index())
    state = {}
    for code, g in st.groupby("bid_code"):
        state[code] = g.sort_values("ly")[["ly", "p"]].values

    def geo(col):
        out = {}
        gg = t[t[col].astype(str) != ""]
        for (k, code), g in gg.groupby([col, "bid_code"]):
            if len(g) >= 3:
                out[(str(k), code)] = (float(g["price"].median()), int(g["ly"].max()))
        return out

    return state, geo("pod"), geo("dist")


def state_lookup(state, code, ly):
    """Strictly prior-year statewide average from train data."""
    arr = state.get(code)
    if arr is None:
        return None, None
    prior = arr[arr[:, 0] < ly]
    if len(prior) == 0:
        return None, None
    yr, p = prior[-1]
    return float(p), int(yr)


def run_v7(con, ln, binder, ac, qc, ls, train_ci, score_ci, leak_free):
    bmap = dict(zip(binder["month"], binder["binder"]))
    bmonths = sorted(bmap)

    def kapi_at(month):
        prior = [m for m in bmonths if m <= month]
        return bmap[prior[-1]] if prior else bmap[bmonths[0]]

    byear = binder.copy()
    byear["y"] = byear["month"].str[:4].astype(int)
    kyr_map = byear.groupby("y")["binder"].mean().to_dict()

    if leak_free:
        state, podt, distt = build_price_tables(
            ln[ln["ci"].isin(train_ci)], con[con["ci"].isin(train_ci)])
    else:
        raise NotImplementedError("published v7 is read from v7_pred.tsv, not recomputed")

    cinfo = con.set_index("ci").to_dict("index")
    rows = []
    for ci, g in ln[ln["ci"].isin(score_ci)].groupby("ci"):
        c = cinfo[ci]
        ly, cat = c["ly"], c["cat"]
        kapi = kapi_at(c["month"])
        kyr = kyr_map.get(min(ly, 2025), kapi)

        qty_by_code = g.groupby("bid_code")["quantity"].sum().to_dict()
        s = 0.0
        adj = 0.0
        has_mob = False
        ls_seen = {}

        for r in g.itertuples():
            code = r.bid_code
            if code in ADJ:
                adj += r.quantity * r.price      # fixed-price pass-through, known at bid time
                continue
            if code == MOB:
                has_mob = True
                continue
            if code == DEMOB:
                continue
            if r.unit == "LS" and (code, cat) in ls:
                ls_seen[code] = ls[(code, cat)]
                continue

            p, yr = None, None
            pk = podt.get((str(c["pod"]), code)) if c["pod"] else None
            dk = distt.get((str(c["dist"]), code))
            if pk:
                p, yr = pk
            elif dk:
                p, yr = dk
            else:
                p, yr = state_lookup(state, code, ly)
            if p is None:
                continue

            a = ac_pct_for(r.description, ac)
            if a:
                unit = max(0.0, p - a * kyr) * esc(yr, ly, ESC_ASPH) + a * kapi
            else:
                unit = p * esc(yr, ly, ESC_OTHER)

            if code in qc:
                beta, qref = qc[code]
                qcode = qty_by_code.get(code, r.quantity)
                if qref > 0 and qcode > 0:
                    unit *= min(2.5, max(0.6, (qcode / qref) ** beta))
            s += r.quantity * unit

        tot_pct = sum(ls_seen.values())
        pred = s * (1 + tot_pct) * (1 + (0.05 if has_mob else 0.0) + 0.015) + adj
        rows.append((c["contract_id"], cat, c["engineer_estimate"], pred))

    return pd.DataFrame(rows, columns=["contract_id", "cat", "ee", "pred"])


def table(d, label):
    d = d[(d["ee"] > 0) & (d["pred"] > 0)].copy()
    d["ape"] = (d["pred"] - d["ee"]).abs() / d["ee"] * 100
    rows = [(c, len(g), g["ape"].mean(), g["ape"].median()) for c, g in d.groupby("cat")]
    rows.append(("ALL", len(d), d["ape"].mean(), d["ape"].median()))
    out = pd.DataFrame(rows, columns=["cat", f"n_{label}", f"mean_{label}", f"med_{label}"])
    return out.sort_values("cat").reset_index(drop=True)


def main():
    con, ln, binder, ac, qc, ls, v7pub = load()
    cutoff = con["letting_date"].quantile(1 - HOLDOUT_FRAC)
    train_ci = set(con.loc[con["letting_date"] <= cutoff, "ci"])
    test_ci = set(con.loc[con["letting_date"] > cutoff, "ci"])
    hold_ids = set(con.loc[con["ci"].isin(test_ci), "contract_id"])
    print(f"holdout: letting_date > {cutoff.date()}   "
          f"{len(test_ci)} contracts, train {len(train_ci)}")

    pub = v7pub[v7pub["contract_id"].isin(hold_ids)].copy()
    lf = run_v7(con, ln, binder, ac, qc, ls, train_ci, test_ci, leak_free=True)

    base = pd.read_csv(os.path.join(DATA_DIR, "pred_baseline.csv"), dtype={"contract_id": str})
    base = base.rename(columns={"engineer_estimate": "ee", "pred_ee": "pred"})[
        ["contract_id", "cat", "ee", "pred"]]

    t = (table(pub, "v7pub")
         .merge(table(lf, "v7lf"), on="cat", how="outer")
         .merge(table(base, "a1b"), on="cat", how="outer"))
    cols = ["cat", "n_v7lf",
            "mean_v7pub", "mean_v7lf", "mean_a1b",
            "med_v7pub", "med_v7lf", "med_a1b"]
    t = t[cols].rename(columns={"n_v7lf": "n"})
    print("\n" + "=" * 92)
    print("MEAN / MEDIAN absolute percent error vs engineer_estimate — identical holdout")
    print("=" * 92)
    print(t.to_string(index=False, float_format=lambda v: f"{v:8.2f}"))

    print("\nwinner by work_type (leak-free v7 vs A1+B, on mean APE):")
    for _, r in t.iterrows():
        if pd.isna(r["mean_v7lf"]) or pd.isna(r["mean_a1b"]):
            continue
        win = "A1+B" if r["mean_a1b"] < r["mean_v7lf"] else "v7"
        gap = abs(r["mean_a1b"] - r["mean_v7lf"])
        print(f"  {r['cat']:7} n={int(r['n']):3}  ->  {win:5} by {gap:5.2f} pp")


if __name__ == "__main__":
    main()
