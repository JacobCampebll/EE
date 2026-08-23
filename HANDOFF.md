# HANDOFF — EE Predictor coordination log

**Read this first.** Agents append newest entry at the top. Claim a file in your entry *before* editing it. Same branch (`claude/github-integration-mz7dt1`), no force-push.

## Claims
| File | Holder | Notes |
|------|--------|-------|
| — | — | none held |

---

## 2026-08-23 ~19:20 EDT — Grok

**Done**
- Loaded **district unit prices** into `data.json` / inlined `DATA` from public KYTC `UBER_AUBP_Data 20250610.xlsx` (Construction Engineer Resource Center). Method: per (district, bid_code), median unit price in the newest year ≥2022; `n` = contract count that year. All 12 districts; only cells with n≥3 kept. `geo.county` still `{}` (AUBP has district only, no county).
- Cascade now hits district for most PAVE items on Allen districts (D07/D08/D11).
- **Blind re-score of August holdouts** (numbers live in chat only — not written into ACCURACY / fixtures):

| Job | src | Raw vs EE | Cal vs EE |
|-----|-----|-----------|-----------|
| Clark 262155 D07 | 23 dist / 1 state / 2 LS | **−1.8%** | +5.3% |
| Jackson 263024 D11 | 9 dist / 2 LS | **−1.5%** | +5.6% |
| Lincoln 262234 D08 | 15 dist / 10 state / 2 LS | +6.1% | +13.7% |

- Key finding: **raw is now the better point estimate** once district prices are on. PAVE bias (−7.2%) was fit against statewide under-prediction; with local prices the under-prediction shrinks and calibration overshoots. Do **not** invent a new bias constant here — re-fit from Supabase `bid_backtest_v6` with geo on, or gate calibration when `srcCounts.district+county` dominate.
- Lincoln still high: D08 asphalt (00190/00301) sits above statewide; partial state fallback on 10 items. County tables or a D08-specific check next.
- Restored this HANDOFF from PLACEHOLDER commit `9c1b9cc`.

**Not done / blockers**
- County-level tables (need county on bid rows — Supabase or join ContId→county).
- Bias re-fit with geo cascade.
- Do not merge PR #1 / flip default branch (user/Claude).

**Source note:** AUBP is contractor unit bids (same class as statewide averages already in the app), not EE line items. Updated through 2025-06-10 only.

---

## Prior entries

See git history for Claude 12:52 and earlier Grok parser/KAPI notes if this file was truncated.
