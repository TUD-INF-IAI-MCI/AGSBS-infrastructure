#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest
from MAGSBS.quality_assurance import latex
from MAGSBS.quality_assurance import meta

def iserror(obj):
    return isinstance(obj, meta.ErrorMessage)

def check(text):
    return latex.DisplayMathShouldNotBeUsedWithinAParagraph().check(1, text)

class testDisplayMathShouldNotBeInsideAParagraph(unittest.TestCase):
    def test_error_is_not_triggered_for_correct_formulas(self):
        self.assertFalse(iserror(check("dies ist normaler text")))
        self.assertFalse(iserror(check("dies $ist$ normaler text")))

    def test_that_displaymath_detected(self):
        self.assertTrue(iserror(check("this $$is$$ errorneous")))

    def test_that_formulas_at_beginning_or_end_of_line_detected(self):
        self.assertTrue(iserror(check("$$is$$ errorneous")))
        self.assertTrue(iserror(check("this $$is$$")))

    def test_isolated_paragraph_is_no_problem(self):
        self.assertFalse(iserror(check("$$jo$$")))
        self.assertFalse(iserror(check("    $$jo$$")))
        self.assertFalse(iserror(check("\t$$jo$$")))

    def test_that_multiple_displaymaths_are_detected(self):
        self.assertTrue(iserror(check("jo $$a$$ and $$b$$")))

