# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest
from MAGSBS.quality_assurance import CasesSqueezedOnOneLine


class testCasesSqueezedOnOneLine(unittest.TestCase):
    def test_that_errorneous_case_is_detected(self):
        err = CasesSqueezedOnOneLine().worker(
            {(1, 1): r"\begin{cases}a&b\\c&d\end{cases}"}
        )
        self.assertTrue(err, "error expected, got %s" % repr(err))

    def test_that_proper_case_environments_are_ignored(self):
        err = CasesSqueezedOnOneLine().worker(
            {(1, 1): "\\begin{cases}a&b\\\\\nc&d\\end{cases}"}
        )
        self.assertFalse(err, "Expected nothing, got " + repr(err))
