#!/usr/bin/env node
// Proves the price cascade in index.html resolves county -> pod -> district -> statewide,
// per item code, honouring geo_min_n at every tier.
//
// Pod price tables do not exist yet (they need the KYTC AUBP source), so the tiers are
// exercised with synthetic tables injected into a copy of DATA. That is the point: this
// locks the ORDER in place now, so whoever generates the real tables finds out immediately
// if the tier stops firing.
//
//   node tests/test_cascade_js.mjs
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");

function extractFn(src, name) {
  const start = src.indexOf(`function ${name}(`);
  if (start === -1) throw new Error(`${name} not found in index.html`);
  let depth = 0;
  for (let i = src.indexOf("{", start); i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`unbalanced braces in ${name}`);
}

// Real pod definitions come from the file; only the price tables are synthetic.
const realData = JSON.parse(
  html.slice(html.indexOf("const DATA = ") + "const DATA = ".length,
             (() => {
               const i = html.indexOf("const DATA = ") + "const DATA = ".length;
               let depth = 0;
               for (let j = i; j < html.length; j++) {
                 if (html[j] === "{") depth++;
                 else if (html[j] === "}" && --depth === 0) return j + 1;
               }
               throw new Error("unbalanced DATA");
             })())
);

const CODE = "00001";
const DATA = {
  rules: { geo_min_n: 3 },
  geo: {
    county_to_district: realData.geo.county_to_district,
    pods: realData.geo.pods,
    county: { LINCOLN: { [CODE]: { p: 10, n: 5, yr: 2025 } } },
    pod: { GARBOYLIN: { [CODE]: { p: 20, n: 5, yr: 2025 } } },
    district: { "08": { [CODE]: { p: 30, n: 5, yr: 2025 } },
                "07": { [CODE]: { p: 31, n: 5, yr: 2025 } },
                "11": { [CODE]: { p: 33, n: 5, yr: 2025 } } },
  },
};

const src = [extractFn(html, "normCounty"), extractFn(html, "districtOf"),
             extractFn(html, "podOf"), extractFn(html, "localPrice")].join("\n");
const localPrice = new Function("DATA", `${src} return localPrice;`)(DATA);

const check = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log(`${ok ? "OK  " : "FAIL"} ${name}${ok ? "" : `  got ${JSON.stringify(got)} want ${JSON.stringify(want)}`}`);
  return ok;
};
const at = county => {
  const r = localPrice(CODE, county);
  return r ? { scope: r.scope, p: r.rec.p } : null;
};

let bad = 0;

// 1. county wins when it clears geo_min_n
bad += !check("county beats pod and district", at("LINCOLN"), { scope: "county", p: 10 });

// 2. county thin -> pod, NOT district
DATA.geo.county.LINCOLN[CODE].n = 2;
bad += !check("thin county falls to pod", at("LINCOLN"), { scope: "pod", p: 20 });

// 3. the whole point of GARBOYLIN: Lincoln is D08, but its pod prices it with D07 neighbours
bad += !check("pod overrides Lincoln's D08", at("LINCOLN").p !== 30, true);

// 4. pod thin too -> district (Lincoln's own district, 08)
DATA.geo.pod.GARBOYLIN[CODE].n = 2;
bad += !check("thin pod falls to district", at("LINCOLN"), { scope: "district", p: 30 });

// 5. district thin as well -> null, so unitPrice uses the statewide row
DATA.geo.district["08"][CODE].n = 2;
bad += !check("thin district falls through to statewide", at("LINCOLN"), null);

// 6. a pod county whose district differs still routes to its own district on fall-through
DATA.geo.pod.GARBOYLIN[CODE].n = 2;
bad += !check("Boyle falls to D07, not Lincoln's D08", at("BOYLE"), { scope: "district", p: 31 });

// 7. Jackson joined LAURELCLAY on 2026-08-27 (Jacob's call, reversing the original
// "Jackson prices on its own" note in pods.json). Pooling rescues 84 item codes it could
// not price alone. Scott takes over as the county that must never pick up a pod.
const podFn = new Function("DATA", `${src} return podOf;`)(DATA);
bad += !check("Jackson is in LAURELCLAY", podFn("JACKSON"), "LAURELCLAY");
bad += !check("Scott is in no pod", podFn("SCOTT"), "");
DATA.geo.pod.GARBOYLIN[CODE].n = 5;
// LAURELCLAY has no table in this fixture, so Jackson must still reach its own district, 11.
bad += !check("Jackson falls through an empty pod to D11", at("JACKSON"), { scope: "district", p: 33 });
// ...and picks the pod up as soon as the table exists.
DATA.geo.pod.LAURELCLAY = { [CODE]: { p: 21, n: 5, yr: 2025 } };
bad += !check("Jackson prices on LAURELCLAY once it has a cell", at("JACKSON"), { scope: "pod", p: 21 });
delete DATA.geo.pod.LAURELCLAY;

// 8. no pod tables at all (today's shipped state) must behave exactly as before.
// Undo check 5's thinning first, or this asserts against a district that cannot answer.
DATA.geo.district["08"][CODE].n = 5;
const noPods = JSON.parse(JSON.stringify(DATA));
noPods.geo.pod = {};
noPods.geo.county = {};
const lpNoPods = new Function("DATA", `${src} return localPrice;`)(noPods);
const r8 = lpNoPods(CODE, "LINCOLN");
bad += !check("empty pod tables -> district, unchanged", { scope: r8 && r8.scope, p: r8 && r8.rec.p },
              { scope: "district", p: 30 });

if (bad) { console.log(`\n${bad} check(s) failed`); process.exit(1); }
console.log("\ncascade OK: county -> pod -> district -> statewide");
