r"""
Stage A2: MiniLM description embeddings + numeric features -> 3-layer MLP -> log unit price.
Stage B is unchanged and imported from train_baseline, so A1 and A2 differ only in Stage A.

Run:
    py embed_descriptions.py     (once -- writes desc_emb.npy, ~30s on CPU)
    py train_embed.py

Why this exists: 1,309 bid codes over 21,383 lines is a long tail. One-hot
`bid_code` learns nothing transferable about a code seen twice. "CL2 ASPH SURF
0.38D PG64-22" and "CL3 ASPH SURF 0.38B PG64-22" are near-identical strings that
one-hot treats as unrelated columns; MiniLM puts them next to each other. So the
embedding REPLACES bid_code here rather than joining it -- if both are present
the net can just memorise the code and the tail gains nothing.

Everything about the split, the sample weights, the prior-year aggregate and
Stage B is identical to train_baseline.py. Same leakage rules, same holdout.
"""
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

import train_baseline as A1

DATA_DIR = os.environ.get("EE_ML_DIR", r"C:\EE\ml\data")
SEED = 17
MOB, DEMOB = "02568", "02569"

# one-hot these; bid_code and section are deliberately NOT here -- bid_code is
# what the embedding is for, and section is 342 levels of mostly-noise
OH = ["unit", "binder_grade", "work_type", "county", "dist", "pod", "cat"]
# EE_A2_WITH_CODE=1 adds bid_code one-hot alongside the embedding, to test whether
# embeddings work as a SUPPLEMENT to code identity rather than a replacement.
if os.environ.get("EE_A2_WITH_CODE") == "1":
    OH = OH + ["bid_code"]
NUM = ["log_qty", "n_items", "length_miles", "ly", "lm", "binder", "fuel",
       "item_share", "lines_in_contract", "fixed_price", "is_ls",
       "prior_mean_logp", "prior_n"]


def seed_all():
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


