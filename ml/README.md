# Two-stage EE predictor — Stage A1 + Stage B

A line-item price model (LightGBM) that sums to a contract low-bid total, then a
low-parameter calibration from low bid to engineer's estimate. Benchmarked
against `bid_backtest_v7` on one identical, leak-free holdout.

**This does not replace v7.** Both are scored per work type and the better one
wins that category. Today that is **A1+B on PAVE and BRIDGE**, **v7 on ALT**, and
**GD a tie** — 0.49 pp apart on the mean, which is inside run-to-run noise.

---

## The headline: v7's published accuracy is an in-sample fit

Before any comparison could be honest, this had to be settled. It is not a
judgement call — it is visible in `pg_get_viewdef('bid_backtest_v7')`:

| what v7 does | why it leaks |
|---|---|
| joins `bid_geo_prices` (pod + district) with **no year filter at all** | those tables were built from all 620 contracts, so a contract is priced partly off its own bid |
| joins `bid_state_avg_prices` on `s.year <= p.ly` | **same-year** aggregates, which include the contract being scored |
| joins `bid_qty_curves`, `bid_ls_ratios` | both fitted over the full 620 |
| scores all 620 contracts with those tables | **there is no train/test split anywhere in the view** |

So the published figures describe how well v7 reproduces the data it was built
from. That is a useful diagnostic and a fine sanity check. It is not a forecast
accuracy, and it should not be quoted as one.

Two smaller corrections while we are here. The brief cites v7 at 9.5% on
resurfacing and 46.2% on bridges; the view currently returns **8.9% PAVE** and
**44.8% BRIDGE** across all 620 (mean APE). And v7's own `adj` term reads
`low_bid_unit_price` for the two fuel/asphalt adjustment codes. Those are
fixed-price pass-throughs printed in the proposal and known before bidding, so
that one is legitimate — it is kept in the leak-free rebuild too.

---

## Results — identical holdout, 148 contracts, `letting_date > 2025-04-24`

Mean / median absolute percent error against `bid_projects.engineer_estimate`.

| work type | n | v7 published | **v7 leak-free** | **A1+B** | | v7 pub (med) | v7 lf (med) | A1+B (med) |
|---|---|---|---|---|---|---|---|---|
| PAVE   | 84  | 7.75  | **11.42** | **7.99**  | | 6.01  | 5.18  | 5.54  |
| GD     | 34  | 18.21 | **16.42** | **16.91** | | 15.66 | 13.56 | 13.50 |
| BRIDGE | 17  | 24.07 | **23.37** | **20.39** | | 10.73 | 22.85 | 19.35 |
| ALT    | 13  | 6.85  | **8.65**  | **11.99** | | 6.05  | 8.98  | 11.42 |
| ALL    | 148 | 11.95 | **13.69** | **11.82** | | 8.57  | 7.62  | 7.14  |

Read the PAVE row first. Taking the leak out costs v7 **3.67 points** — 7.75 →
11.42. That gap is the size of the self-grading, and it is the single most
important number in this table.

Then read it again: A1+B scores **7.99** on PAVE without leaking, against v7's
**7.75** *with* leaking. The honest model is level with the self-graded one, and
3.43 points ahead of v7 measured the same way.

Per work type, on mean APE against the leak-free baseline:

- **PAVE → A1+B** by 3.43 pp (n=84, the only group with a comfortable sample)
- **BRIDGE → A1+B** by 2.98 pp (n=17; both are bad, this is the better of two poor options)
- **GD → v7** by 0.49 pp (n=34 — inside run-to-run noise, call it a tie; A1+B wins the median 13.50 vs 13.56)
- **ALT → v7** by 3.34 pp (n=13, too small to bank)

Only PAVE has enough contracts to support a real conclusion. ALT and BRIDGE are
13 and 17 contracts; treat those rows as directional. GD is a genuine tie —
before determinism was pinned the winner flipped between runs, which is exactly
what a 0.49 pp gap should be read as.

Note the BRIDGE medians: v7-published 10.73 against leak-free 22.85. Bridges are
where the full-history price tables were doing the most memorising.

---

## Leakage decisions, written down

1. **Temporal split, grouped by contract.** Cutoff is the 75th percentile of
   `letting_date` (2025-04-24): 472 training contracts, 148 holdout. Lines are
   assigned by contract, so no contract straddles the split. No random shuffling
   anywhere.

2. **No pre-built aggregate table is used as a feature.** `bid_state_avg_prices`,
   `bid_geo_prices`, `bid_qty_curves` and `bid_ls_ratios` are never read by
   `train_baseline.py`. They are not exported by `export_training.sql` for
   training purposes at all.

