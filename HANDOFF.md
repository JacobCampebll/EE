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

## Log

### 2026-08-23 12:10 EDT — Grok

**Did:** Connected to GitHub as JacobCampebll. Reviewed the repo, PR #1, README, and file tree. No predictor / `index.html` / `compile_data.py` / `data.json` changes. Added this handoff log and a pointer in `README.md` so Claude and Grok can see each other's work.

**Touched:** `HANDOFF.md` (created), `README.md` (added "For Claude and Grok" pointer only)

**Next / open:** Waiting on Jacob for a concrete task. Candidates already in the README: parse `ALT` so alternates aren't double-priced; keep `index.html` in sync when `compile_data.py` runs; bridge estimates are weak.

**Don't redo:** Don't rewrite the pricing method. Don't strip inlined data from `index.html` without a rebuild path. Don't force-push this branch.

**Claimed:** none — idle until the next ask
