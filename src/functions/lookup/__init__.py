"""Lookup functions (intent i7-lookup).

VLOOKUP from wi-i7-lookup-1; INDEX and MATCH (types 0 and 1) from wi-i7-lookup-2.
"""

from __future__ import annotations

from src.values import (
    NA,
    REF,
    VALUE,
    Blank,
    Bool,
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


def _pos(v):
    """1-based INDEX position. 0 / negative / blank → #VALUE!; errors propagate."""
    cell = _scalar(v)
    if is_error(cell):
        return cell
    if isinstance(cell, Blank):
        return VALUE
    n = to_number(cell)
    if is_error(n):
        return n
    i = int(n.value)
    if i == 0 or i < 0:
        return VALUE
    return i


def INDEX(array, row, column=None):
    grid = _table(array)
    if is_error(grid):
        return grid
    nrows = len(grid)
    ncols = len(grid[0]) if grid else 0

    r = _pos(row)
    if is_error(r):
        return r

    if column is None:
        if ncols == 1:
            c = 1
        else:
            return VALUE
    else:
        c = _pos(column)
        if is_error(c):
            return c

    if r > nrows or c > ncols:
        return REF
    return grid[r - 1][c - 1]


def _match_type(match_type):
    """Calc: omitted/1 ⇒ approximate; 0 ⇒ exact. Type -1 not in this intent."""
    if match_type is None or isinstance(match_type, Blank):
        return 1
    if isinstance(match_type, Bool):
        return 1 if match_type.value else 0
    if is_error(match_type):
        return match_type
    n = to_number(match_type)
    if is_error(n):
        return n
    return int(n.value)


def MATCH(lookup, lookup_array, match_type=None):
    probe = _scalar(lookup)
    if is_error(probe):
        return probe

    values = getattr(lookup_array, "values", None)
    if not callable(values):
        return VALUE
    cells = values()

    kind = _match_type(_scalar(match_type) if match_type is not None else Blank())
    if is_error(kind):
        return kind

    if kind == 0:
        for i, cell in enumerate(cells):
            cmp = compare(cell, probe)
            if is_error(cmp):
                return cmp
            if cmp == 0:
                return Number(float(i + 1))
        return NA

    # type 1 / omitted: ascending approximate — last value ≤ probe
    best = None
    for i, cell in enumerate(cells):
        cmp = compare(cell, probe)
        if is_error(cmp):
            return cmp
        if cmp <= 0:
            best = i + 1
        else:
            break
    if best is None:
        return NA
    return Number(float(best))


FUNCTIONS = {
    "VLOOKUP": VLOOKUP,
    "INDEX": INDEX,
    "MATCH": MATCH,
}