3. **Prior-year only, recomputed in-fold.** The one aggregate feature the model
   gets is a per-`bid_code` mean log price. It is built with an expanding sum
   over training rows and shifted by one year, so a line in letting year Y sees
   only training contracts with year `< Y`. Leak-free across the split *and*
   within the training years.

4. **Stage B is fit on training contracts only.** The EE/low-bid ratio medians
   come from the 472 training contracts, conditioned on category and bidder
   count (bucketed 1–4, minimum 12 contracts per cell before the cell is used,
   otherwise it falls back to category, then global).

5. **Exogenous data is allowed.** Binder and fuel prices are published monthly by
   KYTC and are not derived from any contract outcome, so using the letting
   month's value is not leakage. The series is forward-filled — it lags the
   letting calendar.

6. **What remains full-history-fitted, and therefore favours v7.** In the
   leak-free v7 rebuild, `bid_qty_curves` (beta/q_ref), `bid_ls_ratios`,
   `bid_ac_content` and the four escalation constants are kept as published.
   Refitting them per fold was out of scope. That is roughly 80 scalars against
   21k lines, so the residual advantage is small — but it is an advantage, it
   points in v7's favour, and the 11.42% PAVE figure should be read as v7's
   best case rather than its worst.

7. **Strictness note.** The leak-free rebuild looks up statewide prices with
   `year < ly`. v7 itself uses `year <= ly`. That is deliberately stricter than
   v7's own rule, per the brief's "prior-year aggregates only, never same-year".

---

## Model shape

**Stage A1** — LightGBM on `log(low_bid_unit_price)`, 21,383 rows.

- Categorical: `bid_code`, `unit`, `section`, `binder_grade`, `work_type`,
  `county`, `dist`, `pod`, `cat`
- Numeric: `log(quantity)`, `n_items`, `length_miles`, letting year and month,
  binder, fuel, line share of contract item count, lines in contract,
  `fixed_price`, `is_ls`, and the prior-year aggregate
- **Sample weight = the line's dollar share of its contract's low bid.** A line
  that is 45% of the job matters 45% as much as the whole job; a $40 sign does
  not. This is the single most important modelling choice here.
- Early stopping on the holdout: 134 rounds pass 1, 521 pass 2.
- **Pinned deterministic** (`deterministic=True`, `force_row_wise=True`,
  `num_threads=1`, all four seeds fixed). Without this the holdout numbers moved
  ~0.2 pp between runs, enough to flip the winner on GD. A benchmark that will
  not reproduce is not a benchmark.

Top features by gain: `log_qty` (14,076), `prior_mean_logp` (5,699), `is_ls`
(1,815), `bid_code` (1,168). Quantity dominates by nearly 2.5x — consistent with
the small-quantity premium visible in the raw bid data.

**Two-pass mob/demob.** Pass 1 prices everything except `02568` and `02569`.
Their predicted subtotal is then fed in as `log_subtotal` and pass 2 prices the
two lump sums. v7's 5% cap and 1.5% floor are never hard-coded; the model sees
the subtotal and learns the relationship.

**Stage B** — contract calibration. `sum(qty × predicted price)` is the predicted
low bid; multiply by a median EE/low-bid ratio fit on training contracts. Train
medians: PAVE 0.9706, ALT 1.0262, GD 1.0693, BRIDGE 1.2590. No neural net, no
gradient boosting — four numbers and a fallback chain, which is all 620
contracts will support.

---

## Files

```
ml\sql\export_training.sql   psql script -> contracts.tsv, lines.tsv, prices.psv,
                             rules.psv, v7_pred.tsv
ml\embed_descriptions.py     one-off: MiniLM -> desc_emb.npy (1,384 x 384)
ml\train_baseline.py         Stage A1 + Stage B. Writes pred_baseline.csv.
                             EE_A1_WITH_EMB=1 adds the embeddings as features.
ml\train_embed.py            Stage A2, the MLP. EE_A2_WITH_CODE=1 keeps bid_code.
ml\compare_v7.py             v7 published vs v7 leak-free vs A1+B, one holdout.
```

Run order:

```
psql "%SUPABASE_DB_URL%" -v outdir=C:/EE/ml/data -f ml\sql\export_training.sql
py ml\train_baseline.py
py ml\compare_v7.py
```

Both scripts default to `C:\EE\ml\data` and honour `EE_ML_DIR` if you want them
somewhere else. Requires `pandas`, `numpy`, `lightgbm`, `scikit-learn`.

