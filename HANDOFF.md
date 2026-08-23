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
