#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest

from MAGSBS.quality_assurance.latex import SpacingInFormulaShouldBeDoneWithQuad

def check(lnum, pos, formula):
    return SpacingInFormulaShouldBeDoneWithQuad().worker({(lnum, pos): formula})

class TestSpacingInFormulaShouldBeDoneWithQuad(unittest.TestCase):
    def test_error_is_recognized(self):
        formula = r'Look at: $\pi\ \ \ \ \ \tau$'
        self.assertNotEqual(check(88, 1, formula), None)

    def test_normal_formulas_are_not_incorrectly_recognized(self):
        formula = r"Look at: $\pi\tau\ \foo\bar$"
        self.assertEqual(check(99, 1, formula), None)

