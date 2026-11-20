"""Lookup functions (intent i7-lookup).

wi-i7-lookup-1 owns VLOOKUP (exact and sorted approximate). INDEX/MATCH follow
in wi-i7-lookup-2 on the same FUNCTIONS table.
"""

from __future__ import annotations

from src.values import (
    NA,
    VALUE,
    Blank,
    Bool,
    Error,
    Number,
    compare,
    is_error,
    to_number,
)

__all__ = ["FUNCTIONS"]


def _scalar(v):
    values = getattr(v, "values", None)
    if callable(values):
        cells = values()
        if len(cells) == 1:
            return cells[0]
        return VALUE
    return v


def _table(arg):
    """Rebuild the Range rectangle as a list of rows (row-major values())."""
    values = getattr(arg, "values", None)
    if not callable(values):
        return VALUE
    rows = arg.r2 - arg.r1 + 1
    cols = arg.c2 - arg.c1 + 1
    if rows < 1 or cols < 1:
        return VALUE
    flat = values()
    if len(flat) != rows * cols:
        return VALUE
    table = []
    i = 0
    for _ in range(rows):
        row = []
        for _ in range(cols):
            row.append(flat[i])
            i += 1
        table.append(row)
    return table


def _approx_flag(range_lookup):
    """Calc: omitted/TRUE/nonzero ⇒ approximate; 0/FALSE ⇒ exact."""
    if range_lookup is None or isinstance(range_lookup, Blank):
        return True
    if isinstance(range_lookup, Bool):
        return range_lookup.value
    if is_error(range_lookup):
        return range_lookup
    n = to_number(range_lookup)
    if is_error(n):
        return n
    return n.value != 0


def VLOOKUP(lookup, table, col_index, range_lookup=None):
    probe = _scalar(lookup)
    if is_error(probe):
        return probe

    grid = _table(table)
    if is_error(grid):
        return grid

    idx = to_number(_scalar(col_index))
    if is_error(idx):
        return idx
    col = int(idx.value)
    width = len(grid[0]) if grid else 0
    if col < 1 or col > width:
        return VALUE

    approx = _approx_flag(_scalar(range_lookup) if range_lookup is not None else Blank())
    if is_error(approx):
        return approx

    if not approx:
        for row in grid:
            cmp = compare(row[0], probe)
            if is_error(cmp):
                return cmp
            if cmp == 0:
                return row[col - 1]
        return NA

    # Sorted ascending approximate: last key ≤ probe.
    best = None
    for row in grid:
        cmp = compare(row[0], probe)
        if is_error(cmp):
            return cmp
        if cmp <= 0:
            best = row
        else:
            break
    if best is None:
        return NA
    return best[col - 1]


FUNCTIONS = {
    "VLOOKUP": VLOOKUP,
}
