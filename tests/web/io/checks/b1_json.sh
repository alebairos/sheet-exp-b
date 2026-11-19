#!/bin/sh
# b1: opening then saving a JSON workbook keeps every cell.
# Contract (plan i11-open-save): web/io/io.js, an ES module (no build, no DOM needed to import):
#   parseJSON(text) -> workbook {sheets: {...}} (throws an Error with a message for a file that is not one)
#   toJSON(workbook) -> text in SPEC.md's shape
# Needs Node.js (any current LTS); nothing to install.
set -eu
cd "$(dirname "$0")/../../../.."
[ -f web/io/io.js ] || { echo "FAIL: web/io/io.js missing"; exit 1; }
node --input-type=module -e '
import { pathToFileURL } from "node:url";
import { isDeepStrictEqual } from "node:util";
const io = await import(pathToFileURL("web/io/io.js").href);
let bad = 0;
const fail = (m) => { bad++; console.log("FAIL " + m); };
for (const fn of ["parseJSON", "toJSON"]) if (typeof io[fn] !== "function") fail(`${fn} is not exported`);
if (bad) process.exit(1);
const book = {sheets: {
  Sheet1: {A1: 1, A2: -2.5, A3: 0, A4: 1e-7, A5: 123456789012, B1: "text", B2: "", B3: "12", B4: "a,\"b\"\nc",
           C1: true, C2: false, D1: "=SUM(A1:A2)", D2: "=Sheet2!A1&\"x\"", E1: {error: "#DIV/0!"}, E2: {error: "#N/A"}},
  Sheet2: {A1: "é ünïcödé ✓"},
  "My Sheet": {},
}};
const text = io.toJSON(book);
let parsed;
try { parsed = JSON.parse(text); } catch (e) { fail("toJSON is not JSON: " + e.message); }
if (parsed && !isDeepStrictEqual(parsed, book)) fail("toJSON changed cells: " + text);
const back = io.parseJSON(text);
if (!isDeepStrictEqual(back, book)) fail("parseJSON(toJSON(book)) is not book: " + JSON.stringify(back));
if (!isDeepStrictEqual(io.parseJSON(io.toJSON(back)), book)) fail("a second open/save changed cells");
if (!Object.keys(back.sheets).every((k, i) => k === Object.keys(book.sheets)[i])) fail("sheet order changed");
const spec = "{\"sheets\": {\"Sheet1\": {\"A1\": 1, \"A2\": \"text\", \"A3\": true, \"B1\": \"=SUM(A1:A2)\"}, \"Sheet2\": {}}}";
if (!isDeepStrictEqual(io.parseJSON(spec), JSON.parse(spec))) fail("the SPEC.md example does not open as written");
for (const badText of ["not json", "[1,2]", "{\"cells\": {}}", "{\"sheets\": 3}"]) {
  let threw = false;
  try { io.parseJSON(badText); } catch (e) { threw = e instanceof Error && !!e.message; }
  if (!threw) fail(`parseJSON(${JSON.stringify(badText)}) does not throw an Error with a message`);
}
if (bad) process.exit(1);
console.log("ok b1");
'
