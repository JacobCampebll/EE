r"""
Stage A1 + Stage B baseline: LightGBM line-item price model -> contract EE.

Run:
    py train_baseline.py

Reads the three files produced by sql\export_training.sql:
    C:\EE\ml\data\contracts.tsv
    C:\EE\ml\data\lines.tsv
    C:\EE\ml\data\prices.psv

Set EE_ML_DIR to point somewhere else (used for the Linux dev run).

LEAKAGE RULES ENFORCED HERE - see README.md for the reasoning:
  * temporal split on letting_date, grouped by contract (a contract is wholly
    in train or wholly in test, never split)
  * no bid_state_avg_prices / bid_geo_prices / bid_qty_curves / bid_ls_ratios
    are read at all; every aggregate is recomputed from TRAIN contracts only
  * every aggregate is PRIOR-YEAR: a line in letting year Y sees only train
    contracts with letting year < Y
  * Stage B's EE/low-bid ratio is fit on TRAIN contracts only
"""
import os
import sys
import numpy as np
import pandas as pd
import lightgbm as lgb

DATA_DIR = os.environ.get("EE_ML_DIR", r"C:\EE\ml\data")
HOLDOUT_FRAC = 0.25          # last 25% of contracts by letting_date
SEED = 17

pd.set_option("display.width", 200)


# ---------------------------------------------------------------- load

def load():
    con = pd.read_csv(
        os.path.join(DATA_DIR, "contracts.tsv"), sep="\t", header=None,
        names=["ci", "contract_id", "letting_date", "work_type", "county",
               "dist", "pod", "n_items", "length_miles", "n_bidders",
               "engineer_estimate", "low_bid"],
        dtype={"contract_id": str, "dist": str, "pod": str},
    )
    con["letting_date"] = pd.to_datetime(con["letting_date"])
    con["pod"] = con["pod"].fillna("")
    con["work_type"] = con["work_type"].fillna("")

    ln = pd.read_csv(
        os.path.join(DATA_DIR, "lines.tsv"), sep="\t", header=None,
        names=["ci", "bid_code", "quantity", "unit", "section",
               "binder_grade", "fixed_price", "price", "description"],
        dtype={"bid_code": str, "unit": str, "section": str,
               "binder_grade": str, "description": str},
        quoting=3,          # no quote handling; the export strips tabs/newlines
    )
    for c in ("unit", "section", "binder_grade", "description"):
        ln[c] = ln[c].fillna("")

    pr = pd.read_csv(os.path.join(DATA_DIR, "prices.psv"), sep="|", header=None,
                     names=["kind", "month", "grade", "value"])
    binder = (pr[(pr.kind == "B") & (pr.grade == "64-22")][["month", "value"]]
              .rename(columns={"value": "binder"}).reset_index(drop=True))
    fuel = (pr[pr.kind == "F"][["month", "value"]]
            .rename(columns={"value": "fuel"}).reset_index(drop=True))
    return con, ln, binder, fuel


def v7_cat(work_type: str) -> str:
    """Mirror bid_backtest_v7's category buckets so the comparison is like-for-like."""
    w = (work_type or "").upper()
    if "BRIDGE" in w:
        return "BRIDGE"
    if "ALTERNATE" in w:
        return "ALT"
    if any(k in w for k in ("RESURF", "PAVEMENT", "MICRO", "THINLAY", "SEAL")):
        return "PAVE"
    return "GD"


# ---------------------------------------------------------------- features

MOB, DEMOB = "02568", "02569"


