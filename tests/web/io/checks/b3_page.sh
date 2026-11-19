#!/bin/sh
# b1 and b2 in the browser: the page's Open, Save JSON and Save CSV are wired to the grid and the engine.
# Contract (plan i11-open-save):
#   web/io/io.js also exports createController({compute}) -> controller with
#     async openText(fileName, text) -> {ok: true} or {ok: false, message}   (.csv opens as CSV, else JSON)
#     async setBook(book)  (the grid's edits);  state -> {book, computed, sheet, name, message}
#     saveJSON() / saveCSV() -> {name, text, type}  (JSON keeps the book as typed; CSV the computed values)
#   web/io/index.html: the page (Open file input #open, buttons #save-json and #save-csv, #message, #grid),
#     loading ./io.js and ../grid/grid.js; web/io/serve.py: python3 web/io/serve.py [port] serves web/ and
#     answers POST /compute with ./engine's computed workbook.
set -eu
cd "$(dirname "$0")/../../../.."
export PYTHONDONTWRITEBYTECODE=1
for f in web/io/io.js web/io/index.html web/io/serve.py; do [ -f "$f" ] || { echo "FAIL: $f missing"; exit 1; }; done
node --input-type=module -e '
import { pathToFileURL } from "node:url";
import { readFileSync } from "node:fs";
const io = await import(pathToFileURL("web/io/io.js").href);
let bad = 0;
const fail = (m) => { bad++; console.log("FAIL " + m); };
if (typeof io.createController !== "function") { console.log("FAIL createController is not exported"); process.exit(1); }
const calls = [];
const compute = async (book) => { calls.push(book); return {sheets: Object.fromEntries(Object.entries(book.sheets).map(([s, c]) =>
  [s, Object.fromEntries(Object.entries(c).map(([k, v]) => [k, typeof v === "string" && v.startsWith("=") ? 99 : v]))]))}; };
const c = io.createController({compute});
let r = await c.openText("book.json", JSON.stringify({sheets: {Data: {A1: 2, B1: "=A1*2", C1: "a,b"}, Other: {}}}));
if (!r || r.ok !== true) fail("opening a JSON workbook did not succeed: " + JSON.stringify(r));
if (c.state.sheet !== "Data") fail("the first sheet is not shown after opening: " + c.state.sheet);
if (!calls.length) fail("opening did not ask the engine to compute");
if (!c.state.computed || c.state.computed.sheets.Data.B1 !== 99) fail("the computed workbook is not kept");
let s = c.saveJSON();
if (s.name !== "book.json" || JSON.parse(s.text).sheets.Data.B1 !== "=A1*2") fail("Save JSON does not keep the formula: " + JSON.stringify(s));
s = c.saveCSV();
if (s.name !== "book.csv" || s.text !== "2,99,\"a,b\"\n") fail("Save CSV does not write the computed values: " + JSON.stringify(s));
await c.setBook({sheets: {Data: {A1: 5}, Other: {}}});
if (JSON.parse(c.saveJSON().text).sheets.Data.A1 !== 5) fail("an edit from the grid is not saved");
r = await c.openText("broken.json", "{not json");
if (!r || r.ok !== false || !r.message) fail("a bad file does not give a message: " + JSON.stringify(r));
if (!c.state.message) fail("the message for a bad file is not in the state");
if (JSON.parse(c.saveJSON().text).sheets.Data.A1 !== 5) fail("a bad file replaced the open workbook");
r = await c.openText("list.csv", "x,1\ny,2\n");
if (!r || r.ok !== true || c.state.book.sheets[c.state.sheet].B2 !== 2) fail("opening a CSV did not load its values");
if (c.saveCSV().text !== "x,1\ny,2\n") fail("CSV opened then saved changed: " + JSON.stringify(c.saveCSV().text));
const html = readFileSync("web/io/index.html", "utf8");
for (const id of ["open", "save-json", "save-csv", "message", "grid"]) if (!new RegExp(`id="${id}"`).test(html)) fail(`index.html has no element #${id}`);
if (!/type="file"[^>]*id="open"|id="open"[^>]*type="file"/.test(html)) fail("#open is not a file input");
if (!/from\s+"\.\/io\.js"/.test(html)) fail("index.html does not load ./io.js");
if (!/from\s+"\.\.\/grid\/grid\.js"/.test(html)) fail("index.html does not load the grid (../grid/grid.js)");
if (!/createController\s*\(/.test(html) || !/\bmount\s*\(/.test(html)) fail("index.html does not create the controller and mount the grid");
if (bad) process.exit(1);
console.log("ok page and controller");
'
python3 - <<'PY'
import json, socket, subprocess, sys, time, urllib.request
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
p = subprocess.Popen([sys.executable, "web/io/serve.py", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
bad = 0
try:
    base = "http://127.0.0.1:%d" % port
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/io/index.html", timeout=1); break
        except Exception:
            time.sleep(0.1)
    page = urllib.request.urlopen(base + "/io/index.html", timeout=5).read().decode()
    if 'id="save-csv"' not in page:
        bad += 1; print("FAIL serve.py does not serve /io/index.html")
    grid = urllib.request.urlopen(base + "/grid/grid.js", timeout=5)
    if "javascript" not in grid.headers.get("Content-Type", ""):
        bad += 1; print("FAIL /grid/grid.js is not served as JavaScript (ES modules need it): %s" % grid.headers.get("Content-Type"))
    book = {"sheets": {"Sheet1": {"A1": 1, "A2": "text", "A3": True}, "Sheet2": {}}}
    req = urllib.request.Request(base + "/compute", data=json.dumps(book).encode(), headers={"Content-Type": "application/json"})
    want = json.loads(subprocess.run(["./engine", "-"], input=json.dumps(book), capture_output=True, text=True).stdout)
    got = json.loads(urllib.request.urlopen(req, timeout=10).read())
    if got != want:
        bad += 1; print("FAIL POST /compute: got %r, want ./engine's %r" % (got, want))
finally:
    p.terminate(); p.wait(5)
if bad:
    sys.exit(1)
print("ok serve.py")
PY
