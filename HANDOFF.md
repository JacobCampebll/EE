# HANDOFF — EE Predictor coordination log

**Read this first.** Agents append newest entry at the top. Claim a file in your entry *before* editing it. Same branch (`claude/github-integration-mz7dt1`), no force-push.

## Claims
| File | Holder | Notes |
|------|--------|-------|
| — | — | none held |

---

## 2026-08-23 ~19:35 EDT — Grok

**Done**
- **Calibration gate:** when ≥50% of unit-priced lines come from county/district tables, skip the statewide PAVE bias and use **raw** as the headline (`biasApplied: false`). UI note + range band updated. No new bias constant invented.
- Merged `geo_district.json` into `data.json` and inlined `DATA` in `index.html` (brace-balanced replace).
- Fixed `merge_geo.py` to use balanced-brace DATA splice (not greedy regex).
- Blind re-score after gate (chat only):

| Job | localShare | bias? | Headline vs EE |
|-----|------------|-------|----------------|
| Clark 262155 D07 | 96% | off | **−1.8%** (±2%) |
| Jackson 263024 D11 | 100% | off | **−1.5%** (±2%) |
| Lincoln 262234 D08 | 60% | off | +6.7% (still out) |

- 2 of 3 holdouts inside ±2% on the headline. Lincoln remains the problem (D08 asphalt high + 10 state fallbacks).

**Not done**
- County tables; Lincoln/D08 deep-dive; bias re-fit on geo-aware backtest in Supabase.
- Do not merge PR #1 / flip default branch.

---

## 2026-08-23 ~19:20 EDT — Grok

**Done**
- Loaded **district unit prices** from KYTC `UBER_AUBP_Data 20250610.xlsx` into `geo_district.json` (median by district+code, newest year ≥2022, n≥3). `geo.county` still empty.
- Key finding before the gate: raw beat calibrated once district prices were on.

**Source note:** AUBP is contractor unit bids (same class as statewide averages already in the app). Updated through 2025-06-10 only.

---

## Prior entries

See git history for Claude entries and earlier parser/KAPI notes.
