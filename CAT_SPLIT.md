Grok cannot push `index.html` / `data.json` through the GitHub file API.
Those two files are ~240 KB / ~204 KB (price tables inlined). The same API
previously wrote `PLACEHOLDER` / `PLACEHOLDER_TOO_LARGE` over the live app
(commits 0098f5d, 9c1b9cc) and took predictee down.

Apply locally instead:

    python3 apply_cat_split.py
    git add index.html data.json compile_data.py
    git commit -m "Split GD into G&D, guardrail/signing, reconstruction"
    git push

The script was tested against this branch's `index.html` on 2026-08-26.
