"""Parse a spreadsheet formula into an AST and render it."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass


class ParseError(Exception):
    """A formula that is not valid syntax."""


@dataclass(frozen=True, slots=True)
class Number:
    value: float


@dataclass(frozen=True, slots=True)
class Text:
    value: str


@dataclass(frozen=True, slots=True)
class Bool:
    value: bool


@dataclass(frozen=True, slots=True)
class Error:
    code: str


@dataclass(frozen=True, slots=True)
class Ref:
    sheet: str | None
    col: str
    row: int
    abs_col: bool
    abs_row: bool


@dataclass(frozen=True, slots=True)
class Range:
    start: Ref
    end: Ref


@dataclass(frozen=True, slots=True)
class Name:
    name: str


@dataclass(frozen=True, slots=True)
class Call:
    name: str
    args: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Missing:
    pass


@dataclass(frozen=True, slots=True)
class Unary:
    expr: Node


@dataclass(frozen=True, slots=True)
class Percent:
    expr: Node


@dataclass(frozen=True, slots=True)
class Binary:
    op: str
    left: Node
    right: Node


Node = (
    Number
    | Text
    | Bool
    | Error
    | Ref
    | Range
    | Name
    | Call
    | Missing
    | Unary
    | Percent
    | Binary
)

MISSING = Missing()

_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
    |(?P<string>"(?:[^"]|"")*")
    |(?P<error>\#(?:GETTING_DATA|DIV/0!|NULL!|NAME\?|VALUE!|NUM!|REF!|N/A))
    |(?P<number>(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)
    |(?P<op><=|>=|<>|[+\-*/^&=<>%])
    |(?P<punct>[(),:!])
    |(?P<sheet>'(?:[^']|'')*')
    |(?P<ref>\$?[A-Za-z]{1,3}\$?\d+)
    |(?P<ident>[A-Za-z_][A-Za-z0-9_.]*)
    """,
    re.VERBOSE | re.IGNORECASE,
)
_REF_PARTS = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)$", re.IGNORECASE)
_PLAIN_SHEET = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*$")


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    text: str


def _float(text: str) -> float:
    try:
        return float(text)
    except OverflowError:
        return math.inf


