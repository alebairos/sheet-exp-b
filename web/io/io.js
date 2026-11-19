// Open/save for the workbook UI (intent i11-open-save): plain ES module, no build.
// parseJSON/toJSON/parseCSV/toCSV and createController are pure (Node-testable).
// download() and openFile() are the only helpers that touch the browser.

export function parseJSON(text) {
  let b;
  try {
    b = JSON.parse(text);
  } catch (e) {
    throw new Error("not a JSON file: " + e.message);
  }
  if (
    !b ||
    typeof b !== "object" ||
    Array.isArray(b) ||
    !b.sheets ||
    typeof b.sheets !== "object" ||
    Array.isArray(b.sheets)
  ) {
    throw new Error('not a workbook: expected {"sheets": {...}}');
  }
  return b;
}

export function toJSON(book) {
  return JSON.stringify(book, null, 2) + "\n";
}

const colName = (i) => {
  let s = "";
  for (let n = i + 1; n > 0; n = Math.floor((n - 1) / 26)) {
    s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  }
  return s;
};

const colIndex = (s) =>
  [...s].reduce((n, ch) => n * 26 + ch.toUpperCase().charCodeAt(0) - 64, 0) - 1;

const NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

function typed(t) {
  if (t === "") return undefined;
  if (NUMBER.test(t)) {
    const x = Number(t);
    if (Number.isFinite(x)) return x;
  }
  if (/^true$/i.test(t)) return true;
  if (/^false$/i.test(t)) return false;
  return t;
}

export function parseCSV(text, sheet = "Sheet1") {
  const rows = [];
  let row = [];
  let f = "";
  let q = false;
  let i = 0;
  while (i < text.length) {
    const c = text[i];
    if (q) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          f += '"';
          i += 2;
          continue;
        }
        q = false;
        i++;
        continue;
      }
      f += c;
      i++;
      continue;
    }
    if (c === '"') {
      q = true;
      i++;
      continue;
    }
    if (c === ",") {
      row.push(f);
      f = "";
      i++;
      continue;
    }
    if (c === "\r" && text[i + 1] === "\n") i++;
    if (c === "\n" || c === "\r") {
      row.push(f);
      rows.push(row);
      row = [];
      f = "";
      i++;
      continue;
    }
    f += c;
    i++;
  }
  if (f !== "" || row.length) {
    row.push(f);
    rows.push(row);
  }
  const cells = {};
  rows.forEach((r, ri) =>
    r.forEach((t, ci) => {
      const v = typed(t);
      if (v !== undefined) cells[colName(ci) + (ri + 1)] = v;
    })
  );
  return { sheets: { [sheet]: cells } };
}

function formatNumber(v) {
  if (!Number.isFinite(v)) return "#NUM!";
  if (Object.is(v, -0)) v = 0;
  return String(Number(v.toPrecision(15))).replace("e+", "E+").replace("e-", "E-");
}

function field(v) {
  if (v === null || v === undefined) return "";
  let s;
  if (typeof v === "boolean") s = v ? "TRUE" : "FALSE";
  else if (typeof v === "number") s = formatNumber(v);
  else if (typeof v === "object") s = typeof v.error === "string" ? v.error : "";
  else s = String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCSV(book, sheet) {
  const cells = (book.sheets || {})[sheet] || {};
  let mr = 0;
  let mc = -1;
  for (const ref of Object.keys(cells)) {
    const m = /^([A-Za-z]+)(\d+)$/.exec(ref);
    if (!m) continue;
    mc = Math.max(mc, colIndex(m[1]));
    mr = Math.max(mr, +m[2]);
  }
  let out = "";
  for (let r = 1; r <= mr; r++) {
    const fs = [];
    for (let c = 0; c <= mc; c++) fs.push(field(cells[colName(c) + r]));
    out += fs.join(",") + "\n";
  }
  return out;
}

export function openFile(file) {
  return file.text();
}

export function download(name, text, type = "text/plain") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function createController({ compute = async (b) => b } = {}) {
  const state = {
    book: { sheets: { Sheet1: {} } },
    computed: { sheets: { Sheet1: {} } },
    sheet: "Sheet1",
    name: "workbook",
    message: "",
  };
  const refresh = async () => {
    state.computed = await compute(state.book);
  };
  return {
    get state() {
      return state;
    },
    async openText(fileName, text) {
      let book;
      try {
        book = /\.csv$/i.test(fileName) ? parseCSV(text) : parseJSON(text);
      } catch (e) {
        state.message = `Could not open ${fileName}: ${e.message}`;
        return { ok: false, message: state.message };
      }
      state.book = book;
      state.sheet = Object.keys(book.sheets)[0] || "Sheet1";
      state.name = fileName.replace(/\.[^.]*$/, "") || "workbook";
      state.message = `Opened ${fileName}`;
      await refresh();
      return { ok: true };
    },
    async openFile(file) {
      return this.openText(file.name, await file.text());
    },
    async setBook(book) {
      state.book = book;
      await refresh();
    },
    saveJSON() {
      return { name: state.name + ".json", text: toJSON(state.book), type: "application/json" };
    },
    saveCSV() {
      return { name: state.name + ".csv", text: toCSV(state.computed, state.sheet), type: "text/csv" };
    },
  };
}
