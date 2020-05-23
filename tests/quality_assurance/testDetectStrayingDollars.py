# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
# absolute imports are fine: we're running test cases from the top directory
import MAGSBS.quality_assurance.markdown as ma
import MAGSBS.quality_assurance.meta as meta
import unittest


def check(line, lnum=1):
    checker = ma.DetectStrayingDollars()
    return checker.check(lnum, line)


class test_DetectStrayingDollars(unittest.TestCase):
    def test_normal_formulas_work_fine(self):
        correct_inlinemath = r"$\sigma + \omega$"
        result = check(correct_inlinemath)
        self.assertEqual(result, None)

    def test_open_math_environments_are_detected(self):
        correct_string = r"$\sigma"
        result = check(correct_string)
        self.assertTrue(isinstance(result, meta.ErrorMessage))

    def test_error_obj_include_line_number(self):
        correct_string = r"$\sigma"
        result = check(correct_string, 80)
        self.assertEqual(result.lineno, 80)

    def test_displaymath_with_newline_is_correct(self):
        second_line = r"\sigma + \omega$$"
        self.assertEqual(check(second_line), None)

    def test_that_dollar_without_closing_dollar_detected(self):
        text = r"Hier kommt eine Formel $\sigma + 1  und ein Dollarzeichen wurde vergessen."
        self.assertNotEqual(check(text), None)

    def test_that_escaped_dollars_are_ignored(self):
        text = "formula: $jo$ and \$ is ignored"
        self.assertEqual(check(text), None)

    def test_that_prices_are_ignored(self):
        text = r"This is $9."
        self.assertEqual(check(text), None)

    def test_that_straying_dollar_at_end_detected(self):
        text = r"The formula is 3\cdot 2$"
        self.assertNotEqual(check(text), None)