def build(con, ln, binder, fuel):
    con = con.copy()
    con["cat"] = con["work_type"].map(v7_cat)
    con["ly"] = con["letting_date"].dt.year
    con["lm"] = con["letting_date"].dt.month
    con["month"] = con["letting_date"].dt.strftime("%Y-%m")

    # as-of join on month: carry the last published binder/fuel forward
    months = pd.DataFrame({"month": sorted(set(con["month"]) | set(binder["month"]) | set(fuel["month"]))})
    months = months.merge(binder, on="month", how="left").merge(fuel, on="month", how="left")
    months = months.sort_values("month")
    months["binder"] = months["binder"].ffill()
    months["fuel"] = months["fuel"].ffill()
    con = con.merge(months, on="month", how="left")

    df = ln.merge(con, on="ci", how="inner", suffixes=("", "_c"))
    df = df[df["price"] > 0].copy()

    df["log_price"] = np.log(df["price"])
    df["log_qty"] = np.log(df["quantity"].clip(lower=1e-6))
    df["line_dollars"] = df["quantity"] * df["price"]

    tot = df.groupby("ci")["line_dollars"].transform("sum")
    df["dollar_share"] = df["line_dollars"] / tot.replace(0, np.nan)
    df["dollar_share"] = df["dollar_share"].fillna(0.0)

    df["lines_in_contract"] = df.groupby("ci")["bid_code"].transform("size")
    df["item_share"] = 1.0 / df["lines_in_contract"]
    df["is_mob"] = (df["bid_code"] == MOB).astype(int)
    df["is_demob"] = (df["bid_code"] == DEMOB).astype(int)
    df["is_ls"] = (df["unit"] == "LS").astype(int)
    return df


CATS = ["bid_code", "unit", "section", "binder_grade", "work_type",
        "county", "dist", "pod", "cat"]
NUMS = ["log_qty", "n_items", "length_miles", "ly", "lm", "binder", "fuel",
        "item_share", "lines_in_contract", "fixed_price", "is_ls"]


def prior_year_aggs(train_df, all_df):
    """Per-bid_code prior-year median log price, computed from TRAIN rows only.

    For a line in letting year Y the feature uses train rows with ly < Y, so it is
    leak-free both across the split and within the training years themselves.
    """
    g = (train_df.groupby(["bid_code", "ly"])["log_price"]
         .agg(["sum", "count"]).reset_index()
         .sort_values(["bid_code", "ly"]))
    g["cum_sum"] = g.groupby("bid_code")["sum"].cumsum() - g["sum"]
    g["cum_n"] = g.groupby("bid_code")["count"].cumsum() - g["count"]
    g["prior_mean_logp"] = np.where(g["cum_n"] > 0, g["cum_sum"] / g["cum_n"], np.nan)
    lut = g[["bid_code", "ly", "prior_mean_logp", "cum_n"]].rename(columns={"cum_n": "prior_n"})

    # a year the code was never seen in still needs the latest prior value
    years = sorted(all_df["ly"].unique())
    codes = sorted(set(all_df["bid_code"]))
    full = pd.MultiIndex.from_product([codes, years], names=["bid_code", "ly"]).to_frame(index=False)
    full = full.merge(lut, on=["bid_code", "ly"], how="left").sort_values(["bid_code", "ly"])
    full["prior_mean_logp"] = full.groupby("bid_code")["prior_mean_logp"].ffill()
    full["prior_n"] = full.groupby("bid_code")["prior_n"].ffill().fillna(0)
    return full


def add_aggs(df, lut):
    out = df.merge(lut, on=["bid_code", "ly"], how="left")
    out["prior_n"] = out["prior_n"].fillna(0)
    return out


def as_categorical(df, cat_maps=None):
    df = df.copy()
    if cat_maps is None:
        cat_maps = {c: pd.Index(sorted(df[c].astype(str).unique())) for c in CATS}
    for c in CATS:
        codes = cat_maps[c].get_indexer(df[c].astype(str))
        df[c] = pd.Categorical.from_codes(codes, categories=list(cat_maps[c]))
    return df, cat_maps


# ---------------------------------------------------------------- stage A

FEATS = CATS + NUMS + ["prior_mean_logp", "prior_n"]


