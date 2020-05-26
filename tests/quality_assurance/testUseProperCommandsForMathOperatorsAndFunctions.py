# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest

from MAGSBS.quality_assurance import (
    UseProperCommandsForMathOperatorsAndFunctions,
)

check = lambda x: UseProperCommandsForMathOperatorsAndFunctions().worker(
    {(1, 1): x}
)


class TestUseProperCommandsForMathOperatorsAndFunctions(unittest.TestCase):
    def test_that_normal_functions_dont_trigger(self):
        self.assertFalse(check("foobar"))
        self.assertFalse(check(r"\gamma\alpha"))

    def test_that_properly_set_operators_dont_trigger(self):
        self.assertFalse(check(r"\max\{1,i\mid \ldots\}"))
        self.assertFalse(check(r"\sin(\pi)"))
        self.assertFalse(check(r"\cos(\frac\pi2)"))

    def test_that_operators_and_funcs_without_backslash_trigger(self):
        self.assertTrue(check(r"max\{1,i\mid \ldots\}"))
        self.assertTrue(check(r"sin(\pi)"))
        self.assertTrue(check(r"cos(\frac\pi2)"))

    def test_infix_matches_dont_trigger(self):
        self.assertFalse(check(r"A\setminus B"))
        self.assertFalse(check(r"A\setminus B"))
