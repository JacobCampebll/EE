# Frozen holdout — August 20, 2026 Allen-won jobs

These three contracts are a **blind holdout**. The app must not know their
Engineer's Estimates, bids, or awards. Do not paste those numbers into
`index.html`, `data.json`, `compile_data.py`, or the accuracy table.

Score later by dropping the proposal PDF into the app and comparing *outside*
the repo (chat with Jacob, or a file that is not committed).

| Call | Contract | County | Proposal |
|---|---|---|---|
| 403 | 262155 | Clark — KY 1927 & US 60 resurfacing | https://transportation.ky.gov/Construction-Procurement/Proposals/403-CLARK-26-2155.pdf |
| 407 | 263024 | Jackson — various roads resurfacing | https://transportation.ky.gov/Construction-Procurement/Proposals/407-JACKSON-26-3024.pdf |
| 410 | 262234 | Lincoln — US 150 / KY 300 resurfacing | https://transportation.ky.gov/Construction-Procurement/Proposals/410-LINCOLN-26-2234.pdf |

Letting month to use when scoring: `2026-08`. Work type: PAVE.

Rules for both agents:

1. Do **not** fold these jobs into `ACCURACY`, `CURVES_RAW`, `LS_RATIOS`, or any
   other constant in `compile_data.py`.
2. Do **not** special-case these contract IDs in `index.html`.
3. Do **not** commit EE / bid / award dollars for these jobs.
4. Git history of this file from 2026-08-23 14:00 EDT still has a scored table.
   Do not resurrect it into the app.

## Parser layout (no labels)

These PDFs taught the parser, not the prices:

- Official table header is `LINE BID CODE ALT DESCRIPTION QUANTITY UNIT …`
- `Section:` is real (`0001 - PAVING` / `ROADWAY`, `0002 - DEMOBILIZATION`)
- Lump-sum rows wrap (`02650` / `02676` split across 2–3 lines)
- Full proposals also contain a **Material Summary** with different line numbers
  and per-road quantities. Parsing both double-counts asphalt. The app now
  reads only `PROPOSAL BID ITEMS` when that heading is present.

Layout fixtures (quantities only): `tests/fixtures/*.pbi.txt`. Run
`python3 tests/test_parse.py`.
