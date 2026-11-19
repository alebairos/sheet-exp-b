#!/bin/sh
# b2: selecting and editing a cell updates it.
# Contract (plan i9-grid), in web/grid/grid.js:
#   select(state, ref) -> state with that cell selected (rendered with class "selected")
#   edit(state, ref, text) -> state whose sheet holds the typed value: a number, TRUE/FALSE, text, or no cell for ""
#   mount(container, state, {rows, cols, onChange}) -> wires the same in the browser (click selects, typing edits)
set -eu
cd "$(dirname "$0")/../../../.."
[ -f web/grid/grid.js ] || { echo "FAIL: web/grid/grid.js missing"; exit 1; }
node --input-type=module -e '
import { pathToFileURL } from "node:url";
const g = await import(pathToFileURL("web/grid/grid.js").href);
let bad = 0;
const fail = (m) => { bad++; console.log("FAIL " + m); };
for (const f of ["createState", "select", "edit", "renderHTML", "mount"]) if (typeof g[f] !== "function") fail(`${f} is not exported`);
if (bad) process.exit(1);
const tdOf = (html, ref) => (html.match(new RegExp(`<td[^>]*data-ref="${ref}"[^>]*>[\\s\\S]*?</td>`)) || [""])[0];
const selected = (td) => /class="[^"]*\bselected\b[^"]*"/.test(td);
let s = g.createState({sheets: {Sheet1: {A1: 1, B2: "old"}}}, "Sheet1");
s = g.select(s, "B2");
let html = g.renderHTML(s, {rows: 3, cols: 3});
if (!selected(tdOf(html, "B2"))) fail("B2 is not rendered selected after select(B2)");
if (selected(tdOf(html, "A1"))) fail("A1 is still rendered selected after select(B2)");
const cells = () => s.book.sheets.Sheet1;
const typed = [["42", 42], ["-2.5", -2.5], ["1e3", 1000], ["TRUE", true], ["false", false], ["hello", "hello"], ["=A1+1", "=A1+1"], ["007x", "007x"]];
for (const [text, want] of typed) {
  s = g.edit(s, "B2", text);
  if (cells().B2 !== want) fail(`edit B2 to ${JSON.stringify(text)}: cell holds ${JSON.stringify(cells().B2)}, want ${JSON.stringify(want)}`);
}
s = g.edit(s, "C3", "9");
html = g.renderHTML(s, {rows: 3, cols: 3});
if (!/>\s*9\s*<\/td>/.test(tdOf(html, "C3"))) fail("C3 does not show 9 after editing it");
if (cells().A1 !== 1) fail("editing other cells changed A1");
s = g.edit(s, "B2", "");
if ("B2" in cells()) fail("editing B2 to empty text leaves a cell, want a blank (no key)");
if (bad) process.exit(1);
console.log("ok b2");
'
