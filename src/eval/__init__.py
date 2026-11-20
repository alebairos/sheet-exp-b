"""Formula evaluator (intent i3-evaluator).

``evaluate`` reads stored cells and returns a ``src.values.Value``. Operators use
Calc's coercion. ``register`` and ``registry`` supply the functions a call may run.
"""

import math

from src.functions.registry import discover_functions
from src.parser import (
    Binary,
    Bool as BoolNode,
    Call,
    Error as ErrorNode,
    Missing,
    Name,
    Number as NumberNode,
    ParseError,
    Percent,
    Range as RangeNode,
    Ref,
    Text as TextNode,
    Unary,
    parse,
)
from src.values import (
    BLANK,
    DIV0,
    NAME,
    NUM,
    REF,
    VALUE,
    Blank,
    Bool,
    Error,
    Number,
    Text,
    compare,
    from_json,
    is_error,
    to_number,
    to_text,
)

__all__ = ["Range", "evaluate", "register", "registry"]

_REGISTERED = {}

_CMP = {
    "=": lambda c: c == 0,
    "<>": lambda c: c != 0,
    "<": lambda c: c < 0,
    ">": lambda c: c > 0,
    "<=": lambda c: c <= 0,
    ">=": lambda c: c >= 0,
}


def register(name, fn=None):
    """Record fn under the uppercase name. Use as ``@register("NAME")``."""
    def deco(func):
        _REGISTERED[str(name).upper()] = func
        return func

    if fn is None:
        return deco
    return deco(fn)


def registry():
    """Direct registrations plus each package's ``FUNCTIONS`` table, uppercase keys."""
    merged = {}
    for mod in discover_functions().values():
        table = getattr(mod, "FUNCTIONS", None)
        if isinstance(table, dict):
            for key, fn in table.items():
                merged[str(key).upper()] = fn
    merged.update(_REGISTERED)
    return merged


class Range:
    """A rectangle of cells. ``values`` walks it row by row, blanks included."""

    def __init__(self, book, sheet, r1, c1, r2, c2):
        self.book = book
        self.sheet = sheet
        self.r1 = min(r1, r2)
        self.c1 = min(c1, c2)
        self.r2 = max(r1, r2)
        self.c2 = max(c1, c2)

    def values(self):
        """Every cell from the top-left. Each cell on an unknown sheet is #REF!."""
        cells = _cells(self.book, self.sheet)
        out = []
        for row in range(self.r1, self.r2 + 1):
            for col in range(self.c1, self.c2 + 1):
                out.append(_cell(cells, col, row))
        return out

    def __repr__(self):
        a = "%s%d" % (_col_name(self.c1), self.r1)
        b = "%s%d" % (_col_name(self.c2), self.r2)
        return "Range(%r, %s:%s)" % (self.sheet, a, b)


def evaluate(formula, book, sheet):
    """Value of formula on sheet. A blank reference used alone is 0."""
    try:
        node = parse(formula)
    except ParseError:
        return VALUE
    result = _eval(node, book, sheet)
    if isinstance(result, Range):
        result = _collapse(result)
        if isinstance(result, Blank):
            return Number(0.0)
    return result


def _eval(node, book, sheet):
    if isinstance(node, NumberNode):
        if not math.isfinite(node.value):
            return NUM
        return Number(node.value)
    if isinstance(node, TextNode):
        return Text(node.value)
    if isinstance(node, BoolNode):
        return Bool(node.value)
    if isinstance(node, ErrorNode):
        return Error(node.code)
    if isinstance(node, (Ref, RangeNode)):
        return _range_from(node, book, sheet)
    if isinstance(node, Name):
        return NAME
    if isinstance(node, Call):
        return _call(node, book, sheet)
    if isinstance(node, Missing):
        return BLANK
    if isinstance(node, Unary):
        return _on_number(_scalar(node.expr, book, sheet), lambda x: Number(-x))
    if isinstance(node, Percent):
        return _on_number(_scalar(node.expr, book, sheet), lambda x: Number(x / 100.0))
    if isinstance(node, Binary):
        return _binary(
            node.op,
            _scalar(node.left, book, sheet),
            _scalar(node.right, book, sheet),
        )


def _call(node, book, sheet):
    fn = registry().get(node.name.upper())
    if not callable(fn):
        return NAME
    args = [_arg(arg, book, sheet) for arg in node.args]
    return fn(*args)


def _arg(node, book, sheet):
    if isinstance(node, (Ref, RangeNode)):
        return _range_from(node, book, sheet)
    return _scalar(node, book, sheet)


def _scalar(node, book, sheet):
    value = _eval(node, book, sheet)
    if isinstance(value, Range):
        return _collapse(value)
    return value


def _collapse(rng):
    vals = rng.values()
    if len(vals) == 1:
        return vals[0]
    return VALUE


def _binary(op, left, right):
    if op == "&":
        a = to_text(left)
        b = to_text(right)
        if is_error(a):
            return a
        if is_error(b):
            return b
        return Text(a.value + b.value)
    pred = _CMP.get(op)
    if pred is not None:
        order = compare(left, right)
        if is_error(order):
            return order
        return Bool(pred(order))
    a = to_number(left)
    b = to_number(right)
    if is_error(a):
        return a
    if is_error(b):
        return b
    return _ARITH[op](a.value, b.value)


def _on_number(value, fn):
    number = to_number(value)
    if is_error(number):
        return number
    return fn(number.value)


def _finite(z):
    if isinstance(z, complex) or not math.isfinite(z):
        return NUM
    return Number(z)


def _div(x, y):
    if y == 0:
        return DIV0
    return _finite(x / y)


def _pow(x, y):
    try:
        z = x ** y
    except ZeroDivisionError:
        return DIV0
    except (OverflowError, ValueError):
        return NUM
    return _finite(z)


_ARITH = {
    "+": lambda x, y: _finite(x + y),
    "-": lambda x, y: _finite(x - y),
    "*": lambda x, y: _finite(x * y),
    "/": _div,
    "^": _pow,
}


def _range_from(node, book, sheet):
    if isinstance(node, Ref):
        name = _sheet_name(node, sheet)
        col = _col(node.col)
        return Range(book, name, node.row, col, node.row, col)
    left = _sheet_name(node.start, sheet)
    right = node.end.sheet if node.end.sheet is not None else left
    name = left if left == right else None
    return Range(
        book,
        name,
        node.start.row,
        _col(node.start.col),
        node.end.row,
        _col(node.end.col),
    )


def _sheet_name(ref, sheet):
    if ref.sheet is not None:
        return ref.sheet
    return sheet


def _cells(book, sheet):
    if not isinstance(book, dict) or not isinstance(sheet, str):
        return None
    sheets = book.get("sheets")
    if not isinstance(sheets, dict):
        return None
    cells = sheets.get(sheet)
    if not isinstance(cells, dict):
        return None
    return cells


def _cell(cells, col, row):
    if cells is None:
        return REF
    key = _col_name(col) + str(row)
    if key not in cells:
        return BLANK
    return from_json(cells[key])


def _col(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def _col_name(n):
    chars = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        chars.append(chr(65 + rem))
    return "".join(reversed(chars))
