"""Math and statistics functions (intent i5-math).

Aggregates (wi-i5-math-1) walk ranges; scalars/rounding (wi-i5-math-2) coerce
operands the way operators do. Criteria ops land in a sibling WI.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, ROUND_UP

from src.values import (
    DIV0,
    NUM,
    VALUE,
    Blank,
    Bool,
    Number,
    Text,
    is_error,
    to_number,
)


def _cells(arg):
    values = getattr(arg, "values", None)
    if callable(values):
        return values()
    return (arg,)


def _numbers(args):
    """Floats from args and ranges, or the first error."""
    nums = []
    for arg in args:
        for cell in _cells(arg):
            if isinstance(cell, (Blank, Text)):
                continue
            if is_error(cell):
                return cell
            if isinstance(cell, Bool):
                nums.append(1.0 if cell.value else 0.0)
            elif isinstance(cell, Number):
                if not math.isfinite(cell.value):
                    return NUM
                nums.append(cell.value)
            else:
                return VALUE
    return nums


def _finite(x):
    if not math.isfinite(x):
        return NUM
    return Number(x)


def _apply(empty, reduce):
    def fn(*args):
        nums = _numbers(args)
        if is_error(nums):
            return nums
        if not nums:
            return empty
        return reduce(nums)

    return fn


def _sum(nums):
    return _finite(math.fsum(nums))


def _average(nums):
    return _finite(math.fsum(nums) / len(nums))


def _min(nums):
    return Number(min(nums))


def _max(nums):
    return Number(max(nums))


def _count(nums):
    return Number(len(nums))


def _product(nums):
    product = 1.0
    for x in nums:
        product *= x
    return _finite(product)


def _median(nums):
    ordered = sorted(nums)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return Number(ordered[mid])
    return _finite((ordered[mid - 1] + ordered[mid]) / 2.0)


def _stdev(nums):
    if len(nums) < 2:
        return DIV0
    mean = math.fsum(nums) / len(nums)
    acc = math.fsum((x - mean) ** 2 for x in nums)
    return _finite(math.sqrt(acc / (len(nums) - 1)))


def _counta(*args):
    n = 0
    for arg in args:
        for cell in _cells(arg):
            if not isinstance(cell, Blank):
                n += 1
    return Number(n)


def _scalar(v):
    """Collapse a one-cell Range the way operators do; leave Values alone."""
    values = getattr(v, "values", None)
    if callable(values):
        cells = values()
        if len(cells) == 1:
            return cells[0]
        return VALUE
    return v


def _as_number(v):
    n = to_number(_scalar(v))
    if is_error(n):
        return n
    return n


def _digits(v, default=0):
    if v is None:
        return Number(float(default))
    return _as_number(v)


def _quantize(x, digits, mode):
    """Scale ``x`` to ``digits`` places with the given decimal rounding mode."""
    try:
        d = int(digits)
    except (OverflowError, ValueError):
        return NUM
    # Decimal(str(float)) keeps the binary float's decimal form Calc sees.
    val = Decimal(str(x))
    quant = Decimal(1).scaleb(-d)
    try:
        out = val.quantize(quant, rounding=mode)
    except Exception:
        return NUM
    f = float(out)
    if not math.isfinite(f):
        return NUM
    return Number(f)


def ROUND(x, digits):
    a = _as_number(x)
    if is_error(a):
        return a
    b = _as_number(digits)
    if is_error(b):
        return b
    return _quantize(a.value, b.value, ROUND_HALF_UP)


def ROUNDUP(x, digits=None):
    a = _as_number(x)
    if is_error(a):
        return a
    b = _digits(digits, 0)
    if is_error(b):
        return b
    return _quantize(a.value, b.value, ROUND_UP)


def ROUNDDOWN(x, digits=None):
    a = _as_number(x)
    if is_error(a):
        return a
    b = _digits(digits, 0)
    if is_error(b):
        return b
    return _quantize(a.value, b.value, ROUND_DOWN)


def INT(x):
    a = _as_number(x)
    if is_error(a):
        return a
    return Number(math.floor(a.value))


def MOD(n, d):
    a = _as_number(n)
    if is_error(a):
        return a
    b = _as_number(d)
    if is_error(b):
        return b
    if b.value == 0:
        return DIV0
    # Calc: n - d * INT(n/d)
    q = math.floor(a.value / b.value)
    return Number(a.value - b.value * q)


def ABS(x):
    a = _as_number(x)
    if is_error(a):
        return a
    return Number(abs(a.value))


def POWER(x, y):
    a = _as_number(x)
    if is_error(a):
        return a
    b = _as_number(y)
    if is_error(b):
        return b
    try:
        z = a.value ** b.value
    except ZeroDivisionError:
        return DIV0
    except (OverflowError, ValueError):
        return NUM
    if isinstance(z, complex) or not math.isfinite(z):
        return NUM
    return Number(z)


def SQRT(x):
    a = _as_number(x)
    if is_error(a):
        return a
    if a.value < 0:
        return NUM
    return Number(math.sqrt(a.value))


FUNCTIONS = {
    "SUM": _apply(Number(0.0), _sum),
    "AVERAGE": _apply(DIV0, _average),
    "MIN": _apply(Number(0.0), _min),
    "MAX": _apply(Number(0.0), _max),
    "COUNT": _apply(Number(0.0), _count),
    "COUNTA": _counta,
    "PRODUCT": _apply(Number(0.0), _product),
    "MEDIAN": _apply(VALUE, _median),
    "STDEV": _apply(DIV0, _stdev),
    "ROUND": ROUND,
    "ROUNDUP": ROUNDUP,
    "ROUNDDOWN": ROUNDDOWN,
    "INT": INT,
    "MOD": MOD,
    "ABS": ABS,
    "POWER": POWER,
    "SQRT": SQRT,
}
