# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest
import MAGSBS.quality_assurance as qa
import MAGSBS.quality_assurance.markdown as ma


class test_ParagraphMayNotEndOnBackslash(unittest.TestCase):
    def test_normal_paragraphs_are_recognized(self):
        content1 = {1: ["line1", "line2", "line3"]}
        content2 = {1: ["line1", "line2", "line3",], 8: ["foo", "bar"]}
        self.assertEqual(
            ma.ParagraphMayNotEndOnBackslash().worker(content1, "dummy"), None
        )
        self.assertEqual(
            ma.ParagraphMayNotEndOnBackslash().worker(content2, "dummy"), None
        )

    def test_that_error_case_is_correctly_identified(self):
        content = {1: ["a", "b", "c\\"], 5: ["dummy"]}
        err_obj = ma.ParagraphMayNotEndOnBackslash().worker(content, "dummy")
        self.assertTrue(isinstance(err_obj, qa.meta.ErrorMessage))
