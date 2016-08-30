#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
# absolute imports are fine: we're running test cases from the top directory
import MAGSBS.quality_assurance.markdown as ma
import MAGSBS.quality_assurance.meta as meta
import unittest

class test_InlineMathsShouldntContainNewlines(unittest.TestCase):
    def test_normal_formulas_work_fine(self):
        correct_inlinemath = r"$\sigma + \omega$"
        checker = ma.InlineMathsShouldntContainNewlines()
        result = checker.check(1, correct_inlinemath)
        self.assertEqual(result, None)

    def test_open_math_environments_are_detected(self):
        correct_string = r"$\sigma"
        checker = ma.InlineMathsShouldntContainNewlines()
        result = checker.check(1, correct_string)
        self.assertTrue(isinstance(result, meta.ErrorMessage))

    def test_error_obj_include_line_number(self):
        correct_string = r"$\sigma"
        checker = ma.InlineMathsShouldntContainNewlines()
        result = checker.check(1, correct_string)
        self.assertEqual(result.lineno, 1)

    def test_displaymath_with_newline_is_correct(self):
        second_line = r"\sigma + \omega$$"
        checker = ma.InlineMathsShouldntContainNewlines()
        self.assertEqual(checker.check(1, second_line), None)



# errors include (correct) line numer
# displaymath with newline are all right