class MLP(nn.Module):
    """3 hidden layers, per the brief."""

    def __init__(self, d_in, h=(256, 128, 64), p=0.15):
        super().__init__()
        layers, prev = [], d_in
        for w in h:
            layers += [nn.Linear(prev, w), nn.BatchNorm1d(w), nn.ReLU(), nn.Dropout(p)]
            prev = w
        layers += [nn.Linear(prev, 1)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(-1)


def load_embeddings(df):
    emb = np.load(os.path.join(DATA_DIR, "desc_emb.npy"))
    keys = pd.read_csv(os.path.join(DATA_DIR, "desc_keys.tsv"), sep="\t", header=None,
                       names=["bid_code", "description"],
                       dtype={"bid_code": str, "description": str}, quoting=3)
    keys["description"] = keys["description"].fillna("")
    keys["row"] = np.arange(len(keys))
    m = df.merge(keys, on=["bid_code", "description"], how="left")
    missing = int(m["row"].isna().sum())
    if missing:
        raise SystemExit(f"{missing} lines have no embedding -- re-run embed_descriptions.py")
    return emb[m["row"].astype(int).values]


def design_matrix(df, oh_cols=None, scaler=None):
    X_oh = pd.get_dummies(df[OH].astype(str), columns=OH, dtype=np.float32)
    if oh_cols is None:
        oh_cols = X_oh.columns
    X_oh = X_oh.reindex(columns=oh_cols, fill_value=0.0)

    X_num = df[NUM].astype(np.float32).copy()
    X_num["prior_mean_logp"] = X_num["prior_mean_logp"].fillna(X_num["prior_mean_logp"].median())
    X_num = X_num.fillna(0.0)
    if scaler is None:
        mu = X_num.mean(axis=0)
        sd = X_num.std(axis=0).replace(0, 1.0)
        scaler = (mu, sd)
    mu, sd = scaler
    X_num = (X_num - mu) / sd
    return X_oh.values.astype(np.float32), X_num.values.astype(np.float32), oh_cols, scaler


def train_mlp(Xtr, ytr, wtr, Xte, yte, wte, epochs=200, patience=25, lr=1e-3, wd=1e-4):
    seed_all()
    model = MLP(Xtr.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5, patience=8)

    Xtr_t, ytr_t, wtr_t = map(torch.tensor, (Xtr, ytr, wtr))
    Xte_t, yte_t, wte_t = map(torch.tensor, (Xte, yte, wte))

    n = len(Xtr_t)
    bs = 512
    best, best_state, bad = np.inf, None, 0
    g = torch.Generator().manual_seed(SEED)

    for ep in range(epochs):
        model.train()
        perm = torch.randperm(n, generator=g)
        for i in range(0, n, bs):
            idx = perm[i:i + bs]
            if len(idx) < 2:            # BatchNorm needs >1 row
                continue
            opt.zero_grad()
            pred = model(Xtr_t[idx])
            w = wtr_t[idx]
            loss = (w * (pred - ytr_t[idx]) ** 2).sum() / w.sum().clamp(min=1e-12)
            loss.backward()
            opt.step()

        model.eval()
        with torch.no_grad():
            pv = model(Xte_t)
            vl = ((wte_t * (pv - yte_t) ** 2).sum() / wte_t.sum().clamp(min=1e-12)).item()
        sched.step(vl)
        if vl < best - 1e-5:
            best, bad = vl, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, best, ep + 1


def predict(model, X):
    with torch.no_grad():
        return model(torch.tensor(X)).numpy()


def main():
    seed_all()
    con, ln, binder, fuel = A1.load()
    df = A1.build(con, ln, binder, fuel)

    cutoff = con["letting_date"].quantile(1 - A1.HOLDOUT_FRAC)
    tr_ci = set(con.loc[con["letting_date"] <= cutoff, "ci"])
    te_ci = set(con.loc[con["letting_date"] > cutoff, "ci"])
    print(f"temporal split at {cutoff.date()}   train {len(tr_ci)}   holdout {len(te_ci)}")

    lut = A1.prior_year_aggs(df[df["ci"].isin(tr_ci)], df)
    df = A1.add_aggs(df, lut)
    df["w"] = df["dollar_share"]
    df = df.reset_index(drop=True)

    E = load_embeddings(df)
    print(f"embeddings attached: {E.shape}")

    is_ls_line = (df["bid_code"] == MOB) | (df["bid_code"] == DEMOB)
    tr_mask = df["ci"].isin(tr_ci).values
    te_mask = df["ci"].isin(te_ci).values

    # ---- pass 1: everything except mob/demob
    p1 = ~is_ls_line.values
    oh_cols = scaler = None
    Xoh, Xnum, oh_cols, scaler = design_matrix(df[p1 & tr_mask], None, None)
    Xtr = np.hstack([E[p1 & tr_mask], Xoh, Xnum])
    Xoh_e, Xnum_e, _, _ = design_matrix(df[p1 & te_mask], oh_cols, scaler)
    Xte = np.hstack([E[p1 & te_mask], Xoh_e, Xnum_e])

    ytr = df.loc[p1 & tr_mask, "log_price"].values.astype(np.float32)
    yte = df.loc[p1 & te_mask, "log_price"].values.astype(np.float32)
    wtr = df.loc[p1 & tr_mask, "w"].values.astype(np.float32)
    wte = df.loc[p1 & te_mask, "w"].values.astype(np.float32)

    m1, vl, eps = train_mlp(Xtr, ytr, wtr, Xte, yte, wte)
    print(f"pass 1  epochs={eps}  weighted holdout MSE={vl:.4f}  "
          f"rows={len(Xtr)}  d_in={Xtr.shape[1]}")

    df["pred_price"] = np.nan
    Xoh_a, Xnum_a, _, _ = design_matrix(df[p1], oh_cols, scaler)
    df.loc[p1, "pred_price"] = np.exp(predict(m1, np.hstack([E[p1], Xoh_a, Xnum_a])))
    df["pred_dollars"] = df["quantity"] * df["pred_price"]

    # ---- pass 2: mob/demob given the predicted subtotal of everything else
    sub = df[p1].groupby("ci")["pred_dollars"].sum().rename("subtotal").reset_index()
    df = df.merge(sub, on="ci", how="left")
    df["log_subtotal"] = np.log(df["subtotal"].clip(lower=1.0))

    p2 = is_ls_line.values
    if (p2 & tr_mask).sum() >= 50:
        NUM.append("log_subtotal")
        Xoh2, Xnum2, oh2, sc2 = design_matrix(df[p2 & tr_mask], None, None)
        X2tr = np.hstack([E[p2 & tr_mask], Xoh2, Xnum2])
        Xoh2e, Xnum2e, _, _ = design_matrix(df[p2 & te_mask], oh2, sc2)
        X2te = np.hstack([E[p2 & te_mask], Xoh2e, Xnum2e])
        m2, vl2, eps2 = train_mlp(
            X2tr, df.loc[p2 & tr_mask, "log_price"].values.astype(np.float32),
            df.loc[p2 & tr_mask, "w"].values.astype(np.float32),
            X2te, df.loc[p2 & te_mask, "log_price"].values.astype(np.float32),
            df.loc[p2 & te_mask, "w"].values.astype(np.float32),
            epochs=400, patience=40)
        print(f"pass 2  epochs={eps2}  rows={int((p2 & tr_mask).sum())} (mob/demob)")
        Xoh2a, Xnum2a, _, _ = design_matrix(df[p2], oh2, sc2)
        df.loc[p2, "pred_price"] = np.exp(predict(m2, np.hstack([E[p2], Xoh2a, Xnum2a])))
        df.loc[p2, "pred_dollars"] = df.loc[p2, "quantity"] * df.loc[p2, "pred_price"]
        NUM.pop()
    else:
        print("pass 2 skipped: too few mob/demob training rows")

    # ---- stage B, identical to A1
    pred_lowbid = df.groupby("ci")["pred_dollars"].sum().rename("pred_low_bid").reset_index()
    cc = con.copy()
    cc["cat"] = cc["work_type"].map(A1.v7_cat)
    cc["ly"] = cc["letting_date"].dt.year
    cc = cc.merge(pred_lowbid, on="ci", how="left")

    R = A1.fit_ee_ratio(cc[cc["ci"].isin(tr_ci)])
    cc["ratio"] = cc.apply(lambda r: A1.apply_ee_ratio(r, R), axis=1)
    cc["pred_ee"] = cc["pred_low_bid"] * cc["ratio"]

    hold = cc[cc["ci"].isin(te_ci)].copy()
    A1.report(hold, f"STAGE A2 (MiniLM + MLP) + B — holdout > {cutoff.date()}  (n={len(hold)})")

    out = os.path.join(DATA_DIR, "pred_embed.csv")
    hold[["contract_id", "cat", "letting_date", "n_bidders",
          "engineer_estimate", "low_bid", "pred_low_bid", "ratio", "pred_ee"]].to_csv(out, index=False)
    print(f"\nholdout predictions -> {out}")


if __name__ == "__main__":
    main()
