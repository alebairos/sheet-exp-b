"""Aggregate functions (wi-i5-math-1).

A range yields numbers, with blanks and text left out and booleans as 1 and 0.
The first error in that walk is the result. COUNTA counts every non-blank.
"""

import math

from src.values import (
    DIV0,
    NUM,
    VALUE,
    Blank,
    Bool,
    Number,
    Text,
    is_error,
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
}
