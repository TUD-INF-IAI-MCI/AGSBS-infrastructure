# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest
import MAGSBS.errors as errors
import MAGSBS.quality_assurance
import MAGSBS.quality_assurance.markdown as ma


def is_error(obj):
    return isinstance(obj, MAGSBS.quality_assurance.meta.ErrorMessage)


class TestTextInItemizeShouldntStartWithItemizeCharacter(unittest.TestCase):
    def run_checker(self, *arguments):
        return ma.TextInItemizeShouldntStartWithItemizeCharacter().worker(*arguments)

    def test_that_normal_itemizes_are_notaffected(self):
        file = {1: ["- item", "- item", "- another"], 6: ["+ item", "+ item"]}
        self.assertTrue(self.run_checker(file) is None)

    def test_that_normale_enumerations_dont_trigger_error(self):
        file = {
            1: ["1. item", "2. item", "3. another"],
            6: ["+ item", "+ item"],
        }
        self.assertTrue(self.run_checker(file) is None)

    def test_that_itemize_with_enumeration_is_recognized(self):
        file = {1: ["- item", "- item", "- 3. another"]}
        self.assertTrue(is_error(self.run_checker(file)))
        file = {1: ["* item", "* item", "* 3. another"]}
        self.assertTrue(is_error(self.run_checker(file)))

    def test_that_enumerations_with_itemizes_are_recognized(self):
        file = {1: ["1. item", "2. item", "3. - another"]}
        self.assertTrue(is_error(self.run_checker(file)))

    def test_that_enumeration_with_enumeration_is_recognized(self):
        file = {1: ["1. item", "2. item", "3. 1. another"]}
        self.assertTrue(is_error(self.run_checker(file)))

    def test_that_indented_lists_work_as_well(self):
        file = {1: ["1. item", "    1. item", "    2. 1. another"]}
        self.assertTrue(is_error(self.run_checker(file)))

    def test_that_number_without_dot_is_not_recognized_as_sublist(self):
        file = {1: ["- item", "- item", "- 15% another"]}
        self.assertEqual(self.run_checker(file), None)

    def test_that_(self):
        data = {1: ["- - - -"]}
        self.assertEqual(self.run_checker(data), None)
        data = {3: ["* * * * *"]}
        self.assertEqual(self.run_checker(data), None)

    def test_that_bold_text_is_not_threated_as_sublist(self):
        data = {1: ["muh"], 3: ["- **foo**", "- bar", "- baz"]}
        self.assertEqual(self.run_checker(data), None)

    def test_that_(self):
        data = {1: ["muh"], 3: ["- 14.08.2019", "- bar", "- baz"]}
        self.assertEqual(self.run_checker(data), None)

    def test_that_slanted_text_is_not_treated_as_error(self):
        text = {
            1: [
                "- fooobar",
                "- *Cost = max \# of simultaneous accesses to a single bank*",
            ]
        }
        self.assertEqual(self.run_checker(text), None)

    def test_years_are_not_recognized_as_itemize_character(self):
        text = {1: ["- 2008.", "- 2009."]}
        self.assertEqual(self.run_checker(text), None)

    def test_that_bold_text_is_ok(self):
        text = {
            1: ["normal", "text"],
            4: [
                "* *blahblah*",
                "* *barbar*",
                "* *foobar*",
                "* *blubblub*",
                "* *last*",
            ],
        }
        self.assertEqual(self.run_checker(text), None)

    def test_that_hyphens_in_line_are_fine(self):
        text = {
            1: [
                "- this is normal text",
                "- without much sense",
                "- foo",
                "-    Je viens de recevoir un petit héritage - de ma grand-",
            ]
        }
        self.assertEqual(self.run_checker(text), None)
