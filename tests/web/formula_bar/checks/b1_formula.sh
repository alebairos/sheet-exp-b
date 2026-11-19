#!/bin/sh
# b1: the formula bar shows and edits the selected cell's formula.
# Contract (plan i10-formula-bar): web/formula_bar/formula_bar.js, an ES module (no build, no DOM needed to import):
#   barText(raw, sheet, ref) -> what the bar shows for that cell of the workbook as typed (formulas kept)
#   commit(raw, sheet, ref, text) -> a new workbook with that cell set from the bar's text
#   renderHTML({raw, computed, sheet, ref}) -> the bar's HTML; mount(container, state, {onCommit}) wires it in the page
# Needs Node.js (any current LTS); nothing to install.
set -eu
cd "$(dirname "$0")/../../../.."
[ -f web/formula_bar/formula_bar.js ] || { echo "FAIL: web/formula_bar/formula_bar.js missing"; exit 1; }
node --input-type=module -e '
import { pathToFileURL } from "node:url";
const f = await import(pathToFileURL("web/formula_bar/formula_bar.js").href);
let bad = 0;
const expect = (label, got, want) => { if (JSON.stringify(got) !== JSON.stringify(want)) { bad++; console.log(`FAIL ${label}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); } };
for (const fn of ["barText", "commit", "renderHTML", "mount"]) if (typeof f[fn] !== "function") { bad++; console.log(`FAIL ${fn} is not exported`); }
if (bad) process.exit(1);
const raw = {sheets: {Sheet1: {A1: 1, A2: 2.5, B1: "=SUM(A1:A2)", B2: "=\"a\"&\"b\"", C1: "text", C2: true, C3: false}, Sheet2: {A1: "=Sheet1!A1*2"}}};
expect("bar for a formula", f.barText(raw, "Sheet1", "B1"), "=SUM(A1:A2)");
expect("bar for a number", f.barText(raw, "Sheet1", "A1"), "1");
expect("bar for 2.5", f.barText(raw, "Sheet1", "A2"), "2.5");
expect("bar for text", f.barText(raw, "Sheet1", "C1"), "text");
expect("bar for TRUE", f.barText(raw, "Sheet1", "C2"), "TRUE");
expect("bar for FALSE", f.barText(raw, "Sheet1", "C3"), "FALSE");
expect("bar for a blank cell", f.barText(raw, "Sheet1", "D9"), "");
expect("bar on Sheet2", f.barText(raw, "Sheet2", "A1"), "=Sheet1!A1*2");
const html = f.renderHTML({raw, computed: {sheets: {Sheet1: {B2: "ab"}}}, sheet: "Sheet1", ref: "B2"});
if (!html.includes("B2")) { bad++; console.log("FAIL the bar does not name the selected cell B2"); }
if (!html.includes("=&quot;a&quot;&amp;&quot;b&quot;") && !html.includes("=&#34;a&#34;&amp;&#34;b&#34;")) { bad++; console.log("FAIL the formula =\"a\"&\"b\" is not in the bar, HTML-escaped: " + html); }
let r = f.commit(raw, "Sheet1", "D1", "=A1+1");
expect("commit a formula", r.sheets.Sheet1.D1, "=A1+1");
r = f.commit(r, "Sheet1", "B1", "=MAX(A1:A2)");
expect("commit replaces a formula", r.sheets.Sheet1.B1, "=MAX(A1:A2)");
r = f.commit(r, "Sheet1", "A1", "42");
expect("commit a number", r.sheets.Sheet1.A1, 42);
r = f.commit(r, "Sheet1", "C1", "true");
expect("commit a boolean", r.sheets.Sheet1.C1, true);
r = f.commit(r, "Sheet1", "C2", "hello");
expect("commit text", r.sheets.Sheet1.C2, "hello");
r = f.commit(r, "Sheet1", "C3", "");
expect("commit empty makes a blank", "C3" in r.sheets.Sheet1, false);
expect("commit leaves the input workbook alone", raw.sheets.Sheet1.B1, "=SUM(A1:A2)");
expect("commit leaves other sheets alone", r.sheets.Sheet2.A1, "=Sheet1!A1*2");
if (bad) process.exit(1);
console.log("ok b1");
'
