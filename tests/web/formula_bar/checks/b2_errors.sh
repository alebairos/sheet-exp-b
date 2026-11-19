#!/bin/sh
# b2: errors display as Calc names them.
# Contract (plan i10-formula-bar): errorText(computed, sheet, ref) -> the error's name as Calc shows it, or "";
# renderHTML shows it in an element with class "error" (and no such element when the cell is not in error).
set -eu
cd "$(dirname "$0")/../../../.."
[ -f web/formula_bar/formula_bar.js ] || { echo "FAIL: web/formula_bar/formula_bar.js missing"; exit 1; }
node --input-type=module -e '
import { pathToFileURL } from "node:url";
const f = await import(pathToFileURL("web/formula_bar/formula_bar.js").href);
let bad = 0;
const fail = (m) => { bad++; console.log("FAIL " + m); };
if (typeof f.errorText !== "function") { console.log("FAIL errorText is not exported"); process.exit(1); }
const names = ["#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#N/A", "#NUM!"];
const computed = {sheets: {Sheet1: {A1: 1, A2: "#DIV/0!", A3: true}}};
const raw = {sheets: {Sheet1: {A1: 1, A2: "#DIV/0!", A3: true}}};
names.forEach((n, i) => { computed.sheets.Sheet1["B" + (i + 1)] = {error: n}; raw.sheets.Sheet1["B" + (i + 1)] = "=X" + i; });
names.forEach((n, i) => {
  const ref = "B" + (i + 1);
  if (f.errorText(computed, "Sheet1", ref) !== n) fail(`errorText ${ref}: got ${JSON.stringify(f.errorText(computed, "Sheet1", ref))}, want ${n}`);
  const html = f.renderHTML({raw, computed, sheet: "Sheet1", ref});
  const m = html.match(/<[a-z]+[^>]*class="[^"]*\berror\b[^"]*"[^>]*>([\s\S]*?)<\//);
  if (!m || m[1].trim() !== n) fail(`the bar for ${ref} does not show ${n} in an element with class error: ${html}`);
  if (!html.includes("=X" + i)) fail(`the bar for ${ref} hides its formula =X${i}`);
});
for (const ref of ["A1", "A2", "A3", "Z9"]) {
  if (f.errorText(computed, "Sheet1", ref) !== "") fail(`errorText ${ref} (not an error): got ${JSON.stringify(f.errorText(computed, "Sheet1", ref))}, want ""`);
  const html = f.renderHTML({raw, computed, sheet: "Sheet1", ref});
  if (/class="[^"]*\berror\b/.test(html)) fail(`the bar for ${ref} (not an error) shows an error element`);
}
if (bad) process.exit(1);
console.log("ok b2");
'
