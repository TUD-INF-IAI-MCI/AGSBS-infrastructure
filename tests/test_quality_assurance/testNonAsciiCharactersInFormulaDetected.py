#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest
from MAGSBS.quality_assurance.latex import NonAsciiCharactersInFormulaDetected

def check(formula):
    return NonAsciiCharactersInFormulaDetected().worker({(1,1):formula})

class TestNonAsciiCharactersInFormulaDetected(unittest.TestCase):
    def test_normal_formulas_are_ok(self):
        self.assertFalse(check('\\tau\\gamma\\alpha\'"{}'))

    def test_that_umlauts_within_text_ignored(self):
        self.assertFalse(check(r'\gamma\text{öäü}'))
        self.assertFalse(check(r'\gamma\text{öäü} \and \text{é}'))

    def test_umlauts_and_accents_in_formula_detected(self):
        self.assertTrue(check('öäü'))
        self.assertTrue(check('èí'))

    def test_that_unicode_signs_detected(self):
        self.assertTrue(check('ł~øæſðđ'))