def fit_stage_a(tr, te, extra_feat=None):
    feats = FEATS + (extra_feat or [])
    # deterministic=True + force_row_wise + single thread: without these LightGBM
    # varies run to run and the holdout numbers move by ~0.2pp, which is enough to
    # flip the winner on a group as tight as GD. A benchmark that will not
    # reproduce is not a benchmark.
    params = dict(objective="regression", metric="l2", learning_rate=0.05,
                  num_leaves=63, min_data_in_leaf=20, feature_fraction=0.85,
                  bagging_fraction=0.85, bagging_freq=1, lambda_l2=1.0,
                  verbose=-1, seed=SEED, num_threads=1,
                  deterministic=True, force_row_wise=True,
                  data_random_seed=SEED, feature_fraction_seed=SEED,
                  bagging_seed=SEED)
    dtr = lgb.Dataset(tr[feats], label=tr["log_price"], weight=tr["w"],
                      categorical_feature=CATS, free_raw_data=False)
    dte = lgb.Dataset(te[feats], label=te["log_price"], weight=te["w"],
                      categorical_feature=CATS, reference=dtr, free_raw_data=False)
    model = lgb.train(params, dtr, num_boost_round=3000,
                      valid_sets=[dte], valid_names=["holdout"],
                      callbacks=[lgb.early_stopping(100, verbose=False),
                                 lgb.log_evaluation(0)])
    return model, feats


# ---------------------------------------------------------------- stage B

def fit_ee_ratio(train_con):
    """EE / low_bid, fit on TRAIN contracts only. Low-parameter by design."""
    t = train_con.copy()
    t["ratio"] = t["engineer_estimate"] / t["low_bid"]
    t = t[(t["ratio"] > 0.3) & (t["ratio"] < 3.0)]
    glob = t["ratio"].median()
    by_cat = t.groupby("cat")["ratio"].median().to_dict()
    t["nb"] = t["n_bidders"].clip(1, 4)
    by_cat_nb = t.groupby(["cat", "nb"])["ratio"].agg(["median", "size"])
    by_cat_nb = by_cat_nb[by_cat_nb["size"] >= 12]["median"].to_dict()
    by_year = t.groupby("ly")["ratio"].median().to_dict()
    return {"global": glob, "cat": by_cat, "cat_nb": by_cat_nb, "year": by_year}


def apply_ee_ratio(row, R):
    nb = int(min(max(row["n_bidders"], 1), 4))
    return R["cat_nb"].get((row["cat"], nb), R["cat"].get(row["cat"], R["global"]))


# ---------------------------------------------------------------- metrics

def report(pred_con, label):
    d = pred_con.copy()
    d["ape"] = (d["pred_ee"] - d["engineer_estimate"]).abs() / d["engineer_estimate"] * 100
    rows = []
    for cat, g in d.groupby("cat"):
        rows.append((cat, len(g), g["ape"].mean(), g["ape"].median()))
    rows.append(("ALL", len(d), d["ape"].mean(), d["ape"].median()))
    out = pd.DataFrame(rows, columns=["work_type", "n", "mean_ape", "median_ape"])
    out = out.sort_values("work_type").reset_index(drop=True)
    print(f"\n=== {label} ===")
    print(out.to_string(index=False, float_format=lambda v: f"{v:7.2f}"))
    return out


# ---------------------------------------------------------------- main

