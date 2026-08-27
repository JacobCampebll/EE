# KYTC Engineer's Estimate Predictor

Predicts the KYTC **Engineer's Estimate** for a highway contract from the Proposal Bid Items
PDF alone — before letting, before any bid tab exists.

---

## Deploy (Netlify)

This is a **static** site: open `index.html` or publish the repo root. No `npm run build`.

1. [Netlify](https://app.netlify.com) → Add new site → Import from GitHub → `JacobCampebll/EE`
2. **Branch to deploy:** `claude/github-integration-mz7dt1` (app lives here; `main` may still be a stub until PR #1 is merged)
3. **Build command:** leave empty, or `true`
4. **Publish directory:** `.` (repo root)
5. Deploy — you get a `*.netlify.app` URL

`netlify.toml` is already in the repo with these settings.

**Demo tip:** drop any KYTC Proposal Bid Items PDF. County is auto-detected when present; override in the UI. Predicted EE uses statewide averages, district unit prices where available (D07/D08/D09/D11), KAPI asphalt escalation, and a calibration gate when local prices dominate.

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

## How prediction works

1. **Look up a unit price** for that item code, newest year available. Order:
   **county → district → statewide**. County/district averages are used only when `n ≥ 3`
   samples exist. District tables (from KYTC AUBP) cover Allen districts D07/D08/D09/D11 today;
   other areas fall back to statewide. The proposal's county is detected from the PDF (override in the dropdown).
2. **Escalate** with KAPI (asphalt) or a year-chain factor (other items) to the letting month.
3. **Apply the quantity curve** where one exists (high-dollar item codes). Unit prices fall
   for large quantities and rise for small ones.
4. **Lump-sum ratios** for traffic control / mill-text mobilization scale with the job total.
5. **Mob / demob** caps per KYTC practice (mob ≤ 5%, demob ≥ 1.5%).
6. **Calibration:** if most unit prices came from statewide tables, apply the measured work-type
   bias (e.g. PAVE −0.3% after pods). If most came from district/county/pod tables, the headline stays **raw**
   so we do not double-correct.

## Accuracy (620 KYTC projects backtested)

Figures are from `bid_backtest_v7` (county → pod → district → state). Guardrail and signing
are no longer mixed into grade-and-drain, and reconstruction with structures is measured
separately.

| Work type | n | Mean error | Median | Bias (fallback) | Within ±5% | Within ±10% |
|---|---:|---|---|---|---|---|
| Resurfacing | 358 | 8.9% | 6.2% | −0.3% | 41% | 69% |
| Alternates (micro / thinlay) | 79 | 8.8% | 7.6% | −5.4% | 35% | 59% |
| Grade & drain / new route | 55 | 15.9% | 13.7% | −12.9% | 18% | 40% |
| Guardrail / signing | 54 | 16.6% | 13.9% | −16.2% | 9% | 33% |
| Bridge | 64 | 44.8% | 19.6% | +21.3% | 13% | 28% |
| Reconstruction w/ structures | 10 | 14.0% | 5.2% | +12.5% | 50% | 70% |

Reconstruction is measured on its own, not borrowed from bridge — it predicts better than
grade-and-drain. At n=10 the sample is thin, so the app still rates it LOW confidence on
sample size alone.

Target is **±5%**, ideally **±2%**.

## Files

| File | Role |
|------|------|
| `index.html` | Whole app (UI + engine + inlined price data) |
| `data.json` | Same price data, reviewable in diffs |
| `geo_district.json` | District unit-price table (merged into data on deploy) |
| `compile_data.py` | Regenerates `data.json` from KYTC source CSVs |
| `netlify.toml` | Static publish settings for Netlify |
| `HANDOFF.md` | Agent coordination log |

## Known limitations

- **Alternates are not detected.** Both sides may be priced → over-predict.
- **Bridges** are order-of-magnitude only.
- **District tables** are contractor bid medians (AUBP), not EE line items — can run hot in competitive districts.
- **Unpriced items** contribute $0 and are flagged.
- Source CSVs for `compile_data.py` are not in the repo (pass via flags / env).
