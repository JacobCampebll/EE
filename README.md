# KYTC Engineer's Estimate Predictor

Predicts the KYTC **Engineer's Estimate** for a highway contract from the Proposal Bid Items
PDF alone — before letting, before any bid tab exists.

The Allen Company · QC / Estimating

---

## For Claude and Grok

This repo is being worked by **Grok** and **Claude** in parallel.

**Before you change anything:** read [`HANDOFF.md`](HANDOFF.md). Append a dated note of what you did (newest first). Do not rewrite the other agent's entries. Claim a file before you edit it.

---

## What it does

Drop in a proposal PDF. The app parses the bid items table in the browser, prices every line
from KYTC's own published statewide average unit bid prices, applies the KYTC mobilization /
demobilization rules, and returns a predicted Engineer's Estimate with a confidence range.

The proposal PDF never leaves the device — parsing is client-side. Only the bundled price
data is used.

## Accuracy (620 KYTC projects backtested)

These figures are the **raw statewide basis** before calibration. The app's headline number
is now `raw × (1 − bias)` so it sits at the center of the range (paving was systematically
7.2% low; that is now applied to the number you read, not just the band).

Target is **±5%**, ideally **±2%**. We are not there yet — paving hit ±5% on 36% of jobs.

| Work type | Mean error | Median | Bias | Within ±5% | Within ±10% |
|---|---|---|---|---|---|
| Resurfacing | 9.5% | 7.5% | −7.2% | 36% | 64% |
| Alternates (micro / thinlay) | 7.7% | 6.6% | −3.9% | 38% | 68% |
| Grade & drain | 16.8% | 15.1% | −12.5% | 13% | 29% |
| Bridge | 46.2% | 18.9% | +32% | 8% | 17% |

Bias correction uses the already-measured backtest bias. It does **not** invent new
quantity-curve or lump-sum constants. A new held-out backtest is required before we can
claim the calibrated headline is inside ±5%.

Bridges are weak on purpose-honesty grounds: most bridge dollars sit in lump-sum items whose
statewide average mixes small deck patches with full rehabs, and there is no quantity to scale
by. The app flags this in the UI. Treat bridge output as order-of-magnitude only.

---

## Files

| File | Purpose |
|---|---|
| `index.html` | The whole app. Self-contained, no build step, no server. |
| `data.json` | Compiled price/rule data baked into `index.html` at build time. |
| `compile_data.py` | Regenerates `data.json` from the source KYTC files. |
| `HANDOFF.md` | Grok + Claude session log. Newest first. |

`index.html` already contains the data inline — `data.json` is kept in the repo so the
compiler output is reviewable in diffs.

## Deploying

Netlify: drag this folder to <https://app.netlify.com/drop>, or connect the repo and set the
publish directory to the repo root. No build command.

Local: open `index.html` directly. PDF parsing needs internet (pdf.js loads from CDN);
everything else works offline.

---

## How the prediction works

For each bid item:

1. **Look up the statewide average unit price** for that item code, newest year available
   (KYTC publishes one file per year, 2022–2025).
2. **Escalate** from the file year to the letting year using measured year-over-year drift.
   Asphalt items are handled separately: the binder cost is stripped out at the file year's
   KAPI index, the remaining residual is escalated, then binder is added back at the letting
   month's KAPI. This keeps asphalt from being double-counted for inflation.
3. **Apply the quantity curve** where one exists (43 high-dollar item codes). Unit prices fall
   as quantity rises. Quantity is pooled **per job, per item code** — a job split across six
   roads gets scale credit for the whole tonnage, not six small penalties.
4. **Lump-sum items** with a known ratio are priced as a percent of the work subtotal, not from
   a flat statewide average. Each LS code counts **once per job** regardless of how many roads
   it repeats across.
5. **Mobilization / demobilization** use the hard KYTC caps: mob ≤ 5% of the work subtotal,
   demob ≥ 1.5%. Verified exact against real bid tabs.
6. **Fuel and asphalt adjustment** items are pre-priced in the proposal and pass through.

The displayed range comes from that work type's own backtest spread, shifted by its measured
bias. The point estimate is the raw basis — **read the range, not the number**.

---

## Regenerating the data

Re-run when KYTC publishes a new year of average unit prices, a new Fuel & Asphalt
spreadsheet, or when enough new lettings are loaded to re-derive the ratios.

The source CSVs are **not in the repo**. Pass them in:

```bash
python3 compile_data.py --prices path/to/state_avg_all.csv --binder path/to/binder_prices.csv
# equivalent: EE_PRICES=... EE_BINDER=... python3 compile_data.py
# optional: --out path/to/data.json   (default: data.json next to the script)
```

If a source file is missing, the script exits 1 and prints the paths it tried plus the
expected columns. With no flags it also looks in the current directory, next to the script,
and (last resort) the original `/home/claude/...` session paths.

Then rebuild `index.html` with the new data inline — regenerating `data.json` alone does
not change app behavior. Claude owns `index.html`; leave an `HANDOFF.md` request rather
than editing it from this side.

Sources:

- **Average unit bid prices** (one .xlsx per year) —
  <https://transportation.ky.gov/Construction-Procurement/Pages/Average-Unit-Bid-Prices.aspx>
- **KAPI binder index / fuel index** — "Fuel and Asphalt Spreadsheet LET DT SEPT 2020 FORWARD" —
  <https://transportation.ky.gov/Construction/Pages/Fuel-and-Asphalt-Adjustments.aspx>

Constants at the top of `compile_data.py` (escalation chains, LS ratios, quantity curves,
accuracy figures) are derived in Supabase — project `allen-qc`, tables prefixed `bid_`,
view `bid_backtest_v6`. Update them there first, then paste in. Do not invent them locally.
Regenerating with the same source CSVs must not change a number in `data.json` except
`meta.built`.

---

## Known limitations

- **Alternates are not detected.** If a proposal has alternate sections (e.g. microsurfacing
  vs. thinlay), only one gets built — but the app prices *both* and will over-predict badly.
  Fix requires parsing the `ALT` column. Until then, delete the un-wanted alternate's lines or
  treat the result as high.
- **Bridges** — see accuracy table.
- **KAPI carry-forward.** KYTC publishes the binder index in arrears. For a letting later than
  the newest published month, the last known value is carried forward and labelled as such.
  Refresh the spreadsheet when a newer month posts.
- **Unpriced items contribute $0.** If an item code has no statewide average anywhere in
  2022–2025, it is flagged and the result is a floor, not a midpoint.
- Backtest ratios and curves were derived from the same 620 projects they are scored on, so
  fresh proposals will run somewhat worse than the table above.
