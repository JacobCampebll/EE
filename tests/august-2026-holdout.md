# August 20, 2026 holdout — Allen-won jobs

Out-of-sample test the app has never seen. Source: KYTC *Letting Results* PDF for
2026-08-20 plus the official **PROPOSAL BID ITEMS** pages in each proposal PDF.
Letting month used: `2026-08` (KAPI carried forward from 2026-04, last published).
Work type: PAVE. Parser used here is a clean read of the bid-items table (not the
in-browser pdf.js path). Engine is the current `index.html` formulas including
bias calibration.

None of these three have an `ALT` column populated. All three were sole-bidder.

| Job | Call | Contract | EE | Allen bid | App raw | App calibrated | cal vs EE |
|---|---|---|---:|---:|---:|---:|---:|
| Clark — KY 1927 & US 60, 5.13 mi resurfacing | 403 | 262155 | $1,204,141 | $1,097,724 (−8.8%) | $1,107,801 (−8.0%) | **$1,187,562** | **−1.4%** |
| Jackson — various roads, 2.04 mi resurfacing | 407 | 263024 | $351,647 | $353,032 (+0.4%) | $312,415 (−11.2%) | **$334,909** | **−4.8%** |
| Lincoln — US 150 bypass / KY 300, 2.75 mi resurfacing | 410 | 262234 | $1,211,090 | $1,226,612 (+1.3%) | $1,231,457 (+1.7%) | $1,320,122 | +9.0% |

Mean |error| vs EE: raw **6.95%** → calibrated **5.05%**. Hit ±5%: raw 1/3, calibrated **2/3**.
Allen's own bids averaged **3.5%** off the EE.

## Read this correctly

Calibration (PAVE +7.2%) is a 358-job average. It rescued Clark and Jackson, which
were systematically low like the backtest. Lincoln's raw basis was already +1.7% —
applying the same +7.2% overshot. **Do not retune bias, curves, or LS ratios from
n=3.** Log it, wait for more August district jobs.

Proposals:

- https://transportation.ky.gov/Construction-Procurement/Proposals/403-CLARK-26-2155.pdf
- https://transportation.ky.gov/Construction-Procurement/Proposals/407-JACKSON-26-3024.pdf
- https://transportation.ky.gov/Construction-Procurement/Proposals/410-LINCOLN-26-2234.pdf

Letting results:

- https://transportation.ky.gov/Construction-Procurement/Publications/2026-08-20/Letting%20Results.pdf
