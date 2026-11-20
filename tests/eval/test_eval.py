"""Behavior the operator checks do not cover: parse errors, calls, and ranges."""

import unittest

import src.functions.math as math_pkg
from src.eval import Range, evaluate, register, registry
from src.values import BLANK, NAME, REF, VALUE, Error, Number, Text, to_json


def _book():
    return {"sheets": {"Sheet1": {"A1": 1, "B1": 2, "A2": 3, "B2": 4}}}


class ParseTest(unittest.TestCase):
    def test_bad_formula_is_an_error(self):
        for formula in ("=1+", "=()", "nope", "", None):
            got = evaluate(formula, _book(), "Sheet1")
            self.assertIsInstance(got, Error)
            self.assertEqual(got, VALUE)


class CallTest(unittest.TestCase):
    def test_unknown_call_does_not_run_its_arguments(self):
        seen = []

        @register("t_seen")
        def mark():
            seen.append(1)
            return Number(1)

        got = evaluate("=NOSUCH(T_SEEN())", _book(), "Sheet1")
        self.assertEqual(got, NAME)
        self.assertEqual(seen, [])

        got = evaluate("=T_SEEN()", _book(), "Sheet1")
        self.assertEqual(got, Number(1))
        self.assertEqual(seen, [1])

    def test_omitted_argument_is_blank(self):
        seen = []

        @register("t_omit")
        def omit(*args):
            seen.append(args)
            return Number(0)

        evaluate("=T_OMIT(,1)", _book(), "Sheet1")
        self.assertIs(seen[0][0], BLANK)
        self.assertEqual(seen[0][1], Number(1))

    def test_registered_name_is_uppercase(self):
        @register("t_case")
        def f():
            return Number(1)

        names = registry()
        self.assertIn("T_CASE", names)
        self.assertNotIn("t_case", names)
        self.assertIs(names["T_CASE"], f)

    def test_package_function_is_used_at_call_time(self):
        def pkg():
            return Number(4)

        previous = getattr(math_pkg, "FUNCTIONS", None)
        math_pkg.FUNCTIONS = {"t_pkg": pkg}
        try:
            self.assertEqual(evaluate("=t_pkg()", _book(), "Sheet1"), Number(4))
        finally:
            if previous is None:
                del math_pkg.FUNCTIONS
            else:
                math_pkg.FUNCTIONS = previous

    def test_register_overrides_a_package_function(self):
        def pkg():
            return Number(4)

        @register("t_over")
        def direct():
            return Number(7)

        previous = getattr(math_pkg, "FUNCTIONS", None)
        math_pkg.FUNCTIONS = {"t_over": pkg}
        try:
            self.assertEqual(evaluate("=T_OVER()", _book(), "Sheet1"), Number(7))
        finally:
            if previous is None:
                del math_pkg.FUNCTIONS
            else:
                math_pkg.FUNCTIONS = previous


class RangeTest(unittest.TestCase):
    def test_stored_formula_is_not_recalculated(self):
        book = {"sheets": {"Sheet1": {"A1": "=1+1"}}}
        self.assertEqual(evaluate("=A1", book, "Sheet1"), Text("=1+1"))

    def test_multi_cell_range_in_arithmetic_is_value_error(self):
        book = _book()
        self.assertEqual(evaluate("=A1:A2+1", book, "Sheet1"), VALUE)
        self.assertEqual(evaluate("=A1:A1+1", book, "Sheet1"), Number(2))

    def test_unknown_sheet_cells_are_ref(self):
        seen = []

        @register("t_cells")
        def cells(r):
            seen.append(r.values())
            return Number(1)

        evaluate("=T_CELLS(Nope!A1:B1)", _book(), "Sheet1")
        self.assertEqual(seen[0], [REF, REF])

    def test_corners_walk_row_by_row_from_the_top_left(self):
        seen = []

        @register("t_walk")
        def walk(r):
            seen.append([to_json(v) for v in r.values()])
            return Number(0)

        evaluate("=T_WALK(B2:A1)", _book(), "Sheet1")
        self.assertEqual(seen[0], [1, 2, 3, 4])

    def test_returned_range_collapses_like_a_reference(self):
        book = {"sheets": {"Sheet1": {"Z9": None}}}

        @register("t_one")
        def one():
            return Range(book, "Sheet1", 1, 1, 1, 1)

        @register("t_blank")
        def blank():
            return Range(book, "Sheet1", 9, 26, 9, 26)

        @register("t_two")
        def two():
            return Range(book, "Sheet1", 1, 1, 1, 2)

        book["sheets"]["Sheet1"]["A1"] = 5
        self.assertEqual(evaluate("=T_ONE()+1", book, "Sheet1"), Number(6))
        self.assertEqual(evaluate("=T_BLANK()", book, "Sheet1"), Number(0))
        self.assertEqual(evaluate("=T_TWO()", book, "Sheet1"), VALUE)
