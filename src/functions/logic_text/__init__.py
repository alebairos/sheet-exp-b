"""Logic, information, and text functions (intent i6-logic-text).

wi-i6-logic-text-1 owns logic/information; wi-i6-logic-text-2 owns text ops on
the same FUNCTIONS table.
"""

from __future__ import annotations

import math

from src.values import (
    VALUE,
    Blank,
    Bool,
    Error,
    Number,
    Text,
    is_error,
    to_bool,
    to_number,
    to_text,
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


def IF(cond, then, otherwise=None):
    c = to_bool(_scalar(cond))
    if is_error(c):
        return c
    if c.value:
        return _scalar(then)
    if otherwise is None:
        return Bool(False)
    return _scalar(otherwise)


def IFERROR(value, fallback):
    v = _scalar(value)
    if is_error(v):
        return _scalar(fallback)
    return v


def AND(*args):
    if not args:
        return VALUE
    bools = []
    for arg in args:
        b = to_bool(_scalar(arg))
        if is_error(b):
            return b
        bools.append(b.value)
    return Bool(all(bools))


def OR(*args):
    if not args:
        return VALUE
    bools = []
    for arg in args:
        b = to_bool(_scalar(arg))
        if is_error(b):
            return b
        bools.append(b.value)
    return Bool(any(bools))


def NOT(x):
    b = to_bool(_scalar(x))
    if is_error(b):
        return b
    return Bool(not b.value)


def ISBLANK(x):
    return Bool(isinstance(_scalar(x), Blank))


def ISNUMBER(x):
    # Calc treats TRUE/FALSE as 1/0, so booleans count as numbers (clarification).
    v = _scalar(x)
    return Bool(isinstance(v, (Number, Bool)))


def ISTEXT(x):
    return Bool(isinstance(_scalar(x), Text))


def ISERROR(x):
    return Bool(isinstance(_scalar(x), Error))


def _nonneg_int(v, default=None):
    """A string-function count: truncated toward zero, or #VALUE! if negative."""
    if v is None:
        return default
    n = to_number(_scalar(v))
    if is_error(n):
        return n
    i = math.trunc(n.value)
    if i < 0:
        return VALUE
    return i


def CONCATENATE(*args):
    if not args:
        return VALUE
    parts = []
    for arg in args:
        t = to_text(_scalar(arg))
        if is_error(t):
            return t
        parts.append(t.value)
    return Text("".join(parts))


def LEFT(text, count=None):
    t = to_text(_scalar(text))
    if is_error(t):
        return t
    n = _nonneg_int(count, 1)
    if is_error(n):
        return n
    return Text(t.value[:n])


def RIGHT(text, count=None):
    t = to_text(_scalar(text))
    if is_error(t):
        return t
    n = _nonneg_int(count, 1)
    if is_error(n):
        return n
    if n == 0:
        return Text("")
    return Text(t.value[-n:])


def MID(text, start, length):
    t = to_text(_scalar(text))
    if is_error(t):
        return t
    s = to_number(_scalar(start))
    if is_error(s):
        return s
    start_i = math.trunc(s.value)
    if start_i < 1:
        return VALUE
    n = _nonneg_int(length)
    if is_error(n):
        return n
    begin = start_i - 1
    return Text(t.value[begin : begin + n])


def LEN(text):
    t = to_text(_scalar(text))
    if is_error(t):
        return t
    return Number(float(len(t.value)))


def UPPER(text):
    t = to_text(_scalar(text))
    if is_error(t):
        return t
    return Text(t.value.upper())


def LOWER(text):
    t = to_text(_scalar(text))
    if is_error(t):
        return t
    return Text(t.value.lower())


def TRIM(text):
    t = to_text(_scalar(text))
    if is_error(t):
        return t
    # Calc TRIM: strip leading/trailing ASCII spaces, collapse internal runs.
    s = t.value.strip(" ")
    while "  " in s:
        s = s.replace("  ", " ")
    return Text(s)


FUNCTIONS = {
    "IF": IF,
    "IFERROR": IFERROR,
    "AND": AND,
    "OR": OR,
    "NOT": NOT,
    "ISBLANK": ISBLANK,
    "ISNUMBER": ISNUMBER,
    "ISTEXT": ISTEXT,
    "ISERROR": ISERROR,
    "CONCATENATE": CONCATENATE,
    "LEFT": LEFT,
    "RIGHT": RIGHT,
    "MID": MID,
    "LEN": LEN,
    "UPPER": UPPER,
    "LOWER": LOWER,
    "TRIM": TRIM,
}
