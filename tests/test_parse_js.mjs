#!/usr/bin/env node
// Runs the REAL parseBidItems out of index.html against the layout fixtures.
//
// test_parse.py mirrors the same logic in Python, which is useful for quick
// iteration but can silently drift from the shipped app. This one extracts the
// function from index.html itself, so a parser edit that breaks the app fails
// here even if the Python copy still passes.
//
// Fixtures are public bid-item quantities only — no EE / bid / award dollars.
//
//   node tests/test_parse_js.mjs
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// Pull `function parseBidItems(...) { ... }` out of index.html by brace matching.
function extractFn(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start === -1) throw new Error(`${name} not found in index.html`);
  let depth = 0, i = src.indexOf("{", start);
  const open = i;
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`unbalanced braces in ${name} (from ${open})`);
}

// CONFIG.units is the only outside binding parseBidItems closes over. Read it
// from index.html too, so the unit list can't drift out of sync either.
function extractUnits(src) {
  const m = src.match(/units\s*:\s*\[([^\]]+)\]/);
  if (!m) throw new Error("CONFIG.units not found in index.html");
  return m[1].split(",").map(s => s.trim().replace(/^["']|["']$/g, "")).filter(Boolean);
}

const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
const CONFIG = { units: extractUnits(html) };
const parseBidItems = new Function("CONFIG", `${extractFn(html, "parseBidItems")} return parseBidItems;`)(CONFIG);

// Expected counts come from the August 2026 proposal layouts. 02650 (maintain
// traffic) and 02676 (mill mobilization) are the wrapped lump-sum rows the old
// head regex dropped — they are the regression this suite exists to catch.
const CASES = [
  { file: "clark-262155.pbi.txt",   items: 31 },
  { file: "jackson-263024.pbi.txt", items: 14 },
  { file: "lincoln-262234.pbi.txt", items: 32 },
];

let failed = 0;
for (const c of CASES) {
  const lines = fs.readFileSync(path.join(ROOT, "tests/fixtures", c.file), "utf8").split("\n");
  const out = parseBidItems(lines);
  const count = code => out.filter(o => o.code === code).length;
  const problems = [];
  if (out.length !== c.items) problems.push(`${out.length} items, want ${c.items}`);
  if (count("02650") !== 2) problems.push(`02650 x${count("02650")}, want 2`);
  if (count("02676") !== 2) problems.push(`02676 x${count("02676")}, want 2`);
  if (out.some(o => !(o.qty > 0))) problems.push("item with non-positive qty");
  if (out.every(o => !o.section)) problems.push("no items tagged with a Section");

  if (problems.length) { failed++; console.log(`FAIL ${c.file}: ${problems.join("; ")}`); }
  else console.log(`OK   ${c.file} ${out.length} items`);
}

if (failed) { console.log(`\n${failed} of ${CASES.length} fixtures failed`); process.exit(1); }
console.log(`\nall ${CASES.length} fixtures OK against index.html`);
