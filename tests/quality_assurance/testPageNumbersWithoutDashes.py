# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
# absolute imports are fine: test cases are running from the source root anyway
import MAGSBS.quality_assurance.markdown as ma
import MAGSBS.quality_assurance.meta as meta

import unittest


class TestPageNumbersWithoutDashes(unittest.TestCase):
    def test_normal_page_numbers_work_fine(self):
        checker = ma.PageNumbersWithoutDashes()
        result = checker.worker({1: ["|| - Seite 8 -"]})
        self.assertEqual(result, None)

    def test_normal_page_numbers_without_spaceswork_fine(self):
        checker = ma.PageNumbersWithoutDashes()
        result = checker.worker({1: ["||-Seite 8-"]})
        self.assertEqual(result, None)

    def test_that_missing_leading_dash_is_detected(self):
        checker = ma.PageNumbersWithoutDashes()
        result = checker.worker({1: ["|| Seite 8 -"]})
        self.assertTrue(isinstance(result, meta.ErrorMessage))

    def test_that_missing_trailing_dash_is_detected(self):
        checker = ma.PageNumbersWithoutDashes()
        result = checker.worker({1: ["|| - Seite 8"]})
        self.assertTrue(isinstance(result, meta.ErrorMessage))

    def test_that_spaces_at_the_end_dont_trigger(self):
        checker = ma.PageNumbersWithoutDashes()
        result = checker.worker({1: ["|| - Seite 8 - "]})
        self.assertFalse(isinstance(result, meta.ErrorMessage))
        result = checker.worker({1: ["|| - Seite 8 -\t"]})
        self.assertFalse(isinstance(result, meta.ErrorMessage))
