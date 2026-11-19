"""Values, coercion and errors (intent i2-values).

Cell values as LibreOffice Calc has them: numbers, text, booleans, the blank cell
and the six errors. ``from_json``/``to_json`` map workbook cells both ways;
``to_number``, ``to_text`` and ``compare`` apply Calc's default coercion rules.
"""

import math
import re

__all__ = [
    "Number", "Text", "Bool", "Blank", "BLANK", "Error", "ERROR_CODES",
    "DIV0", "VALUE", "REF", "NAME", "NA", "NUM",
    "from_json", "to_json", "to_number", "to_text", "to_bool", "compare",
    "is_error", "format_number",
]

ERROR_CODES = ("#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#N/A", "#NUM!")


class Value:
    __slots__ = ()

    def __setattr__(self, name, value):
        raise AttributeError("values are immutable")


class Number(Value):
    __slots__ = ("value",)

    def __init__(self, value):
        object.__setattr__(self, "value", float(value))

    def __eq__(self, other):
        return isinstance(other, Number) and other.value == self.value

    def __hash__(self):
        return hash(("Number", self.value))

    def __repr__(self):
        return "Number(%r)" % (self.value,)


class Text(Value):
    __slots__ = ("value",)

    def __init__(self, value):
        object.__setattr__(self, "value", str(value))

    def __eq__(self, other):
        return isinstance(other, Text) and other.value == self.value

    def __hash__(self):
        return hash(("Text", self.value))

    def __repr__(self):
        return "Text(%r)" % (self.value,)


class Bool(Value):
    __slots__ = ("value",)

    def __init__(self, value):
        object.__setattr__(self, "value", bool(value))

    def __eq__(self, other):
        return isinstance(other, Bool) and other.value == self.value

    def __hash__(self):
        return hash(("Bool", self.value))

    def __repr__(self):
        return "Bool(%r)" % (self.value,)


class Blank(Value):
    """The blank (missing) cell; use the ``BLANK`` singleton."""

    __slots__ = ()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __eq__(self, other):
        return isinstance(other, Blank)

    def __hash__(self):
        return hash("Blank")

    def __repr__(self):
        return "BLANK"


BLANK = Blank()


class Error(Value):
    __slots__ = ("code",)

    def __init__(self, code):
        object.__setattr__(self, "code", str(code))

    def __eq__(self, other):
        return isinstance(other, Error) and other.code == self.code

    def __hash__(self):
        return hash(("Error", self.code))

    def __repr__(self):
        return "Error(%r)" % (self.code,)


DIV0 = Error("#DIV/0!")
VALUE = Error("#VALUE!")
REF = Error("#REF!")
NAME = Error("#NAME?")
NA = Error("#N/A")
NUM = Error("#NUM!")


def is_error(v):
    return isinstance(v, Error)


def from_json(j):
    """A workbook cell (1, "text", true, null, {"error": "#N/A"}) as a Value."""
    if isinstance(j, Value):
        return j
    if j is None:
        return BLANK
    if isinstance(j, bool):
        return Bool(j)
    if isinstance(j, (int, float)):
        return Number(j)
    if isinstance(j, str):
        return Text(j)
    if isinstance(j, dict) and isinstance(j.get("error"), str):
        return Error(j["error"])
    return VALUE


def to_json(v):
    """A Value as a workbook cell; an integral number is written as an integer."""
    if isinstance(v, Number):
        x = v.value
        if not math.isfinite(x):
            return {"error": NUM.code}
        if x == int(x) and abs(x) < 2 ** 53:
            return int(x)
        return x
    if isinstance(v, Text):
        return v.value
    if isinstance(v, Bool):
        return v.value
    if isinstance(v, Error):
        return {"error": v.code}
    if isinstance(v, Blank):
        return None
    raise TypeError("not a value: %r" % (v,))


# Calc's default "unambiguous" text-to-number: signed decimal, optional exponent.
_NUMBER_TEXT = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def to_number(v):
    """The operand of an arithmetic operator: a Number or an Error."""
    if isinstance(v, Number):
        return v if math.isfinite(v.value) else NUM
    if isinstance(v, Bool):
        return Number(1.0 if v.value else 0.0)
    if isinstance(v, Blank):
        return Number(0.0)
    if isinstance(v, Error):
        return v
    if isinstance(v, Text):
        if _NUMBER_TEXT.fullmatch(v.value):
            x = float(v.value)
            return Number(x) if math.isfinite(x) else NUM
        return VALUE
    return VALUE


def format_number(x):
    """Calc's general format: up to 15 significant digits, no trailing zeros."""
    if not math.isfinite(x):
        return "#NUM!"
    if x == 0:
        return "0"
    s = "%.15g" % x
    if "e" in s:
        mant, exp = s.split("e")
        if "." in mant:
            mant = mant.rstrip("0").rstrip(".")
        sign = exp[0]
        digits = exp[1:].lstrip("0").rjust(2, "0")
        return "%sE%s%s" % (mant, sign, digits)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def to_text(v):
    """The operand of ``&``: a Text or an Error."""
    if isinstance(v, Text):
        return v
    if isinstance(v, Number):
        return Text(format_number(v.value)) if math.isfinite(v.value) else NUM
    if isinstance(v, Bool):
        return Text("TRUE" if v.value else "FALSE")
    if isinstance(v, Blank):
        return Text("")
    if isinstance(v, Error):
        return v
    return VALUE


def to_bool(v):
    """A logical operand: a Bool or an Error (text is #VALUE!, blank is FALSE)."""
    if isinstance(v, Bool):
        return v
    if isinstance(v, Number):
        return Bool(v.value != 0)
    if isinstance(v, Blank):
        return Bool(False)
    if isinstance(v, Error):
        return v
    return VALUE


def _rank(v):
    # Calc orders numbers (booleans are numbers) before text.
    return 1 if isinstance(v, Text) else 0


def _sign(a, b):
    return (a > b) - (a < b)


def compare(a, b):
    """Compare two values as Calc's = <> < > <= >= do: -1, 0, 1 or an Error."""
    if isinstance(a, Error):
        return a
    if isinstance(b, Error):
        return b
    if isinstance(a, Blank) and isinstance(b, Blank):
        return 0
    if isinstance(a, Blank):
        a = Text("") if isinstance(b, Text) else Number(0.0)
    if isinstance(b, Blank):
        b = Text("") if isinstance(a, Text) else Number(0.0)
    ra, rb = _rank(a), _rank(b)
    if ra != rb:
        return _sign(ra, rb)
    if ra == 1:
        return _sign(a.value.casefold(), b.value.casefold())
    x = 1.0 if a.value is True else 0.0 if a.value is False else a.value
    y = 1.0 if b.value is True else 0.0 if b.value is False else b.value
    return _sign(x, y)
