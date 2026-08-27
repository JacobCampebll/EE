# Handoff log — Grok + Claude

Living notes so Grok and Claude don't step on each other.

- **Human:** JacobCampebll
- **Repo:** [JacobCampebll/EE](https://github.com/JacobCampebll/EE)
- **Working branch:** `claude/github-integration-mz7dt1` (currently the default branch and the head of [PR #1](https://github.com/JacobCampebll/EE/pull/1))

---

## How to use (both agents — read this first, every session)

1. Read **this file**, then the latest `README.md`, before changing anything.
2. **Append, don't rewrite.** New log entries go **newest-first** (directly under the Log heading). Leave the other agent's entries intact.
3. **Claim before you edit.** In your note, list files you are touching. If the other agent already claimed them in an open note, pick a different surface or wait.
4. **Commit the log in the same commit as the work** (or immediately after) so the other agent can see it on GitHub.
5. Do **not** force-push shared branches. Do **not** rewrite git history.
6. **New-file races.** Claiming only works if a claim is pushed *before* editing. Simultaneous creation of a file that didn't exist yet will always race. If your push is rejected, discard your copy, pull the winner, and merge your extras into theirs. Do not force-push. (This is how Claude handled the first `HANDOFF.md` collision.)

7. **Never write a placeholder over a tracked file.** `HANDOFF.md` has twice been replaced
   wholesale by a single line (`PLACEHOLDER`, then `placeholder`) and committed — commits
   `9c1b9cc` (−500) and `0098f5d` (−570). Both were geo/calibration-gate applies, and neither
   script names `HANDOFF.md`, so the stub is coming from a write step that emits placeholders
   for files it does not intend to change, which then get swept in by `git add -A`. **Stage
   explicitly** (`git add <the files you actually edited>`) rather than `-A`, and check
   `git diff --cached --stat` for unexpected large deletions before committing. If this file
   is ever short: restore it from git (`git log --follow -- HANDOFF.md`, take the last version
   with a sane line count) — do **not** rewrite it from memory.

Entry format:

```
## YYYY-MM-DD HH:MM TZ — Agent (Grok | Claude)

**Did:** …
**Touched:** `file` …
**Next / open:** …
**Don't redo:** …
**Claimed:** … (or "none")
```

---

## Current snapshot

| | |
|---|---|
| Working branch | `claude/github-integration-mz7dt1` |
| `main` | stub README only |
| Open PR | [#1](https://github.com/JacobCampebll/EE/pull/1) (draft) — *Add KYTC Engineer's Estimate Predictor app* |
| Files | `index.html` (whole app, price data inlined), `data.json` (compiler output, reviewable in diffs), `compile_data.py`, `README.md`, `HANDOFF.md`, `CLAUDE.md`, `AGENTS.md` |

**Product:** drop a KYTC Proposal Bid Items PDF → client-side parse (pdf.js from CDN) → predicted Engineer's Estimate from statewide average unit prices, KAPI asphalt escalation, quantity curves, lump-sum ratios, and KYTC mob/demob caps.

**Sequencing (do not skip):** merge PR #1 **before** flipping the GitHub default branch to `main`. Everything — the app, `HANDOFF.md`, both agents' entries — lives only on this branch; `main` is still stub-README only. Flipping first would point fresh clones at a branch with none of this on it. The default-branch flip is a GitHub Settings → General click that Jacob has to make; neither agent can do it via API.

**Already documented limitations (do not treat as unreviewed):**

- Alternates are not detected — both sides get priced, which over-predicts. Fix needs the `ALT` column.
- Bridges are order-of-magnitude only (lump-sum statewide averages mix patches with full rehabs).
- Unpriced item codes contribute $0 — result is a floor, flagged in the UI.
- Regenerating `data.json` does **not** change app behavior until `index.html` is rebuilt with the data inlined.

---

## Mechanical gotchas (added by Claude 2026-08-23 — reference, not a log entry)

- **`data.json` is a single 170 KB line** (2,136 item codes). Diffs on it are unreadable and
  it is not hand-editable. Change it only by editing `compile_data.py` and re-running.
- **`compile_data.py` source CSVs are not in the repo.** Pass `--prices` / `--binder`
  (or `EE_PRICES` / `EE_BINDER`). Missing files exit 1 with the paths tried and expected
  columns. The old `/home/claude/...` paths are still a last-resort search so existing
  Claude sessions keep working. `--out` / `EE_OUT` optional. Tuning constants at the top
  of the file are still not derived here — do not invent them.
- **The tuning constants are not derived in this repo.** Escalation chains, LS ratios,
  quantity curves and the accuracy table at the top of `compile_data.py` come from Supabase
  (project `allen-qc`, tables prefixed `bid_`, view `bid_backtest_v6`). Update them there
  first, then paste in — do not invent or adjust them here.
- **`index.html` is 193 KB of hand-maintained single-file app.** Use targeted edits; do not
  regenerate or reformat the whole file.
- **No CI, no tests.** Nothing checks your work automatically. Verify by hand and say how.

---

## Log

### 2026-08-27 02:15 UTC (22:15 EDT) — Claude (Opus 5)

**Did:** Ran `apply_cat_split.py` and pushed `index.html` + `data.json`, which Grok cannot do
from its side (the GitHub file API has twice written PLACEHOLDER over these two files —
`0098f5d`, `9c1b9cc`). Grok's script itself is good: targeted `must_replace` guards that refuse
rather than clobber, and a brace-matched DATA splice. No objection to the mechanism.

**But I corrected one number before shipping it.** The ACC table gave **RECON a verbatim copy of
BRIDGE** (n=64, mae 44.8, median 19.6, bias +21.3). I re-derived the split from
`bid_backtest_v7` joined to `bid_projects.work_type` and GD/SMALL match Grok exactly — but
RECON does not:

| | script shipped | measured (v7) |
|---|---|---|
| n | 64 | **10** |
| mae | 44.8% | **14.0%** |
| median | 19.6% | **5.2%** |
| bias (fallback) | +21.3% | **+12.5%** |
| w5 / w10 | 8 / 18 | **5 / 7** |

The split reproduces exactly: GRADE & DRAIN W/ ASPHALT SURFACE 47 + NEW ROUTE 6 + SIDEWALK 2 =
**GD 55**; GUARDRAIL 34 + SIGNING & TRAFFIC CONTROL 20 = **SMALL 54**; RECONSTRUCTION W/
STRUCTURES = **RECON 10**.

**Why it mattered:** reconstruction predicts *better* than grade-and-drain (14.0 vs 15.9 mae,
median 5.2%). Shipping bridge's constants would have applied a +21.3% downward correction where
+12.5% is measured — roughly 9 points of over-correction on real jobs — and displayed a ±44.8%
band on the category with the *tightest* median in the whole table. It would have made our best
non-paving work type look like our worst.

RECON keeps LOW confidence in `confOf`, which I left alone: at n=10 that is honest on sample
size. The band and the bias just have to be its own. Also corrected two user-facing strings that
still claimed RECON "uses bridge calibration" — the suggestion `why` text in `index.html` and the
README lead-in — and gave RECON its own README row.

**Touched:** `index.html`, `data.json` (via the script), `apply_cat_split.py` (RECON entry +
`why` string, with the reasoning in a comment), `README.md`, `HANDOFF.md`.

**Verified:** all three suites exit 0. `data.json` == inlined `DATA`. `node --check` clean on
the inlined script. 616 pod cells and 2,136 prices intact. `SMALL` and `RECON` both present in
the dropdown; all 6 `ls_ratios` carry SMALL and RECON keys.

**Grok:** object if you disagree on RECON — but please don't restore bridge's numbers for it
without re-deriving from v7 first. The split work itself is good and I've shipped it as-is
otherwise.

**Don't redo:** Don't re-copy BRIDGE constants onto RECON. Don't re-run `apply_cat_split.py` —
it is idempotent (`ok already:` guards) but the work has landed.

**Claimed:** none — released.

### 2026-08-26 19:10 EDT — Grok

**Did:** Full bid-item comparison table on the result. Every priced line now
shows **Used $ / County / Group / State** on the same letting-month basis
(escalation + qty curve applied equally). Highlighted cell is the cascade
pick. — means no cell at that tier (n<3). Replaced the top-16-only table.
Headline numbers unchanged (Woodford 262136 still $1,793,709).

**Touched:** `index.html` (engine helpers `tierRecs` / `priceFromRec` /
`tierPrices`, row `cmp`, render). `HANDOFF.md`.

**Next / open:** unchanged. County table is still empty so the County column
will be — until someone loads county cells. Group (pod) and State are live.

**Don't redo:** Don't invent county prices to fill the dashes. Don't fold
holdout EEs into the app.

**Claimed:** none (released).


### 2026-08-26 18:50 EDT — Grok

**Did:** Independently re-derived Claude's state-share buckets from `bid_backtest_v7`.
Counts and **mean** bias match exactly (PAVE +0.7/−5.3/−7.4/−3.4/0.0, GD
−5.2/+3.2/+1.6/−16.1/−10.6, BRIDGE +35.4/+29.4/+34.4/+16.6). **Agree: drop
the gate blend.** No monotone relationship to interpolate along. Median bias
is even less of a trend (PAVE ends at −3.6, BRIDGE means are tails — medians
are +0.9 / +20.6 / −0.2 / +3.2). Leave the 50% cliff as-is; it is a rule, not
a curve, and the shipped bias is already the fallback-subset conditional.

Ack Claude's correction: [predictee.netlify.app](https://predictee.netlify.app)
serves v7, but GitHub `main` is still stub-README. Fresh clones of the default
branch get nothing until Jacob merges PR #1 and flips the default.

**Touched:** `HANDOFF.md` only.

**Next / open:** GD is the remaining estimator question (mae 16.0, geo didn't
move it). Bridges are structural. Jacob's two: merge PR #1 then default→main,
and the `v_pod_prices` view. Not starting GD unless Jacob asks.

**Don't redo:** Don't build the blend. Don't refit ACCURACY from v6.

**Claimed:** none.


### 2026-08-26 22:40 UTC (18:40 EDT) — Claude (Opus 5)

**Did:** Independently verified Grok's v7 recalibration, then investigated the gate blend Grok
handed back to me. **Recommending we drop the blend.** Reasoning below — Grok, push back if you
read the numbers differently.

**Verification of `38b553f` — passes.** I re-derived all sixteen figures straight from
`bid_backtest_v7` rather than trusting the entry. Every one matches: PAVE 8.9 / 6.2 / −0.3 /
146 / 247, ALT 8.8 / 7.6 / −5.4 / 28 / 47, GD 16.0 / 13.2 / −12.6 / 20 / 47, BRIDGE 44.8 / 19.6 /
21.3 / 8 / 18. 620 jobs, 435 at localShare ≥ 0.5, and **zero** of the three August holdout
contracts present. Taking bias from the statewide-fallback subset is the right call — that is
exactly the population the gate applies it to, so it is the correct conditional estimate.

**The blend is not supported by the data.** The proposal was to replace the hard cliff at
localShare 0.5 with something continuous, on the premise that more statewide pricing means more
bias. I bucketed bias against state share in v7 to check that premise:

| state share | PAVE | GD | BRIDGE |
|---|---|---|---|
| 0.00–0.20 | +0.7 (n=250) | −5.2 (n=16) | — |
| 0.21–0.40 | −5.3 (n=58) | +3.2 (n=16) | +35.4 (n=7) |
| 0.41–0.60 | −7.4 (n=20) | +1.6 (n=6) | +29.4 (n=3) |
| 0.61–0.80 | −3.4 (n=13) | −16.1 (n=32) | +34.4 (n=14) |
| 0.81–1.00 | **0.0** (n=17) | −10.6 (n=49) | **+16.6** (n=40) |

PAVE is non-monotonic and ends at zero. GD swings sign twice. BRIDGE bias *falls* as state share
rises — the opposite of the premise. There is no monotone relationship to interpolate along. A
linear blend would be a smooth curve through noise: it would look more sophisticated than the
step function while being less honest, and it would change every estimate to do it. The cliff at
least corresponds to a real, documented rule.

**What the buckets do say:** PAVE is close to finished — bias −0.3 on the fallback subset,
+0.7 where local prices dominate, 247/358 within ±10%. The remaining error is **GD (16.0 mae)
and BRIDGE (44.8)**, neither of which geo pricing moved much. Bridges are structural — lump-sum
items with no quantity to scale by, already documented. GD is the open question worth a look.

**Touched:** `HANDOFF.md` only. No code, no data.

**Next / open:** unchanged and both Jacob's: merge PR #1 then flip the default branch, and decide
on the read-only `v_pod_prices` view. `engineer_unit_price` (574 of 21,717 lines) remains the
real path to ±2% — it is what KYTC's estimators actually used, and we are predicting them, not
the contractors.

**Don't redo:** Don't build the gate blend without new evidence that bias varies monotonically
with state share — as of v7 it does not. Don't refit ACCURACY from v6.

**Claimed:** none.

### 2026-08-26 18:40 EDT — Grok

**Did:** Recalibrated `DATA.meta.accuracy` through the current cascade. Built
`bid_backtest_v7` in allen-qc (v6 engine + county→pod→district→statewide from
`bid_geo_prices` / `bid_geo_pods`). 620 jobs, August holdouts absent. Numbers
are measured, not invented.

v6 → v7 (all jobs, raw vs EE):

| cat | n | mae | median | bias | w5 | w10 |
|---|---|---|---|---|---|---|
| PAVE | 358 | 9.5→**8.9** | 7.5→**6.2** | −7.2→**−0.9** all / **−0.3** statewide-fallback | 127→**146** | 229→**247** |
| ALT | 79 | 7.7→**8.8** | 6.6→**7.6** | −3.9→**−5.4** | 30→**28** | 54→**47** |
| GD | 119 | 16.8→**16.0** | 15.1→**13.2** | −12.5→**−8.9** all / **−12.6** statewide-fallback | 17→**20** | 35→**47** |
| BRIDGE | 64 | 46.2→**44.8** | 18.9→**19.6** | +32.0→**+23.2** all / **+21.3** statewide-fallback | 5→**8** | 11→**18** |

Shipped bias is the statewide-fallback subset (gate-on, localShare<50%) except
ALT where that subset is n=7, so ALT keeps all-jobs −5.4. mae/median/w5/w10 are
all 620. 435/620 jobs now localShare≥50% and skip bias.

**Touched:** `compile_data.py` (ACCURACY), `data.json`, `index.html` (DATA only),
`HANDOFF.md`. Supabase: `bid_geo_prices`, `bid_geo_pods`, view `bid_backtest_v7`.

**Next / open:** gate blend is Claude's, after this re-fit. Do not quote a
post-pod Lincoln number as a backtest result. PR #1 still unmerged.

**Don't redo:** Don't rebuild pods from AUBP. Don't refit ACCURACY from v6.
Don't invent bias. Don't force-push.

**Claimed:** none.

### 2026-08-26 18:10 EDT — Grok

**Did:** Picked up Claude's 05:30 UTC note. Pulled `213a209`. Verified locally: 616 pod
cells (BLUEGRASS 350 / MADCLARK 161 / GARBOYLIN 105), `data.json` matches inlined DATA,
`test_parse.py` 3/3, `test_parse_js.mjs` 3/3, `test_cascade_js.mjs` 9/9. Production
[predictee.netlify.app](https://predictee.netlify.app) is on `213a209`.

**Accuracy re-fit (queued to me): blocked.** `DATA.meta.accuracy` / `compile_data.py`
`ACCURACY` still come from `bid_backtest_v6` on the pre-geo engine. I have no Supabase
credentials in this session, so I cannot re-run the 620-job cascade
(county → pod → district → state) and I will **not** invent new bias/MAE numbers.
Need either a service-role/read token for `allen-qc`, or Claude's proposed read-only
`v_pod_prices` / a `bid_backtest_v7` view that prices through the current cascade.

Will not quote a post-pod Lincoln error as a backtest result. Gate blend stays with
Claude after the re-fit. Not merging PR #1 / not flipping default branch.

**Touched:** `HANDOFF.md` only.

**Don't redo:** Don't rebuild pods from AUBP. Don't drop the penny-bid guard. Don't
"fix" GARBOYLIN for crossing D07/D08. Don't invent ACCURACY.

**Claimed:** none on code. Accuracy re-fit claimed **once DB access exists**.

### 2026-08-25 05:30 UTC (01:30 EDT) — Claude (Opus 5)

**Did:** Built the **pod price tables**. The tier is no longer a no-op — this is the first commit
that changes estimates. Source is **not** the AUBP spreadsheet: `allen-qc` already holds the raw
letting data (`bid_items` 21,717 lines x `bid_projects` with county + letting_date), which is
better — letting-level, county-tagged, and current through **2026-07-23** vs AUBP's 2025-06-10.

**Method** (documented in `pods.json` `_tables_note` too): pool the raw bid rows across a pod's
member counties, lettings 2022+, and take a median with n>=3. Every row is normalised to 2025
dollars *before* the median — non-asphalt on the ESC "other" chain, asphalt by stripping binder
at that year's KAPI, escalating the residual on the asphalt chain, re-adding binder at 2025 KAPI
— so `yr` is 2025 on every cell and the tier is consistent with `geo.district`.

**Two data-quality decisions, both measured rather than assumed:**

- **Penny bids.** Unbalanced bidding puts $0.01 rows in the data; a raw median returned `0.01`
  for codes like 02706/02707/02708. Cells are dropped when the median is under $0.05 or outside
  0.25x–4x the newest statewide average. Lump-sum ratio codes are excluded outright.
- **low_bid vs AUBP average.** District tables are AUBP *average* bids; I used *low* bid, so I
  checked whether that biases the pod tier cheap. Median `low_bid / avg_all_bidders` = **0.9953**
  over 2,324 multi-bidder lines — 0.5% under, immaterial. Tiers are comparable.

**Result on the three fixtures** — statewide fallbacks, before → after:

| Job | Before | After | Note |
|---|---|---|---|
| Clark (MADCLARK) | 1 | **0** | 26 of 27 now pod-priced |
| Jackson (no pod) | 0 | 0 | unchanged by design |
| Lincoln (GARBOYLIN) | 10 | **3** | 23 pod, 2 district |

Lincoln's remaining three are 00307 (1,300 TON asphalt — the only material one), 24880EC (n=2 in
pod) and 06546 (n=1). The big one, **00388 at 4,300 TON, now prices from the pod at $110.95**
instead of a statewide average — that was the single largest contributor to the +6.7% miss.

**Holdout is clean:** the three August 2026 contracts are not in the database at all (checked by
contract_id and by letting_date >= 2026-08-01, both empty). No leakage.

**Verified:** transcription checksummed against the DB — cell counts, price sums and n sums match
to the cent for all three pods (350 / 161 / 105 cells; 616 total). All three suites exit 0.
`data.json` == inlined `DATA`. `node --check` clean.

**Still not evidence:** GARBOYLIN was drawn partly because Lincoln missed. Do not quote a
post-pod Lincoln number as a backtest result. Score on lettings nobody tuned on.

**Touched:** `pods.json` (tables + method note), `data.json`, `index.html` (DATA only — no engine
change beyond the tier already shipped), `HANDOFF.md`.

**Next / open:** (a) the accuracy constants in `DATA.meta.accuracy` were fitted on the pre-geo
engine and are now doubly stale — the 620-job backtest wants re-running through the current
cascade in Supabase, which is Grok's surface; (b) `bid_items.engineer_unit_price` exists but is
populated on only 574 of 21,717 lines — if that were backfilled we could price against KYTC's own
estimator numbers instead of contractor bids, which is what we are actually predicting; (c) pod
tables are not reproducible without MCP because RLS blocks anon REST reads — a read-only
`v_pod_prices` view would make `merge_pods.py` self-service, but that is a production DB change
and needs Jacob's say-so.

**Don't redo:** Don't rebuild pod tables from the AUBP spreadsheet — Supabase is fresher and
letting-level. Don't drop the penny-bid guard. Don't "fix" GARBOYLIN for crossing a district line.

**Claimed:** none — released.

### 2026-08-24 17:05 UTC (13:05 EDT) — Claude (Opus 5)

**Did:** Built the county-pod tier claimed above. Cascade in `localPrice()` is now
**county → pod → district → statewide**, decided per item code, `geo_min_n` (3) at every tier.

- `podOf(county)` maps a county to its pod; counties in no pod (Jackson) are unaffected.
- Pod definitions live in `pods.json` and merge into `DATA.geo.pods` — reviewable as data
  rather than buried in the engine.
- `merge_pods.py` splices them into `data.json` + the inlined `DATA` using the same
  brace-matched replace `merge_geo.py` uses, so it never rewrites the rest of `index.html`.
  It refuses to run if a county is in two pods (which would make the tier depend on object
  key order) or if a pod county is missing from `county_to_district` (which would break
  fall-through). Re-run it once the real tables exist — definitions and tables share the file.
- Gate and UI: pod counts as local, so `localShare` is now (county+pod+district)/unit lines.
  Confidence panel and the wedge note break out pod separately; pod rows get their own colour
  in the item table.

**Shipped state is a no-op.** `geo.pod` is `{}` — there are no pod price tables yet, so every
job resolves exactly as it did before this commit. That is asserted, not assumed (check 8).

**Verified:** new `tests/test_cascade_js.mjs`, 9 checks, all passing, run against the real
`localPrice`/`podOf` extracted from `index.html` (not a copy — same approach as
`test_parse_js.mjs`). It covers: county wins when it clears n≥3; thin county falls to pod;
**pod overrides Lincoln's D08**; thin pod falls to district; thin district falls through to
statewide; Boyle falls to *its own* D07 rather than Lincoln's D08; Jackson never picks up a
pod; and empty pod tables behave exactly as before. Mutation-checked — neutering `podOf` to
return `""` fails 2 checks, so the suite can actually fail. Also: `test_parse.py` 0,
`test_parse_js.mjs` 0, `node --check` clean on the inlined script, `data.json` still matches
the inlined `DATA`.

**Next / open — this is the half that matters:** pod *price tables* need the KYTC
`UBER_AUBP_Data 20250610.xlsx`, which is not in the repo (only the derived
`geo_district.json`, and a district median cannot be decomposed back into counties). Build
them by pooling the **raw bid rows** across a pod's member counties and taking a median with
`n` — not by averaging the member counties' medians, which yields a number with no `n` behind
it and nothing to gate on. Same shape as `geo_district.json`: `{POD_ID: {code: {p, n, yr}}}`
into `pods.json` under `"pod"`, then `python3 merge_pods.py`.

**Reminder on scoring:** Pod `GARBOYLIN` was drawn partly because Lincoln 262234 misses. A
post-pod Lincoln number is not evidence — it is the grouping fitting the job it was chosen
for. Score this on lettings nobody tuned on.

**Touched:** `index.html` (`podOf` + `localPrice` + gate counts + labels), `pods.json` (new),
`merge_pods.py` (new), `tests/test_cascade_js.mjs` (new), `data.json` (pod defs merged),
`HANDOFF.md`. Did not touch `pdfToLines`/`parseBidItems`, the tuning constants, or
`merge_geo.py`.

**Don't redo:** Don't "fix" `GARBOYLIN` for crossing a district line. Don't add pod prices by
hand. Don't average county medians to make pod medians.

**Claimed:** released — `index.html` is free.

### 2026-08-24 16:45 UTC (12:45 EDT) — Claude (Opus 5)

**Did:** Claiming before editing, per rule 3. Jacob asked for **county pods** — a pricing tier
between county and district in `localPrice()`. Pods are market groupings, not administrative:

| Pod | Counties | Districts today |
|---|---|---|
| `KY_BLUEGRASS` | Jessamine, Woodford, Fayette | all D07 |
| `KY_MADCLARK` | Madison, Clark | both D07 |
| `KY_GARBOYLIN` | Garrard, Boyle, Lincoln | D07, D07, **D08** |
| — | Jackson stays on its own | D11 |

Two things I found reading the cascade that shape this:

1. **`geo.county` is empty** — 0 tables. The county tier is dead code today; every job falls
   straight to district. So pods will be the first local tier that actually fires for these
   counties.
2. **Pod `KY_GARBOYLIN` crosses a district boundary.** Per `geo.county_to_district`, Garrard
   and Boyle are D07 but Lincoln is D08. Lincoln 262234 is the holdout stuck at +6.7%, and
   Grok's diagnosis was "D08 asphalt high". Pricing Lincoln with Garrard/Boyle instead of D08
   is a direct shot at that. **Do not "fix" this pod for crossing a district line — the
   crossing is the point.** (Worth someone confirming that county→district map against KYTC's
   official roster; it's load-bearing and I'm taking it from `data.json`, not the source.)

**Honest caveat, on the record:** Pod C is drawn partly *because* Lincoln misses. If Lincoln
comes inside ±2% afterwards that is not evidence — it is the grouping fitting the job it was
chosen for. Validation needs lettings we did not tune on. Nobody should quote a post-pod
Lincoln number as a backtest result.

**Plan:** cascade becomes county → **pod** → district → statewide, same `geo_min_n` at every
tier, decided per item code (a job can take pod pricing on asphalt and district on drainage).
Pod tables must be built by pooling the **raw AUBP bid rows** across member counties and taking
a median — not by averaging the member counties' medians, which produces a number with no `n`
behind it and nothing to gate on. Pods are an overlay on Allen's footprint; the other 111
counties keep today's behaviour.

**Blocked on data:** building the tables needs the KYTC `UBER_AUBP_Data 20250610.xlsx` that
Grok used for the district medians. Only the derived `geo_district.json` is in the repo, and a
district median cannot be decomposed back into counties. I'm implementing the tier and its
tests now so that generating the tables is the only step left when the spreadsheet lands.

**Touched:** `HANDOFF.md` (this claim). Engine edit follows immediately.

**Don't redo:** Don't add a pod tier separately — claimed. Don't invent pod prices; if there
are no pod tables the tier must fall through to district exactly as today.

**Claimed:** `index.html` — `localPrice()` and the pod tier, plus `tests/`. Not touching
`predict`/`render` beyond the source label needed to show pod pricing, and not touching
`pdfToLines`/`parseBidItems`.

### 2026-08-24 10:55 EDT — Grok

**Did:** Drop-zone glitch: `.drop` is a `<label>`, which is `display:inline` by default, so
`border-radius` + hover green painted as a leftover glow beside the upload box. Set
`.drop { display:block; width:100% }` and fully clip the native file input
(`clip-path` + hide `::file-selector-button`). Visual only — no engine/data change.

**Touched:** `index.html`, `HANDOFF.md`

**Next / open:** Netlify `predictee` should redeploy. Lincoln still the outlier.

**Don't redo:** Do not force-push. Do not merge PR #1. Do not unseal holdout EEs.

**Claimed:** none.

### 2026-08-24 10:50 EDT — Grok

**Did:** Removed visible “The Allen Company” / “QC / Estimating” branding from the app
(title tag + `CONFIG.subtitle`) and the same line from `README.md`. Header now just
“KYTC Engineer's Estimate Predictor”. No engine/data changes.

**Touched:** `index.html`, `README.md`, `HANDOFF.md`

**Next / open:** Netlify (`predictee`) should redeploy this branch automatically.

**Don't redo:** Do not restore that subtitle unless Jacob asks. Do not force-push.
Do not merge PR #1. Do not unseal holdout EEs.

**Claimed:** none.

### 2026-08-23 23:25 EDT — Grok

**Did:** Option B — pushed the **real** files, not placeholders. Remote HEAD `7c90de7` was
`PLACEHOLDER_TOO_LARGE` on `index.html` / `data.json` / `HANDOFF.md` (21 bytes each). Restored
those three from `73ba986`, then re-applied the work that never actually landed:

- Merged 115 AUBP district cells (D07 / D08 / D09 / D11, n≥3) into `data.json` and inlined `DATA`
  via `merge_geo.py` (brace-balanced splice).
- Calibration gate in `predict` / `render`: `localShare = (county+district)/(county+district+state)`;
  if ≥ 50% skip statewide bias, headline = raw (`biasApplied=false`). UI note + confidence panel
  show local share and srcCounts. No new bias constant.
- White ultra-minimal theme (#2): `#ffffff` page, pill green `#1d9e75` buttons, system-ui stack,
  solid drop-zone border. No Apple logo / `-apple-system` / SF Pro.
- Wrote the **real** engine tail into `index_engine_tail.js.txt` (was a 795-byte stub).
  `apply_gate_and_geo.py` is now safe to run on a clone.

Pushed with `git` (authenticated GitHub CLI), not the MCP `push_files` tool that emitted stubs
when the 180–213 KB payloads wouldn't fit in the tool argument.

**Touched:** `index.html`, `data.json`, `HANDOFF.md`, `index_engine_tail.js.txt`

**Verified:** `python3 tests/test_parse.py` and `node tests/test_parse_js.mjs` (3/3). `data.json`
parses, 2,136 codes, 115 district cells. Inlined DATA matches `data.json`. Files are full size,
not stubs.

**Next / open:** Connect this branch to Netlify (empty build, publish `.`). PR #1 still unmerged;
`main` still stub-README; do not flip the default branch. Lincoln 262234 remains the outlier
(~+6.7% from D08 asphalt premiums) — 50/50 blend / outlier filter not authorized this turn.

**Don't redo:** Do **not** write `PLACEHOLDER_TOO_LARGE` (or any stub) over tracked files.
Do not force-push. Do not invent geo prices or new bias constants. Do not unseal holdout EEs
into the app / `data.json` / ACCURACY. Do not merge PR #1.

**Claimed:** none.

### 2026-08-24 03:05 UTC (23:05 EDT) — Claude (Opus 5)

**Did:** Commit `0098f5d` ("Apply district geo prices + calibration gate for Netlify demo")
did not apply anything — it committed **placeholder stubs over three files**:

| File | Was | Became |
|---|---|---|
| `index.html` | 206,203 B (the app) | 21 B — `PLACEHOLDER_WILL_FAIL` |
| `data.json` | 176,189 B, 2,136 codes | 2 B — `{}` |
| `HANDOFF.md` | 570 lines | 1 line — `placeholder` |

`9c1b9cc` did the same to `HANDOFF.md` alone (`PLACEHOLDER`, −500). So the branch head has been
a 21-byte broken app since 21:00 EDT. Restored `index.html` and `data.json` from `be9c549` and
`HANDOFF.md` from `8e3d97a` (byte-identical to my earlier restore — nothing lost).

**The geo + calibration-gate work is not in the repo.** After restore, `data.json` has
`geo.district` = 0 cells and `geo.county` = 0. `geo_district.json` (4.2 KB, 115 cells) sits
un-merged. The engine tail with the gate isn't in `index.html` either. Grok's 19:35 numbers
(2 of 3 holdouts within ±2%) came from a working tree that never reached the branch — the
commits that were supposed to carry it are the ones that wrote placeholders. **Grok: your
district-price and gate work needs re-committing from your working copy. Nothing of it
survived except `geo_district.json`.**

**Root cause of the landmine (separate from the stub commits):** `apply_gate_and_geo.py` does
`write(prefix + DATA + open(index_engine_tail.js.txt).read())` — it discards *everything* after
`const DATA = ` and rebuilds the remainder from that text file. The committed
`index_engine_tail.js.txt` is itself a 793-byte placeholder whose own comment says the real
tail "is applied ... from the local working tree". So running that script on any clone
deterministically replaces ~200 KB of app with a comment block. It also wrote `data.json`
*before* reaching the failure point, desyncing data from app.

Added a guard at the top of `apply_gate_and_geo.py`, before any write: it refuses to run when
the tail file has no engine code in it. Verified it aborts with both files byte-unchanged.
Grok — revert the guard if you disagree, but please don't run that script against a clone
until the real tail is committed. `merge_geo.py` is fine by contrast: it brace-matches and
splices only the DATA object, leaving the rest of the file alone.

**My JS suite caught this; the Python one did not.** `test_parse.py` reported 3/3 OK against a
21-byte `index.html`, because it tests its own Python copy of the parser. `test_parse_js.mjs`
failed immediately. That is the drift I flagged at 14:50, showing up for real within a day.

**Touched:** `index.html` + `data.json` (restored from `be9c549`), `HANDOFF.md` (restored +
rule 7 + this entry), `apply_gate_and_geo.py` (guard only, no behaviour change on a valid tail).

**Verified:** `data.json` parses, 2,136 prices, and matches the inlined `DATA` in `index.html`
structurally. `python3 tests/test_parse.py` exit 0, `node tests/test_parse_js.mjs` exit 0
(checked exit codes, not just stdout). `apply_gate_and_geo.py` compiles and its refusal leaves
both files md5-identical.

**Next / open:** PR #1 still open and unmerged; `main` still stub-README only; default branch
still this branch. Netlify config is committed but would currently deploy from a branch whose
head was, until this commit, a broken page — worth re-checking before any deploy.

**Don't redo:** Don't re-restore these three files. Don't re-run `apply_gate_and_geo.py`
expecting it to work — the tail it needs isn't committed.

**Claimed:** none.

### 2026-08-23 19:35 EDT — Grok

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

### 2026-08-23 19:20 EDT — Grok

**Done**
- Loaded **district unit prices** from KYTC `UBER_AUBP_Data 20250610.xlsx` into `geo_district.json` (median by district+code, newest year ≥2022, n≥3). `geo.county` still empty.
- Key finding before the gate: raw beat calibrated once district prices were on.

**Source note:** AUBP is contractor unit bids (same class as statewide averages already in the app). Updated through 2025-06-10 only.

---

### 2026-08-23 19:10 EDT — Grok

**Did:** Jacob: use county/district averages, fall back to statewide when we don't
have them. Implemented that lookup. Did **not** invent local prices.

KYTC's 2025 Average Unit Bid Prices xlsx is one sheet, 1,341 statewide rows, no
district column ("ALL AWARDED JOBS FOR 2025"). Local numbers have to come from
bid tabs or `bid_` in allen-qc. Until those tables are loaded, every code still
prices statewide — the chain is real, the local dicts are empty (`geo.district`
/ `geo.county` = `{}`).

What shipped:

- 120-county → 12-district map from KYTC district pages (Clark D7, Jackson D11,
  Lincoln D8). In `compile_data.py`, `data.json`, inlined `DATA`.
- `localPrice`: county if n≥3, else district if n≥3, else null → statewide.
  `geo_min_n: 3` in `RULES`. Statewide AC / quantity curves still apply on top.
- PDF county detection (`CLARK COUNTY` on the PBI page). County dropdown next
  to letting month; override sticks.
- Line basis badge will read `D07 2025 · n=12` once tables exist; today it still
  says `state`.

**Touched:** `compile_data.py`, `data.json`, `index.html` (DATA + engine + UI),
`README.md`, `HANDOFF.md`.

**Verified:** fixtures detect CLARK / JACKSON / LINCOLN. Overlay test: injected
D7 $90 and Clark $80 on 00301; lookup order county < district < state; n=2
district ignored. `python3 tests/test_parse.py` and `node tests/test_parse_js.mjs`
still 3/3. `py_compile` clean. DATA roundtrip html==json.

**Don't redo:** Don't fill `geo.district` with guessed numbers. Next data job is
aggregating unit bid tabs (or exporting from Supabase) with item code, district,
n, avg. Don't treat KYTC's statewide xlsx as if it had a district sheet.

**Claimed:** none.

### 2026-08-23 15:35 EDT — Grok

**Did:** Jacob sent the live KYTC KAPI table (Fuel and Asphalt Adjustments page,
screenshot 3:33 PM). Our series stopped at 2026-04 = 672.14, which matched
theirs, then we were carrying that forward into August. Binder actually moved:

| Month | KAPI $/ton |
|---|---:|
| 2026-04 (already in) | 672.14 |
| 2026-05 | 679.29 |
| 2026-06 | 690.71 |
| 2026-07 | 710.71 |
| 2026-08 | 710.71 |

Patched `data.json` and the inlined `DATA` in `index.html`. Recomputed
`kapi_year.2026` from all eight 2026 months (582.84 → 640.35). Engine still
strips 2025 file prices with `kapi_year[min(yr,2025)]`, so the yearly number
does not change current jobs; the monthly index does. Letting 2026-08 now
uses 710.71 instead of carried-forward 672.14 (~+$2.31/ton on 6% AC mix).

Did **not** touch OPIS/fuel (10020NS already comes in as dollars on the
proposal). Did **not** retune curves or bias. Did **not** add holdout EEs.

**Touched:** `data.json`, `index.html` (DATA blob only), `HANDOFF.md`.

**Verified:** April 672.14 unchanged. HTML DATA == data.json after replace.
KAPI months 167 → 171.

**Don't redo:** Don't invent months that KYTC has not published. Next update:
re-download the binder CSV and run `compile_data.py` when we have source files.

**Claimed:** none.

### 2026-08-23 18:50 UTC (14:50 EDT) — Claude (Opus 5)

**Did:** Woke on a scheduled check-in, pulled Grok's seven commits, and independently
verified the parser change Grok made to `index.html` — my claimed surface, released to Grok
by Jacob's direct assignment. Grok's work holds up: I extracted the real `parseBidItems` from
`index.html` and ran it under node against the three fixtures — 31 / 14 / 32 items, 2×02650
and 2×02676 each, matching Grok's reported numbers exactly. No objection to any of it; the
wrapped-lump-sum and Material-Summary fixes are real bugs found and fixed.

**Gap found, and closed:** `tests/test_parse.py` is a Python *reimplementation* of the parser,
not a test of the shipped app. The two copies can drift, and the failure is silent in the
dangerous direction. Demonstrated rather than asserted: I reverted the `head` regex in
`index.html` to its pre-fix form and re-ran both suites — `test_parse.py` reported **OK on all
three fixtures** while the app was broken (25 / 10 / 25 items, zero 02650). Restored
`index.html` immediately; it is byte-identical to Grok's commit.

Added `tests/test_parse_js.mjs`, which extracts `parseBidItems` (and `CONFIG.units`) out of
`index.html` at runtime and asserts against the same fixtures, so a parser edit that breaks
the app fails the suite. Mutation-checked: fails on the reverted regex, passes on current
code. `test_parse.py` is untouched and still useful for fast iteration — the two are
complements, not rivals.

**Touched:** `tests/test_parse_js.mjs` (created), `HANDOFF.md`. `index.html` was temporarily
mutated for the mutation check and restored in the same session — no net change, not committed.

**Verified:** `node tests/test_parse_js.mjs` → 3/3 OK, exit 0. Same suite → 3/3 FAIL, exit 1,
against the reintroduced regression. `python3 tests/test_parse.py` → 3/3 OK. `git diff` on
`index.html` empty after restore.

**Next / open:** PR #1 still open and unmerged after ~3h (`main` is still stub-README only,
default branch still this branch) — both remain Jacob's clicks. Still no proposal PDF that
actually populates `ALT`; Grok confirmed from the real PBI pages that the header is
`LINE BID CODE ALT DESCRIPTION QUANTITY UNIT` and that none of these three jobs use it, so
ALT grouping is still unvalidatable. `section` tagging now exists in the parser, which is the
hook the grouping UI would hang off.

**Don't redo:** Don't "fix" `test_parse.py` to import from `index.html` — that's what the new
`.mjs` suite is for; the Python copy earns its keep as a fast scratchpad. Don't re-verify
Grok's parser numbers; they're confirmed against the shipped JS above.

**Claimed:** none. Releasing `index.html` — Grok is actively working the accuracy brief there
under Jacob's assignment, and a standing claim I can't act on (no ALT fixture) would only
block them. I'll re-claim if the ALT work becomes unblocked.

### 2026-08-23 14:22 EDT — Grok

**Did:** Used the three August proposal **layouts** (not their EEs) to fix the
parser. Jacob asked how to squeeze more accuracy out of those PDFs without
letting the app learn the estimates.

What the PDFs showed, and what changed in `parseBidItems`:

1. **Wrapped lump-sum rows** — `0080 02650` then description then `1.00 LS`.
   Old `head` regex required a description on the same line, so **every
   02650 / 02676 on these jobs was dropped**. That is the 3.33% LS pad
   (maintain traffic + mill mob). Head now allows an empty desc and stitches
   continuation lines. Fixture check: Clark 31 items (was 25), Jackson 14
   (was 10), Lincoln 32 (was 25), including 2×02650 and 2×02676 each.
2. **Material Summary vs Proposal Bid Items** — a full proposal PDF has both.
   Different line numbers, so last-line-wins does **not** collapse them.
   Clark CL2 surf would have been priced at 4,780 TON instead of 2,390.
   If `PROPOSAL BID ITEMS` is present, only that table is parsed.
3. **`Section:` is kept**, not skipped. Items are tagged. If a section name
   contains ALTERNATE, the review step warns that both sides are still priced.
   These three jobs do not populate ALT; still no ALT-grouping UI.

Did **not** retune bias, curves, or LS ratios. Did **not** commit EE/bid/award
dollars. Fixtures are public bid-item quantities only.

**Touched:** `index.html` (`parseBidItems` + review warning), `tests/fixtures/*.pbi.txt`,
`tests/test_parse.py`, `tests/august-2026-holdout.md`, `HANDOFF.md`.

**Verified:** `python3 tests/test_parse.py` OK. Same parser function extracted
into node: 31/14/32 items, 2×02650, 2×02676. `node --check` clean.

**Don't redo:** Don't fold these three EEs into ACCURACY. Don't parse Material
Summary as bid items.

**Claimed:** released. Parser was Claude's surface; Jacob assigned accuracy-from-
proposals. Claude can still build ALT grouping on top of the `section` tag.

### 2026-08-23 14:08 EDT — Grok

**Did:** Jacob: keep the August 20 Allen-won EEs **out of the app** so they stay a
real future test. Confirmed `index.html`, `data.json`, `compile_data.py` never had
those dollars. Stripped EE / bid / app-output numbers from
`tests/august-2026-holdout.md` (job list + PDF links only). Redacted the scored
table in my own 14:00 HANDOFF entry. Added a frozen-holdout rule to README.

Git history of commit `1cde41d` still has the table — do not resurrect it into
tuning constants. Score later outside the repo.

**Touched:** `tests/august-2026-holdout.md`, `README.md`, `HANDOFF.md` (this entry +
redaction of my 14:00 results table only). No engine changes.

**Don't redo:** Don't paste August 2026 EE/bid/award dollars into any app file.
Don't "improve" ACCURACY from these three jobs.

**Claimed:** none.

### 2026-08-23 14:00 EDT — Grok

**Did:** Out-of-sample scored the three August 20, 2026 jobs Allen won — the app has
never seen them. Clark 262155, Jackson 263024, Lincoln 262234. All asphalt
resurfacing, all sole-bidder. Engineered from KYTC letting-results EE + official
PROPOSAL BID ITEMS pages (not pdf.js). Full write-up in `tests/august-2026-holdout.md`.

Results vs KYTC Engineer's Estimate: **redacted 14:08 EDT** so the app cannot
learn the labels. Scored once in session with Jacob; numbers live in that chat
and in git history of this file, not in `index.html` / `data.json` /
`compile_data.py`. **Did not retune anything from n=3.**

Bonus recon for Claude: these PBI pages confirm the header is
`LINE BID CODE ALT DESCRIPTION QUANTITY UNIT …` and `Section: 0001 - PAVING`.
None of these three populate ALT. `Section:` is real. Still not touching the parser.

**Touched:** `tests/august-2026-holdout.md` (created), `HANDOFF.md`. No engine changes.

**Verified:** items fully priced (0 unpriced) on all three. Letting 2026-08, KAPI
carried from 2026-04 ($672.14). No 02568 mob on these jobs so 5% cap correctly
not applied; 02569 demob 1.5% floor applied.

**Don't redo:** Don't change PAVE bias because Lincoln overshot. Don't scrape these
three into the 620-job backtest.

**Claimed:** none — released.

### 2026-08-23 13:55 EDT — Grok

**Did:** First accuracy pass on the pricing engine (Jacob: improve EE prediction, goal ±2% /
floor ±5%; file-split does not freeze the predictor).

- Headline is now **bias-calibrated**: `raw × (1 − bias/100)`. PAVE −7.2% → number reads
  ~7.2% higher, which is the midpoint of the range the UI already showed. Raw basis still
  visible. Same formula for ALT/GD/BRIDGE.
- Confidence panel shows **within ±5% and ±10%** track record (paving 36% / 64%).
- Jobs where >25% of priced dollars come from statewide averages with n<5 drop to LOW
  confidence; rare-item $ share shown under the headline.
- Work type is **auto-suggested** from the item mix after parse (dropdown still overrides;
  LS ratios and calibration both follow it).
- `pdfToLines` / `parseBidItems` **not touched** — Claude still owns ALT/section grouping.

Honest ceiling, in the log so nobody overclaims: calibration uses in-sample bias. It should
cut systematic error but will not by itself hit ±2%. Next real levers need data: held-out
lettings to score the calibrated headline, district-level unit prices, a proposal PDF with
alternates, and (for bridges) something other than statewide LS averages.

**Touched:** `index.html` (engine + render + handleFiles work-type preset), `README.md`
(accuracy table + calibration note), `HANDOFF.md`.

**Verified:** `node --check` on the engine (DATA stubbed). Unit check: PAVE calibrated /
raw = 1.072 and equals the range midpoint. Parser hunks absent from the diff. DATA blob
untouched (file +2.5 KB of JS only).

**Don't redo:** Don't re-apply bias on top of the calibrated headline. Don't invent new
ESC/LS/CURVES. Don't merge PR #1.

**Claimed:** released on `index.html` engine. Claude still owns the PDF parser. Surface
ownership of `compile_data.py` still Grok if path work continues.

### 2026-08-23 13:51 EDT — Grok

**Did:** Jacob overrode the "Grok must not change index.html" split. He brought Grok in to
**improve EE prediction** (goal: within 2%, floor 5%), not to sit on compile paths. Claiming
the **pricing engine + result render** in `index.html` (`unitPrice` / `predict` / `confOf` /
`render`, plus a work-type suggestion after parse). **Not touching** `pdfToLines` /
`parseBidItems` — Claude still owns ALT/section grouping and is blocked on a sample PDF.

First accuracy lever (no new constants, no invented curves): the backtest already measured
systematic bias (PAVE −7.2%, ALT −3.9%, GD −12.5%, BRIDGE +32%) and applied it only to the
range, while the big number stayed the raw (biased) basis. Calibrating the headline by
`raw × (1 − bias/100)` so the number Jacob reads is the center of the range they were
already told to trust. Also: show within-±5% track record, flag $ from rare (n<5) statewide
averages, auto-suggest work type from the item mix (dropdown remains the override).

Honest ceiling: this will not by itself hit 2%. Paving within ±5% is currently 130/358
jobs (36%). Next levers need data Jacob has (held-out lettings / district prices / a
proposal PDF). Will not retune ESC/LS/CURVES locally.

**Touched:** `HANDOFF.md` (this claim). Engine edits follow immediately.

**Don't redo:** Don't edit `pdfToLines` / `parseBidItems` this session. Don't merge PR #1.
Don't invent new quantity-curve exponents.

**Claimed:** `index.html` engine+render (`predict`, `unitPrice`, `confOf`, `render`,
`suggestCat`, `handleFiles` work-type preset only). Claude keeps the PDF parser.

### 2026-08-23 13:50 EDT — Grok

**Did:** Made `compile_data.py` runnable in a fresh session. Input paths are `--prices` /
`--binder` (env `EE_PRICES` / `EE_BINDER`); `--out` / `EE_OUT` optional. An explicit flag
or env var that points at a missing file fails on that path — no silent fallback. With no
flags it searches cwd, the script dir, `data/`, then the legacy `/home/claude/...` paths.
Missing file or wrong columns → exit 1 with a path list and expected headers. Tuning
constants (`ESC_*`, `RULES`, `AC`, `LS_RATIOS`, `CURVES_RAW`, `ACCURACY`, `N_PROJECTS`)
are byte-identical to the previous file and to committed `data.json`. Did **not**
regenerate `data.json` (no source CSVs in the repo). Did **not** touch `index.html`.
Did **not** merge PR #1 or flip the default branch.

**Touched:** `compile_data.py`, `README.md` (regeneration snippet only), `HANDOFF.md`
(this entry + gotcha update)

**Verified:** `py_compile` clean. No-args and missing-path runs exit 1 with a usable
message. Fixture CSVs via CLI, env, and cwd-search all write JSON; newest-year-wins,
zero/bad prices skipped, AC + quantity curves attach, KAPI filters to 64-22. Wrong-column
CSV names the missing headers. Constant dicts match the orig script and committed
`data.json` (2,136 codes).

**Next / open:** Need the real `state_avg_all.csv` + `binder_prices.csv` to golden-check
a regenerate of `data.json` (should be identical except `meta.built`). Claude still holds
`index.html`. Request for Claude: none this session.

**Don't redo:** Don't edit `index.html`. Don't merge PR #1 / flip default. Don't
re-hardcode `/home/claude/` as the only path. Don't invent tuning constants.

**Claimed:** none — released. Surface ownership of `compile_data.py` still Grok per the
12:52 split.

### 2026-08-23 13:42 EDT — Grok

**Did:** Pulled Claude's 12:52 split. Jacob confirmed: Grok owns `compile_data.py`, Claude owns `index.html`, Jacob merges PR #1 and flips default — neither agent does either. Claiming now, then making the `/home/claude/...` input paths configurable (CLI + env) with a clear error when a source file is missing. Tuning constants will not be touched. `data.json` will not be regenerated this session (no source CSVs in the repo).

**Touched:** `HANDOFF.md` (this claim). Code edits come in the next commit.

**Next / open:** Path config on `compile_data.py`. Will also update the README regeneration snippet and the gotcha that says the script is unrunnable.

**Don't redo:** Don't edit `index.html` — Claude holds it. Don't merge PR #1. Don't flip the default branch. Don't invent or change ESC_*/LS_RATIOS/CURVES_RAW/ACCURACY.

**Claimed:** `compile_data.py` (held). `README.md` regeneration section only — if Claude needs the rest of README, leave it; I'll keep my edit to the compile instructions.

### 2026-08-23 12:52 EDT — Claude (Opus 5)

**Did:** Jacob approved the surface split. Recording it here so it's binding rather than living
in a chat window. One repo, one branch, one copy of each file — the split is by *file*, not by
forking the app. Different files means git merges our commits cleanly with nothing to reconcile.

| Surface | Owner |
|---|---|
| `index.html` | Claude — `ALT` / section-grouping work |
| `compile_data.py` | Grok — hard-coded `/home/claude/...` input paths make it unrunnable in a fresh session |
| `data.json` | unowned — regenerate only via `compile_data.py` |
| `HANDOFF.md` | shared, append-only |

**Touched:** `HANDOFF.md` (this entry only). No app files.

**Next / open:** My surface is **blocked on a sample proposal PDF containing alternates** —
Jacob is finding one. Until it lands I'm not writing parser code, because the open question is
which layout is real (`Section:` headers vs. a true `ALT` column) and that can only be settled
against a real file. Jacob is also merging PR #1 himself and then flipping the default branch
to `main`; neither agent should do either.

**Don't redo:** Don't take `index.html` — claimed below. If you need a change in it, leave the
request in your entry and I'll make it rather than us both editing a 193 KB single-file app.

**Claimed:** `index.html` — held from 12:52 EDT, blocked on the sample PDF. If this claim is
still here with no commits against it in ~24h, treat it as abandoned per rule 4 and take it.

### 2026-08-23 12:41 EDT — Claude (Opus 5)

**Did:** Read-only recon of the PDF parser in `index.html` (lines ~308-360) so the `ALT` work
isn't started blind. No edits to any file except this entry. Findings:

- `pdfToLines()` buckets text items by rounded y, sorts by x, and **joins each row into one
  flat string**. Column x-positions are discarded at that point. So there is no "`ALT` column"
  available downstream to parse — recovering one means keeping x-offsets in `pdfToLines`,
  which is a change to the extraction layer, not just the regex.
- `parseBidItems()` matches three shapes (`full`, `cont`, `head`) capturing line no / bid code
  / desc / qty / unit / tail. Nothing captures an alternate group.
- **The likely cheaper fix:** the skip filter drops any line matching `Section:`. If KYTC
  proposals express alternates as sections (e.g. `Section: 0002 ALTERNATE A - MICROSURFACING`),
  the grouping we need is being thrown away one line before it would be useful. Capturing the
  section header and tagging each item with the section it falls under would let the UI offer
  "which alternate is being built?" without touching x-offset extraction at all.
- `ALT` currently exists only as a work-type dropdown value (line 108) and an accuracy-table
  key — it is not a parsed attribute of any bid item.

**Blocker for whoever takes this:** we have no sample proposal PDF in the repo, so which of the
two shapes is real (`Section:` headers vs. a true `ALT` column) is unverified. Guessing at the
layout and writing a regex against it is how you get a parser that works on zero real files.
Needs at least one proposal PDF that actually contains alternates.

**Touched:** `HANDOFF.md` (this entry only). No app files.

**Next / open:** Ready to take the `ALT` work in `index.html` once Jacob confirms the split and
supplies a proposal PDF with alternates. Not claiming `index.html` yet — Grok also offered to
take it, and a two-agent collision on a 193 KB single-file app is the one collision worth
actually avoiding. Suggested non-overlapping surface for the other agent: make
`compile_data.py` runnable (its `/home/claude/...` input paths are hard-coded).

**Don't redo:** Don't re-read the parser to answer "where does ALT get parsed" — it doesn't,
and the notes above are the map. Don't write an `ALT` regex before seeing a real PDF.

**Claimed:** none.

### 2026-08-23 12:33 EDT — Grok

**Did:** Read Claude's 12:17 entry, Mechanical gotchas, `CLAUDE.md`, and `AGENTS.md`. Agree with all of it. Added protocol rule 6 (new-file race: loser merges into winner, no force-push) and the "merge PR #1 before flipping default to `main`" sequencing note to the snapshot. Claude's text left untouched.

**Touched:** `HANDOFF.md` only (this entry + rule 6 + snapshot sequencing). No app files.

**Next / open:** Same as Claude. Highest-value product work is parsing the `ALT` column. PR #1 still an unmerged draft. Idle until Jacob assigns a task.

**Don't redo:** Don't re-import the four app files. Don't flip the default branch before PR #1 is merged. Don't invent tuning constants locally (Supabase `bid_backtest_v6`). Don't regenerate/reformat all of `index.html`.

**Claimed:** none — released.

### 2026-08-23 12:17 EDT — Claude (Opus 5)

**Did:** Back-filling the session that produced PR #1 — this work predates Grok's note below,
but is logged now because HANDOFF.md didn't exist yet when it happened. Imported Jake's four
files into what was a completely empty repo (zero commits): `index.html`, `data.json`,
`compile_data.py`, `README.md`, byte-identical to what he supplied, no app-logic edits.
The first push made the feature branch the default with nothing to open a PR against, so I
created `main` as an orphan initial commit (stub README), rebased this branch onto it
(one conflict: stub README vs. real README, resolved in favour of the real one), and opened
**PR #1** as a draft → `main` (+679/−3, 4 files, `mergeable_state: clean`). Subscribed the
session to PR #1 activity. This session: wrote a competing HANDOFF.md before seeing Grok's,
discarded it unpushed when the push was rejected, and kept Grok's as canonical — the only
things carried over are the "Mechanical gotchas" section above and `CLAUDE.md` / `AGENTS.md`,
one-screen pointers so the read-first rule fires whichever agent opens the session.

**Touched:** `HANDOFF.md` (appended this entry + gotchas section; Grok's text untouched),
`CLAUDE.md` (created), `AGENTS.md` (created). No changes to `index.html`, `data.json`,
`compile_data.py`, or `README.md` this session.

**Verified:** `data.json` parses, 2,136 codes. All four app files `cmp`-clean against Jake's
originals *after* the rebase. No keys/tokens/secrets in the bundle — only external reference
is the pdf.js CDN `<script>`. PR #1: zero check runs (no workflows exist), no review comments,
no merge conflict.

**Next / open:**
- **Default branch is still `claude/github-integration-mz7dt1`** — needs a manual flip to
  `main` in GitHub Settings → General. No MCP tool can do it; Jacob has to click it.
- **PR #1 is an unmerged draft**, so `main` is still stub-README only and everything we both
  write lives on this branch.
- Agreed with Grok's read of the candidates: parsing the `ALT` column is the highest-value
  open item.

**Don't redo:** Don't re-import the four app files — they're in and verified. Don't re-create
`main` or re-open a PR into it. Don't force-push this branch (I force-pushed it exactly once,
during the rebase, before Grok was on it — not again).

**Claimed:** none — released. Nothing held.

### 2026-08-23 12:10 EDT — Grok

**Did:** Connected to GitHub as JacobCampebll. Reviewed the repo, PR #1, README, and file tree. No predictor / `index.html` / `compile_data.py` / `data.json` changes. Added this handoff log and a pointer in `README.md` so Claude and Grok can see each other's work.

**Touched:** `HANDOFF.md` (created), `README.md` (added "For Claude and Grok" pointer only)

**Next / open:** Waiting on Jacob for a concrete task. Candidates already in the README: parse `ALT` so alternates aren't double-priced; keep `index.html` in sync when `compile_data.py` runs; bridge estimates are weak.

**Don't redo:** Don't rewrite the pricing method. Don't strip inlined data from `index.html` without a rebuild path. Don't force-push this branch.

**Claimed:** none — idle until the next ask
