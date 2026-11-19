// The formula bar (intent i10-formula-bar): a plain ES module, no build, no libraries.
// Pure functions first (barText, errorText, commit, renderHTML) so Node tests them without
// a browser; mount() is the only DOM code.
//
// raw:      the workbook as typed (SPEC.md JSON, formulas kept), {sheets: {Sheet1: {A1: ...}}}
// computed: ./engine's output for it, errors as {error: "#DIV/0!"}

const escapeHTML = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

const sheetOf = (book, sheet) => (book && book.sheets && book.sheets[sheet]) || {};
const cellOf = (book, sheet, ref) => {
  const cells = sheetOf(book, sheet);
  return Object.prototype.hasOwnProperty.call(cells, ref) ? cells[ref] : undefined;
};

const NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

/** A number as Calc's input line shows it: up to 15 significant digits. */
export function formatNumber(n) {
  if (!Number.isFinite(n)) return "#NUM!";
  if (Object.is(n, -0)) n = 0;
  return String(Number(n.toPrecision(15))).replace("e+", "E+").replace("e-", "E-");
}

function typedText(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "TRUE" : "FALSE";
  if (typeof v === "number") return formatNumber(v);
  if (typeof v === "object") return typeof v.error === "string" ? v.error : "";
  return String(v);
}

/** What the bar shows for that cell of the workbook as typed (formulas kept). */
export function barText(raw, sheet, ref) {
  return typedText(cellOf(raw, sheet, ref));
}

/** The error's name as Calc shows it, or "" when the computed cell is not an error. */
export function errorText(computed, sheet, ref) {
  const v = cellOf(computed, sheet, ref);
  return v && typeof v === "object" && typeof v.error === "string" ? v.error : "";
}

/** The bar's text as a typed value: undefined for a blank cell. */
export function parseInput(text) {
  const s = String(text ?? "");
  if (s === "") return undefined;
  if (s.startsWith("=")) return s;
  if (NUMBER.test(s)) {
    const x = Number(s);
    if (Number.isFinite(x)) return x;
  }
  if (/^true$/i.test(s)) return true;
  if (/^false$/i.test(s)) return false;
  return s;
}

/** A new workbook with that cell set from the bar's text; the input is not mutated. */
export function commit(raw, sheet, ref, text) {
  const book = raw && typeof raw === "object" ? raw : {};
  const sheets = { ...(book.sheets || {}) };
  const cells = { ...(sheets[sheet] || {}) };
  const v = parseInput(text);
  if (v === undefined) delete cells[ref];
  else cells[ref] = v;
  sheets[sheet] = cells;
  return { ...book, sheets };
}

/** The bar's HTML: cell name, input with the text and, for an error only, its name. */
export function renderHTML({ raw, computed, sheet, ref }) {
  const err = errorText(computed, sheet, ref);
  return (
    `<div class="formula-bar">` +
    `<span class="ref">${escapeHTML(ref ?? "")}</span>` +
    `<span class="fx">fx</span>` +
    `<input class="text" aria-label="Formula" value="${escapeHTML(barText(raw, sheet, ref))}">` +
    (err ? `<span class="error" role="alert">${escapeHTML(err)}</span>` : "") +
    `</div>`
  );
}

/**
 * Draws the bar into container; Enter commits, Escape cancels.
 * update({ref, raw, computed, sheet}) follows the grid's selection.
 */
export function mount(container, state, { onCommit = () => {} } = {}) {
  let s = { ...state };
  const draw = () => {
    container.innerHTML = renderHTML(s);
    const input = container.querySelector("input");
    if (!input) return;
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        s = { ...s, raw: commit(s.raw, s.sheet, s.ref, input.value) };
        draw();
        onCommit(s.raw, s.ref, s.sheet);
      } else if (e.key === "Escape") {
        e.preventDefault();
        draw();
      }
    });
  };
  draw();
  return {
    update(next) { s = { ...s, ...next }; draw(); },
    get state() { return s; },
    focus() { const i = container.querySelector("input"); if (i) i.focus(); },
  };
}
