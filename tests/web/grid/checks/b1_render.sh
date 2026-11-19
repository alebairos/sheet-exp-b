#!/bin/sh
# b1: the grid renders a workbook's computed values.
# Contract (plan i9-grid): web/grid/grid.js is an ES module (no build step, no DOM needed to import) exporting
#   display(value) -> the text a cell shows for a computed JSON value
#   createState(book, sheet) -> grid state;  renderHTML(state, {rows, cols}) -> the grid's HTML string
# Needs Node.js (any current LTS); nothing to install.
set -eu
cd "$(dirname "$0")/../../../.."
[ -f web/grid/grid.js ] || { echo "FAIL: web/grid/grid.js missing"; exit 1; }
node --input-type=module -e '
import { pathToFileURL } from "node:url";
const g = await import(pathToFileURL("web/grid/grid.js").href);
let bad = 0;
const expect = (label, got, want) => { if (got !== want) { bad++; console.log(`FAIL ${label}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); } };
for (const [v, want] of [[1, "1"], [2.5, "2.5"], [-3, "-3"], [0.1 + 0.2, "0.3"], [true, "TRUE"], [false, "FALSE"],
                         ["text", "text"], ["", ""], [null, ""], [undefined, ""], [{error: "#DIV/0!"}, "#DIV/0!"], [{error: "#N/A"}, "#N/A"]])
  expect(`display(${JSON.stringify(v)})`, g.display(v), want);
const book = {sheets: {Sheet1: {A1: 1, B1: "a<b", A2: true, C3: {error: "#VALUE!"}, B2: 2.5}, Sheet2: {A1: "other"}}};
const html = g.renderHTML(g.createState(book, "Sheet1"), {rows: 5, cols: 4});
const cell = (ref) => { const m = html.match(new RegExp(`<td[^>]*data-ref="${ref}"[^>]*>([\\s\\S]*?)</td>`)); return m ? m[1].trim() : null; };
expect("cell A1", cell("A1"), "1");
expect("cell B1 (escaped text)", cell("B1"), "a&lt;b");
expect("cell A2", cell("A2"), "TRUE");
expect("cell B2", cell("B2"), "2.5");
expect("cell C3", cell("C3"), "#VALUE!");
expect("blank cell D5", cell("D5"), "");
expect("no cell outside the size", cell("E1"), null);
for (const h of ["A", "B", "C", "D"]) if (!new RegExp(`<th[^>]*>\\s*${h}\\s*</th>`).test(html)) { bad++; console.log(`FAIL column header ${h} missing`); }
for (const r of ["1", "5"]) if (!new RegExp(`<th[^>]*>\\s*${r}\\s*</th>`).test(html)) { bad++; console.log(`FAIL row header ${r} missing`); }
const other = g.renderHTML(g.createState(book, "Sheet2"), {rows: 2, cols: 2});
if (!/<td[^>]*data-ref="A1"[^>]*>\s*other\s*<\/td>/.test(other)) { bad++; console.log("FAIL Sheet2 A1 not rendered"); }
const wide = g.renderHTML(g.createState({sheets: {S: {AA1: 7}}}, "S"), {rows: 1, cols: 27});
if (!/<td[^>]*data-ref="AA1"[^>]*>\s*7\s*<\/td>/.test(wide)) { bad++; console.log("FAIL column 27 is not AA"); }
if (bad) process.exit(1);
console.log("ok b1");
'