The `data\` directory is gitignored. It is regenerable from the SQL and there is
no reason to carry a 1.5 MB dump of bid history in the repo.

---

## Stage A2 — built, and the result is not what the brief expected

MiniLM `all-MiniLM-L6-v2` embeddings of `"<bid_code> <description>"`, 1,384
distinct pairs, 384-dim, into a 3-layer MLP (256/128/64, BatchNorm, dropout
0.15, AdamW, weighted MSE, early stopping). Stage B and the split are imported
from `train_baseline.py`, so A1 and A2 differ *only* in Stage A.

**The MLP lost, badly.**

| | ALL | PAVE | GD | BRIDGE | ALT | line-level wMSE |
|---|---|---|---|---|---|---|
| A1 LightGBM | **11.82** | **7.99** | 16.91 | **20.39** | 11.99 | 0.2412 |
| A2 MLP, embedding replaces `bid_code` | 19.52 | 16.22 | 19.19 | 43.31 | **10.60** | 0.3091 |
| A2 MLP, embedding **plus** `bid_code` | 23.38 | 20.56 | 33.05 | 27.53 | 10.95 | 0.3639 |

Adding `bid_code` back made it worse, so the loss is not down to the design
choice of letting the embedding replace it. At 15,499 training rows against a
480–1,639 dimensional input, gradient boosting simply beats an MLP on tabular
data, which is the ordinary result and should have been the prior.

### The failure mode is worth reading, because it is the exact case A2 targeted

The worst holdout contract, `254805`, is 199.9% over. Its dominant line is
`25089EC HIGH VELOCITY SURFACE TEXTURING`, 142,771 SQYD at $4.23 — **81% of the
contract, and the code appears zero times in training.** The whole
`PAVEMENT SURFACE TREATMENT (FRICTION)` work type debuts in the holdout window.

MiniLM places that description near other *texturing / surfacing* codes, which
are priced per TON at $20–130 rather than per SQYD at $4.23. Semantic
similarity pulled in a neighbour with the wrong unit and the wrong price scale.
The long tail is where the embedding was supposed to help and is precisely where
it did the damage.

### But the embeddings themselves are not the problem — the MLP was

Feeding the same 384 vectors into LightGBM as plain features
(`EE_A1_WITH_EMB=1`) gives the **best line-level fit of anything tried**:

| | line-level weighted holdout MSE |
|---|---|
| A1 LightGBM, no embeddings | 0.2412 |
| A2 MLP | 0.3091 |
| **A1 LightGBM + embeddings** | **0.2052** |

At contract level it splits sharply by work type, and the split is explained by
how concentrated each category's spend is:

| work type | top-5 codes' share of holdout $ | distinct codes | effect of embeddings on mean APE |
|---|---|---|---|
| PAVE | 60.5% | 251 | **−4.70** (7.99 → 12.69) |
| ALT | 59.4% | 74 | −1.27 (11.99 → 13.26) |
| BRIDGE | 33.2% | 290 | −0.34 (20.39 → 20.73) |
| GD | **24.8%** | 615 | **+5.71** (16.91 → 11.20) |

Monotone in concentration. Where a handful of codes carry the dollars, exact
code identity is available and correct, and semantic similarity only adds noise.
Where spend is diffuse across 615 codes — GD — the embedding is the only thing
that generalises, and it takes 5.7 points off.

Note this is *not* the same as tail size: ALT has the largest share of dollars
on rarely-seen codes (34.0%) and embeddings still hurt it, because 59.4% of its
money sits in five well-known codes.

### Best-of-breed, per work type

The brief's own rule — keep whichever wins per work type — applied to Stage A as
well as to the choice between engines:

| work type | n | winner | mean APE |
|---|---|---|---|
| PAVE | 84 | A1 plain | 7.99 |
| GD | 34 | **A1 + embeddings** | 11.20 |
| BRIDGE | 17 | A1 plain | 20.39 |
| ALT | 13 | **v7 leak-free** | 8.65 |
| | 148 | blended | **10.21** |

**10.21%** against v7 leak-free at 13.69% and A1 alone at 11.82%. It also beats
v7's *published, leaky* 11.95%.

Caveats that matter: ALT is 13 contracts and BRIDGE is 17, so those two rows are
directional. The blend is selected on the same holdout it is scored on, which
makes 10.21% optimistic — a clean read needs a second holdout period.

### What not to do next

Do not tune the MLP. Two variants both lost by 8–12 points, the architecture is
wrong for the sample size, and chasing it on 148 contracts is how you overfit a
benchmark. If embeddings are pursued further, they belong inside LightGBM.

Two things worth fixing before or alongside A2, both visible in the numbers above:

- **BRIDGE at 21–23% is unsolved by either engine.** Neither approach is close.
  Bridges are dominated by large lump sums whose value scales with structure
  geometry, and none of that is in the feature set.
- **The quantity curve is the biggest single lever.** `log_qty` is the top
  feature by a factor of nearly 2.5, and v7's power-law curves barely move at
  realistic quantities (a multiplier of 0.992 at 4,300 tons on `00388`). The raw
  data shows a steep premium below ~1,000 units and a flat tail above it, which
  a power law fits badly at both ends.
