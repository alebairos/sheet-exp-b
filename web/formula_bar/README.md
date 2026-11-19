# web/formula_bar

The formula bar: `formula_bar.js`, a plain ES module (no build, no libraries).

- `barText(raw, sheet, ref)`: the selected cell as typed: its formula (`=A1/A2`) or constant (`1`, `2.5`, `TRUE`, text).
- `errorText(computed, sheet, ref)`: the error's name as Calc shows it (`#DIV/0!`, `#VALUE!`, `#REF!`, `#NAME?`, `#N/A`, `#NUM!`), or `""`.
- `commit(raw, sheet, ref, text)`: a new workbook with the cell set (`=` keeps a formula; numbers and TRUE/FALSE are typed; empty text blanks the cell). The input is not mutated.
- `renderHTML({raw, computed, sheet, ref})`: the bar's HTML; an error shows in `<span class="error">`.
- `mount(container, state, {onCommit})`: draws it; Enter commits, Escape cancels; returns `update({ref, raw, computed})`.

Tests: `tests/web/formula_bar` (Node.js).