def tokenize(src: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    n = len(src)
    while i < n:
        match = _TOKEN.match(src, i)
        if match is None:
            raise ParseError(f"unexpected character {src[i]!r}")
        end = match.end()
        if end <= i:
            raise ParseError(f"unexpected character {src[i]!r}")
        kind = match.lastgroup
        if kind is None:
            raise ParseError(f"unexpected character {src[i]!r}")
        if kind != "ws":
            text = match.group(0)
            if kind == "error":
                text = text.upper()
            tokens.append(_Token(kind, text))
        i = end
    return tokens


class Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self.tokens = tokens
        self.i = 0

    def peek(self) -> _Token | None:
        if self.i >= len(self.tokens):
            return None
        return self.tokens[self.i]

    def peek_at(self, offset: int) -> _Token | None:
        j = self.i + offset
        if j >= len(self.tokens):
            return None
        return self.tokens[j]

    def peek_text(self) -> str | None:
        tok = self.peek()
        if tok is None:
            return None
        return tok.text

    def consume(self) -> _Token:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end")
        self.i += 1
        return tok

    def expect(self, text: str) -> _Token:
        tok = self.peek()
        if tok is None or tok.text != text:
            raise ParseError(f"expected {text!r}")
        return self.consume()

    def at_sheet_prefix(self) -> bool:
        tok = self.peek()
        if tok is None:
            return False
        if tok.kind == "sheet":
            return True
        if tok.kind != "ident":
            return False
        nxt = self.peek_at(1)
        return nxt is not None and nxt.text == "!"

    def take_sheet(self) -> str:
        tok = self.consume()
        if tok.kind == "sheet":
            name = tok.text[1:-1].replace("''", "'")
        elif tok.kind == "ident":
            name = tok.text
        else:
            raise ParseError("expected a sheet name")
        self.expect("!")
        return name

    def parse_expr(self) -> Node:
        left = self.parse_concat()
        while self.peek_text() in ("=", "<>", "<", ">", "<=", ">="):
            op = self.consume().text
            right = self.parse_concat()
            left = Binary(op, left, right)
        return left

    def parse_concat(self) -> Node:
        left = self.parse_add()
        while self.peek_text() == "&":
            self.consume()
            right = self.parse_add()
            left = Binary("&", left, right)
        return left

    def parse_add(self) -> Node:
        left = self.parse_mul()
        while self.peek_text() in ("+", "-"):
            op = self.consume().text
            right = self.parse_mul()
            left = Binary(op, left, right)
        return left

    def parse_mul(self) -> Node:
        left = self.parse_pow()
        while self.peek_text() in ("*", "/"):
            op = self.consume().text
            right = self.parse_pow()
            left = Binary(op, left, right)
        return left

    def parse_pow(self) -> Node:
        left = self.parse_percent()
        while self.peek_text() == "^":
            self.consume()
            right = self.parse_percent()
            left = Binary("^", left, right)
        return left

    def parse_percent(self) -> Node:
        node = self.parse_unary()
        while self.peek_text() == "%":
            self.consume()
            node = Percent(node)
        return node

    def parse_unary(self) -> Node:
        if self.peek_text() == "+":
            self.consume()
            return self.parse_unary()
        if self.peek_text() == "-":
            self.consume()
            return Unary(self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> Node:
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end")
        if tok.text == "(":
            self.consume()
            if self.peek_text() == ")":
                raise ParseError("empty parentheses")
            node = self.parse_expr()
            self.expect(")")
            return node
        if tok.kind == "number":
            self.consume()
            return Number(_float(tok.text))
        if tok.kind == "string":
            self.consume()
            return Text(tok.text[1:-1].replace('""', '"'))
        if tok.kind == "error":
            self.consume()
            return Error(tok.text)
        if tok.kind == "sheet" or self.at_sheet_prefix():
            return self.parse_ref_or_range(self.take_sheet())
        if tok.kind == "ref":
            return self.parse_ref_or_range(None)
        if tok.kind == "ident":
            nxt = self.peek_at(1)
            if nxt is not None and nxt.text == "(":
                name = self.consume().text.upper()
                return Call(name, tuple(self.parse_arg_list()))
            self.consume()
            upper = tok.text.upper()
            if upper == "TRUE":
                return Bool(True)
            if upper == "FALSE":
                return Bool(False)
            return Name(tok.text)
        raise ParseError(f"unexpected {tok.text!r}")

    def parse_arg_list(self) -> list[Node]:
        self.expect("(")
        if self.peek_text() == ")":
            self.consume()
            return []
        args: list[Node] = []
        while True:
            if self.peek_text() in (",", ")"):
                args.append(MISSING)
            else:
                args.append(self.parse_expr())
            if self.peek_text() == ",":
                self.consume()
                continue
            if self.peek_text() == ")":
                self.consume()
                return args
            raise ParseError("expected ',' or ')'")

    def parse_ref_or_range(self, sheet: str | None) -> Ref | Range:
        start = self.parse_ref(sheet)
        if self.peek_text() != ":":
            return start
        self.consume()
        end_sheet = self.take_sheet() if self.at_sheet_prefix() else None
        return Range(start, self.parse_ref(end_sheet))

    def parse_ref(self, sheet: str | None) -> Ref:
        tok = self.peek()
        if tok is None or tok.kind != "ref":
            raise ParseError("expected a cell reference")
        self.consume()
        match = _REF_PARTS.fullmatch(tok.text)
        if match is None:
            raise ParseError("expected a cell reference")
        abs_col, col, abs_row, row = match.groups()
        return Ref(sheet, col.upper(), int(row), abs_col == "$", abs_row == "$")


def parse(formula: str) -> Node:
    """Parse a formula that starts with '='."""
    if not isinstance(formula, str):
        raise ParseError("formula must be a string")
    try:
        parser = Parser(tokenize(formula))
        parser.expect("=")
        node = parser.parse_expr()
        if parser.peek() is not None:
            raise ParseError("trailing input")
        return node
    except RecursionError as exc:
        raise ParseError("formula is too deeply nested") from exc


def _local(ref: Ref) -> str:
    col = f"${ref.col}" if ref.abs_col else ref.col
    row = f"${ref.row}" if ref.abs_row else str(ref.row)
    return f"{col}{row}"


def _show_sheet(name: str) -> str:
    if _PLAIN_SHEET.fullmatch(name):
        return name
    return "'" + name.replace("'", "''") + "'"


def _show_ref(ref: Ref) -> str:
    local = _local(ref)
    if ref.sheet is None:
        return local
    return f"{_show_sheet(ref.sheet)}!{local}"


def _show_range(node: Range) -> str:
    left, right = node.start, node.end
    sheet = left.sheet
    if sheet is not None and (right.sheet is None or right.sheet == sheet):
        return f"{_show_sheet(sheet)}!{_local(left)}:{_local(right)}"
    return f"{_show_ref(left)}:{_show_ref(right)}"


def show(node: Node) -> str:
    """Return the canonical text for a parsed formula."""
    if isinstance(node, Number):
        return repr(node.value)
    if isinstance(node, Text):
        return json.dumps(node.value)
    if isinstance(node, Bool):
        return "TRUE" if node.value else "FALSE"
    if isinstance(node, Error):
        return node.code
    if isinstance(node, Ref):
        return _show_ref(node)
    if isinstance(node, Range):
        return _show_range(node)
    if isinstance(node, Name):
        return node.name
    if isinstance(node, Call):
        parts = [node.name]
        parts.extend(show(arg) for arg in node.args)
        return "(" + " ".join(parts) + ")"
    if isinstance(node, Missing):
        return "_"
    if isinstance(node, Unary):
        return f"(neg {show(node.expr)})"
    if isinstance(node, Percent):
        return f"(% {show(node.expr)})"
    if isinstance(node, Binary):
        return f"({node.op} {show(node.left)} {show(node.right)})"
    raise ParseError("unknown formula node")


__all__ = [
    "Binary",
    "Bool",
    "Call",
    "Error",
    "MISSING",
    "Missing",
    "Name",
    "Number",
    "ParseError",
    "Percent",
    "Range",
    "Ref",
    "Text",
    "Unary",
    "parse",
    "show",
]