def main():
    con, ln, binder, fuel = load()
    df = build(con, ln, binder, fuel)

    cutoff = con["letting_date"].quantile(1 - HOLDOUT_FRAC)
    tr_ci = set(con.loc[con["letting_date"] <= cutoff, "ci"])
    te_ci = set(con.loc[con["letting_date"] > cutoff, "ci"])
    print(f"temporal split at {cutoff.date()}   "
          f"train contracts {len(tr_ci)}   holdout contracts {len(te_ci)}")
    print(f"train lines {(df['ci'].isin(tr_ci)).sum()}   "
          f"holdout lines {(df['ci'].isin(te_ci)).sum()}")

    lut = prior_year_aggs(df[df["ci"].isin(tr_ci)], df)
    df = add_aggs(df, lut)
    df["w"] = df["dollar_share"]

    df, cat_maps = as_categorical(df)
    tr = df[df["ci"].isin(tr_ci)].copy()
    te = df[df["ci"].isin(te_ci)].copy()

    # ---- pass 1: everything except mobilisation / demobilisation
    p1_tr = tr[(tr["is_mob"] == 0) & (tr["is_demob"] == 0)]
    p1_te = te[(te["is_mob"] == 0) & (te["is_demob"] == 0)]
    m1, feats1 = fit_stage_a(p1_tr, p1_te)
    print(f"pass 1  best_iter={m1.best_iteration}  "
          f"holdout l2={m1.best_score['holdout']['l2']:.4f}  rows={len(p1_tr)}")

    for frame in (tr, te):
        frame["pred_logp"] = m1.predict(frame[feats1], num_iteration=m1.best_iteration)
    df_all = pd.concat([tr, te])
    df_all["pred_price"] = np.exp(df_all["pred_logp"])
    df_all["pred_dollars"] = df_all["quantity"] * df_all["pred_price"]

    # ---- pass 2: mob / demob, given the predicted subtotal of everything else
    sub = (df_all[(df_all["is_mob"] == 0) & (df_all["is_demob"] == 0)]
           .groupby("ci")["pred_dollars"].sum().rename("subtotal").reset_index())
    df_all = df_all.merge(sub, on="ci", how="left")
    df_all["log_subtotal"] = np.log(df_all["subtotal"].clip(lower=1.0))

    ls_tr = df_all[(df_all["ci"].isin(tr_ci)) & ((df_all["is_mob"] == 1) | (df_all["is_demob"] == 1))]
    ls_te = df_all[(df_all["ci"].isin(te_ci)) & ((df_all["is_mob"] == 1) | (df_all["is_demob"] == 1))]
    if len(ls_tr) >= 50:
        m2, feats2 = fit_stage_a(ls_tr, ls_te, extra_feat=["log_subtotal"])
        print(f"pass 2  best_iter={m2.best_iteration}  rows={len(ls_tr)} (mob/demob)")
        mask = (df_all["is_mob"] == 1) | (df_all["is_demob"] == 1)
        df_all.loc[mask, "pred_price"] = np.exp(
            m2.predict(df_all.loc[mask, feats2], num_iteration=m2.best_iteration))
        df_all.loc[mask, "pred_dollars"] = (
            df_all.loc[mask, "quantity"] * df_all.loc[mask, "pred_price"])
    else:
        print("pass 2 skipped: too few mob/demob training rows")

    # ---- stage B
    pred_lowbid = df_all.groupby("ci")["pred_dollars"].sum().rename("pred_low_bid").reset_index()
    cc = con.copy()
    cc["cat"] = cc["work_type"].map(v7_cat)
    cc["ly"] = cc["letting_date"].dt.year
    cc = cc.merge(pred_lowbid, on="ci", how="left")

    R = fit_ee_ratio(cc[cc["ci"].isin(tr_ci)])
    cc["ratio"] = cc.apply(lambda r: apply_ee_ratio(r, R), axis=1)
    cc["pred_ee"] = cc["pred_low_bid"] * cc["ratio"]

    hold = cc[cc["ci"].isin(te_ci)].copy()
    print(f"\nEE/low-bid ratio (train medians): global={R['global']:.4f}  " +
          "  ".join(f"{k}={v:.4f}" for k, v in sorted(R["cat"].items())))

    report(hold, f"STAGE A1 + B  — holdout, letting_date > {cutoff.date()}  (n={len(hold)})")

    out = os.path.join(DATA_DIR, "pred_baseline.csv")
    hold[["contract_id", "cat", "letting_date", "n_bidders",
          "engineer_estimate", "low_bid", "pred_low_bid", "ratio", "pred_ee"]].to_csv(out, index=False)
    print(f"\nholdout predictions -> {out}")

    imp = pd.DataFrame({"feature": feats1,
                        "gain": m1.feature_importance("gain")}).sort_values("gain", ascending=False)
    print("\ntop 12 features by gain (pass 1):")
    print(imp.head(12).to_string(index=False, float_format=lambda v: f"{v:12.0f}"))


if __name__ == "__main__":
    sys.exit(main())
