# Spec: a spreadsheet engine


## What to build

An engine that computes a workbook the way LibreOffice Calc does, and a browser UI to work in it. Language and stack are free. The repo must build and test from a clean clone with one documented command.

## The engine CLI (the contract the hidden suite uses)

`<engine> <file|->` reads a workbook as JSON:

```json
{"sheets": {"Sheet1": {"A1": 1, "A2": "text", "A3": true, "B1": "=SUM(A1:A2)"}, "Sheet2": {}}}
```

- A string that starts with `=` is a formula; any other value is a constant. Missing cells are blank.
- Output: the computed workbook in the same shape, every formula replaced by its value.
  - Numbers are JSON numbers, text is a string, booleans are `true`/`false`.
  - Errors are `{"error": "#DIV/0!"}`.
- `<engine> - --cell Sheet1!H1` prints only that cell's value.

## Formulas

- References: `A1`, `$A$1`, `A1:B6`, `Sheet2!A1`. Operators: `+ - * / ^ & = <> < > <= >=`, unary minus, `%`.
- Precedence: as Calc does it (including `-A1^2` and `2^3^2`).
- Errors and their propagation: `#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?`, `#N/A`, `#NUM!`.
- Coercion as Calc: text to number in arithmetic, booleans as 1 and 0, the blank cell as 0 or "".
- Recalculation in dependency order. A circular reference gives an error, not a hang.

## Functions (40, no dates)

| Group | Functions |
|---|---|
| Math and statistics (20) | SUM, AVERAGE, MIN, MAX, COUNT, COUNTA, ROUND, ROUNDUP, ROUNDDOWN, INT, MOD, ABS, POWER, SQRT, PRODUCT, SUMIF, COUNTIF, AVERAGEIF, MEDIAN, STDEV |
| Logic and information (9) | IF, IFERROR, AND, OR, NOT, ISBLANK, ISNUMBER, ISTEXT, ISERROR |
| Text (8) | CONCATENATE, LEFT, RIGHT, MID, LEN, UPPER, LOWER, TRIM |
| Lookup (3) | VLOOKUP, INDEX, MATCH |

## The UI

A grid that renders, selects and edits cells. A formula bar that shows the formula and errors. Open and save: CSV and the JSON workbook above.


## Judged by

A hidden suite of 600 cases computed by LibreOffice headless, run once at the end against the engine CLI.
