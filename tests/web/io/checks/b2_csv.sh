#!/bin/sh
# b2: CSV opens and saves values.
# Contract (plan i11-open-save), in web/io/io.js:
#   parseCSV(text, sheet = "Sheet1") -> workbook with one sheet; fields typed as the grid types them
#     (a number, TRUE/FALSE, an empty field is no cell, anything else text); RFC 4180 quoting; CRLF or LF
#   toCSV(computed, sheet) -> the sheet's computed values from A1 to its last used row and column, LF line ends,
#     numbers as Calc shows them, TRUE/FALSE, errors by name, blank as an empty field, quoting where needed
set -eu
cd "$(dirname "$0")/../../../.."
[ -f web/io/io.js ] || { echo "FAIL: web/io/io.js missing"; exit 1; }
node --input-type=module -e '
import { pathToFileURL } from "node:url";
import { isDeepStrictEqual } from "node:util";
const io = await import(pathToFileURL("web/io/io.js").href);
let bad = 0;
const fail = (m) => { bad++; console.log("FAIL " + m); };
for (const fn of ["parseCSV", "toCSV"]) if (typeof io[fn] !== "function") fail(`${fn} is not exported`);
if (bad) process.exit(1);
const csv = "name,qty,price,ok\r\n\"Pens, blue\",3,1.5,TRUE\r\n\"say \"\"hi\"\"\",,-2,false\r\n\"two\nlines\",1e3,x,\r\n";
const got = io.parseCSV(csv);
const want = {sheets: {Sheet1: {A1: "name", B1: "qty", C1: "price", D1: "ok",
  A2: "Pens, blue", B2: 3, C2: 1.5, D2: true,
  A3: "say \"hi\"", C3: -2, D3: false,
  A4: "two\nlines", B4: 1000, C4: "x"}}};
if (!isDeepStrictEqual(got, want)) fail("parseCSV: got " + JSON.stringify(got) + ", want " + JSON.stringify(want));
const named = io.parseCSV("1,2\n3,4", "Data");
if (!isDeepStrictEqual(named, {sheets: {Data: {A1: 1, B1: 2, A2: 3, B2: 4}}})) fail("parseCSV with a sheet name and no final newline: " + JSON.stringify(named));
const computed = {sheets: {Sheet1: {A1: "Item", B1: "Total", A2: "Pens, blue", B2: 4.5, A3: "say \"hi\"", B3: 0.1 + 0.2,
  C3: true, A4: "x", B4: {error: "#DIV/0!"}, C4: false, D2: "two\nlines"}, Sheet2: {B2: 7}}};
const out = io.toCSV(computed, "Sheet1");
const wantCsv = "Item,Total,,\n\"Pens, blue\",4.5,,\"two\nlines\"\n\"say \"\"hi\"\"\",0.3,TRUE,\nx,#DIV/0!,FALSE,\n";
if (out !== wantCsv) fail("toCSV Sheet1: got " + JSON.stringify(out) + ", want " + JSON.stringify(wantCsv));
const out2 = io.toCSV(computed, "Sheet2");
if (out2 !== ",\n,7\n") fail("toCSV Sheet2 (starts at A1): got " + JSON.stringify(out2) + ", want " + JSON.stringify(",\n,7\n"));
const vals = {sheets: {Sheet1: {A1: "a", B1: 1, A2: "b,c", B2: -0.5, C2: true, A3: "q\"q"}}};
const round = io.parseCSV(io.toCSV(vals, "Sheet1"));
if (!isDeepStrictEqual(round, vals)) fail("values do not survive save then open: " + JSON.stringify(round));
if (bad) process.exit(1);
console.log("ok b2");
'
