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
| Files | `index.html` (whole app, price data inlined), `data.json` (compiler output, reviewable in diffs), `compile_data.py`, `README.md` |

**Product:** drop a KYTC Proposal Bid Items PDF → client-side parse (pdf.js from CDN) → predicted Engineer's Estimate from statewide average unit prices, KAPI asphalt escalation, quantity curves, lump-sum ratios, and KYTC mob/demob caps.

**Already documented limitations (do not treat as unreviewed):**

- Alternates are not detected — both sides get priced, which over-predicts. Fix needs the `ALT` column.
- Bridges are order-of-magnitude only (lump-sum statewide averages mix patches with full rehabs).
- Unpriced item codes contribute $0 — result is a floor, flagged in the UI.
- Regenerating `data.json` does **not** change app behavior until `index.html` is rebuilt with the data inlined.

---

## Mechanical gotchas (added by Claude 2026-08-23 — reference, not a log entry)

- **`data.json` is a single 170 KB line** (2,136 item codes). Diffs on it are unreadable and
  it is not hand-editable. Change it only by editing `compile_data.py` and re-running.
- **`compile_data.py` will not run as-is.** It reads absolute paths under `/home/claude/`
  (`state_avg_all.csv`, `bidpred/binder_prices.csv`) that do not exist in a fresh session.
- **The tuning constants are not derived in this repo.** Escalation chains, LS ratios,
  quantity curves and the accuracy table at the top of `compile_data.py` come from Supabase
  (project `allen-qc`, tables prefixed `bid_`, view `bid_backtest_v6`). Update them there
  first, then paste in — do not invent or adjust them here.
- **`index.html` is 193 KB of hand-maintained single-file app.** Use targeted edits; do not
  regenerate or reformat the whole file.
- **No CI, no tests.** Nothing checks your work automatically. Verify by hand and say how.

---

## Log

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
