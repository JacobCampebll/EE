r"""Does `bid_qty_curves` need refitting? Measured, not assumed.

Run (after export_training.sql has written the flat files):
    py qty_curves.py

Background. v7 prices a line as

    unit = table_price * escalation * clamp((qty / q_ref) ** beta, 0.6, 2.5)

with (beta, q_ref) per bid_code in `bid_qty_curves`. Stage A1 found `log_qty`
to be its top feature by a factor of 2.5, which looked like evidence the curves
were under-powered. This script tests that directly, on the same leak-free
holdout `compare_v7.py` uses: price tables rebuilt from TRAIN contracts only,
restricted to strictly prior years, so only the curve varies between columns.

It reports three things:

  1. What the published curves actually do to real lines -- the multiplier
     distribution per code, and the share of dollars they move.
  2. A refit. beta re-estimated per code by OLS of log(deflated price) on
     log(qty) over TRAIN lines only, keeping only slopes significant at
     |t| >= MIN_T. Prices are deflated to 2025 with v7's own escalation chain
     first, so the slope measures quantity and not the year mix of the lines
     carrying that code.
  3. A grid: published vs refit beta, crossed with four sources of q_ref,
     scored on the holdout.

On q_ref. v7's cascade does not use one statistic: pod and district cells are
MEDIANS, statewide is a QUANTITY-WEIGHTED AVERAGE. Those have different neutral
quantities, so a single q_ref cannot be neutral for both tiers. Two of the
variants below give each tier its own reference:

    "tier"  -- median qty for pod/district, sum(q^2)/sum(q) for statewide
    "cal"   -- the q_ref that makes the curve mean-neutral against that tier's
               own base price, closed form from the weighted normal equation
               d/dlog(q_ref) SSE(log p - log P - beta*(log q - log q_ref)) = 0

Nothing here writes to Supabase or to the app. It is a measurement.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_v7 as V

DATA_DIR = os.environ.get("EE_ML_DIR", r"C:\EE\ml\data")

MIN_N = 30            # train lines before a code is eligible for a curve
MIN_T = 2.0           # |t| on the slope; below this the code gets no curve
BETA_LO, BETA_HI = -0.90, 0.10
CLAMP_LO, CLAMP_HI = 0.6, 2.5


# ---------------------------------------------------------------- diagnosis
def describe_published(ln, con, qc):
    """What the shipped curves do to the lines that actually exist."""
    d = ln.merge(con[["ci", "letting_date"]], on="ci")
    d["dollars"] = d["quantity"] * d["price"]
    tot = d["dollars"].sum()

    rows = []
    for code, (beta, qref) in sorted(qc.items()):
        g = d[d["bid_code"] == code]
        if not len(g):
            continue
        q = g["quantity"].values
        m = np.clip((q / qref) ** beta, CLAMP_LO, CLAMP_HI)
        rows.append((code, beta, qref, len(g), float(np.median(q)),
                     float(np.median(q) / qref), float(np.percentile(m, 10)),
                     float(np.median(m)), float(np.percentile(m, 90)),
                     100 * g["dollars"].sum() / tot))

    t = pd.DataFrame(rows, columns=["code", "beta", "q_ref", "n", "med_qty",
                                    "medq/qref", "mult_p10", "mult_p50",
                                    "mult_p90", "%$"]).sort_values("%$", ascending=False)
    sub = d[d["bid_code"].isin(qc)].copy()
    b = sub["bid_code"].map(lambda c: qc[c][0])
    r = sub["bid_code"].map(lambda c: qc[c][1])
    sub["mult"] = np.clip((sub["quantity"] / r) ** b, CLAMP_LO, CLAMP_HI)
    w = sub["dollars"]

    print(f"priced lines {len(d):,}   ${tot:,.0f}")
    print(f"lines carrying a curve: {len(sub):,} "
          f"({100 * w.sum() / tot:.1f}% of dollars)\n")
    print(t.head(20).to_string(index=False, float_format=lambda v: f"{v:10.3f}"))
    print(f"\ndollar-weighted mean multiplier: {(sub['mult'] * w).sum() / w.sum():.4f}")
    print(f"curved dollars within 2% of 1.0: "
          f"{100 * w[sub['mult'].sub(1).abs() < 0.02].sum() / w.sum():.1f}%")
    print(f"clamped low {(sub['mult'] <= CLAMP_LO + 1e-4).sum():,}   "
          f"high {(sub['mult'] >= CLAMP_HI - 1e-4).sum():,}")


# ------------------------------------------------------------------- refit
def fit_curves(train_lines, train_con, min_n=MIN_N, min_t=MIN_T):
    """OLS log(deflated price) ~ log(qty) per bid_code, TRAIN fold only."""
    t = train_lines.merge(train_con[["ci", "ly"]], on="ci", how="left")
    t = t[(t["quantity"] > 0) & (t["price"] > 0)]
    e = t.apply(lambda r: V.esc(r["ly"], 2025, V.ESC_OTHER), axis=1)
    t = t.assign(pdefl=t["price"].values * e.values)

    out = {}
    for code, g in t.groupby("bid_code"):
        n = len(g)
        if n < min_n:
            continue
        x, y = np.log(g["quantity"].values), np.log(g["pdefl"].values)
        if x.std() < 1e-9:
            continue
        X = np.column_stack([np.ones(n), x])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ coef
        se = np.sqrt((resid ** 2).sum() / (n - 2) * np.linalg.inv(X.T @ X)[1, 1])
        tstat = float(coef[1] / se) if se > 0 else 0.0
        if abs(tstat) < min_t:
            continue

        beta = float(np.clip(coef[1], BETA_LO, BETA_HI))
        q, p = g["quantity"].values, g["pdefl"].values
        P_med, P_qw = float(np.median(p)), float((p * q).sum() / q.sum())

        def cal(P, w):
            """q_ref making the curve mean-neutral against base price P."""
            if beta == 0 or P <= 0:
                return np.nan
            return float(np.exp(np.average(x, weights=w)
                                - (np.average(y, weights=w) - np.log(P)) / beta))

        out[code] = {"beta": beta, "n": n, "t": tstat,
                     "r2": float(1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()),
                     "q_med": float(np.median(q)),
                     "q_qw": float((q ** 2).sum() / q.sum()),
                     "cal_geo": cal(P_med, np.ones(n)),
                     "cal_state": cal(P_qw, q)}
    return out


# ------------------------------------------------------------------ scoring
def make_curve(qc_pub, tab, beta_src, qref_src):
    """Return f(bid_code, tier, qty) -> multiplier for one grid cell."""
    def f(code, tier, q):
        if beta_src == "pub":
            if code not in qc_pub:
                return 1.0
            beta = qc_pub[code][0]
        else:
            if code not in tab:
                return 1.0
            beta = tab[code]["beta"]

        if qref_src == "pub":
            if code not in qc_pub:
                return 1.0
            qref = qc_pub[code][1]
        elif qref_src == "none":
            return 1.0
        else:
            if code not in tab:
                return 1.0
            key = ("q_med" if tier == "geo" else "q_qw") if qref_src == "tier" \
                else ("cal_geo" if tier == "geo" else "cal_state")
            qref = tab[code][key]

        if not (q > 0 and qref and qref > 0 and np.isfinite(qref)):
            return 1.0
        return min(CLAMP_HI, max(CLAMP_LO, (q / qref) ** beta))
    return f


def run_v7(con, ln, binder, ac, ls, train_ci, score_ci, curve):
    """v7's arithmetic, leak-free tables, with the quantity step injectable.

    Identical to compare_v7.run_v7 except that the curve is a parameter and the
    tier that supplied the price is passed to it.
    """
    bmap = dict(zip(binder["month"], binder["binder"]))
    bmonths = sorted(bmap)

    def kapi_at(month):
        prior = [m for m in bmonths if m <= month]
        return bmap[prior[-1]] if prior else bmap[bmonths[0]]

    byear = binder.copy()
    byear["y"] = byear["month"].str[:4].astype(int)
    kyr_map = byear.groupby("y")["binder"].mean().to_dict()

    state, podt, distt = V.build_price_tables(
        ln[ln["ci"].isin(train_ci)], con[con["ci"].isin(train_ci)])

    cinfo = con.set_index("ci").to_dict("index")
    rows = []
    for ci, g in ln[ln["ci"].isin(score_ci)].groupby("ci"):
        c = cinfo[ci]
        ly, cat = c["ly"], c["cat"]
        kapi = kapi_at(c["month"])
        kyr = kyr_map.get(min(ly, 2025), kapi)
        qty_by_code = g.groupby("bid_code")["quantity"].sum().to_dict()
        s = adj = 0.0
        has_mob = False
        ls_seen = {}

        for r in g.itertuples():
            code = r.bid_code
            if code in V.ADJ:
                adj += r.quantity * r.price
                continue
            if code == V.MOB:
                has_mob = True
                continue
            if code == V.DEMOB:
                continue
            if r.unit == "LS" and (code, cat) in ls:
                ls_seen[code] = ls[(code, cat)]
                continue

            pk = podt.get((str(c["pod"]), code)) if c["pod"] else None
            dk = distt.get((str(c["dist"]), code))
            if pk:
                p, yr, tier = pk[0], pk[1], "geo"
            elif dk:
                p, yr, tier = dk[0], dk[1], "geo"
            else:
                p, yr = V.state_lookup(state, code, ly)
                tier = "state"
            if p is None:
                continue

            a = V.ac_pct_for(r.description, ac)
            if a:
                unit = max(0.0, p - a * kyr) * V.esc(yr, ly, V.ESC_ASPH) + a * kapi
            else:
                unit = p * V.esc(yr, ly, V.ESC_OTHER)

            unit *= curve(code, tier, qty_by_code.get(code, r.quantity))
            s += r.quantity * unit

        pred = s * (1 + sum(ls_seen.values())) \
            * (1 + (0.05 if has_mob else 0.0) + 0.015) + adj
        rows.append((c["contract_id"], cat, c["engineer_estimate"], pred))
    return pd.DataFrame(rows, columns=["contract_id", "cat", "ee", "pred"])


VARIANTS = [
    ("published beta + published q_ref", "pub", "pub"),
    ("no curve at all", "pub", "none"),
    ("published beta + tier q_ref", "pub", "tier"),
    ("published beta + calibrated q_ref", "pub", "cal"),
    ("refit beta + published q_ref", "refit", "pub"),
    ("refit beta + tier q_ref", "refit", "tier"),
    ("refit beta + calibrated q_ref", "refit", "cal"),
]


def main():
    con, ln, binder, ac, qc_pub, ls, _ = V.load()
    cutoff = con["letting_date"].quantile(1 - V.HOLDOUT_FRAC)
    train_ci = set(con.loc[con["letting_date"] <= cutoff, "ci"])
    test_ci = set(con.loc[con["letting_date"] > cutoff, "ci"])

    print("=" * 78)
    print("1. WHAT THE PUBLISHED CURVES DO")
    print("=" * 78)
    describe_published(ln, con, qc_pub)

    tab = fit_curves(ln[ln["ci"].isin(train_ci)], con[con["ci"].isin(train_ci)])
    print("\n" + "=" * 78)
    print(f"2. REFIT — {len(qc_pub)} published curves, {len(tab)} refit "
          f"(n>={MIN_N}, |t|>={MIN_T}), train fold only")
    print("=" * 78)
    f = pd.DataFrame(tab).T.sort_values("t", key=lambda s: s.abs(), ascending=False)
    f["beta_pub"] = [qc_pub.get(i, (np.nan, np.nan))[0] for i in f.index]
    print(f[["n", "beta", "beta_pub", "t", "r2", "q_med", "q_qw"]].head(15)
          .to_string(float_format=lambda v: f"{v:9.3f}"))

    print("\n" + "=" * 78)
    print(f"3. HOLDOUT — letting_date > {cutoff.date()}  "
          f"({len(test_ci)} contracts, train {len(train_ci)})")
    print("=" * 78)
    out = None
    for name, bs, qs in VARIANTS:
        d = run_v7(con, ln, binder, ac, ls, train_ci, test_ci,
                   make_curve(qc_pub, tab, bs, qs))
        t = V.table(d, "x").rename(columns={"n_x": "n", "mean_x": name,
                                            "med_x": "m|" + name})
        out = t if out is None else out.merge(t.drop(columns="n"), on="cat")

    names = [v[0] for v in VARIANTS]
    pd.set_option("display.width", 240)
    print("\nMEAN APE vs engineer_estimate")
    print(out[["cat", "n"] + names].to_string(index=False,
                                              float_format=lambda v: f"{v:7.2f}"))
    print("\nMEDIAN APE")
    print(out[["cat", "n"] + ["m|" + n for n in names]]
          .to_string(index=False, float_format=lambda v: f"{v:7.2f}"))

    base = out.loc[out["cat"] == "ALL", names[0]].iloc[0]
    print(f"\nbaseline (published curves) ALL mean APE = {base:.2f}")
    for n in names[1:]:
        v = out.loc[out["cat"] == "ALL", n].iloc[0]
        print(f"  {n:38} {v:6.2f}  ({v - base:+.2f} pp)")


if __name__ == "__main__":
    main()
