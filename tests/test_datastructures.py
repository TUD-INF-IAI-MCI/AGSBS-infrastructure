# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest, sys

sys.path.insert(0, ".")  # just in case
import MAGSBS.datastructures as datastructures
import MAGSBS.errors as errors
from MAGSBS.common import setup_i18n
import os

setup_i18n()


class test_gen_id(unittest.TestCase):
    def test_that_spaces_are_replaced_by_hyphens(self):
        self.assertEqual(datastructures.gen_id("hey du da"), "hey-du-da")

    def test_that_leading_hyphens_or_spaces_are_ignored(self):
        self.assertEqual(datastructures.gen_id("  - kk"), "kk")

    def test_that_hypens_in_middle_are_preserved(self):
        heading = "Remarkable - MarkDown saves time"
        result = datastructures.gen_id(heading)
        self.assertTrue(
            "able---" in result,
            "expected 'remarkable---' in id, got '{}'".format(result),
        )

    def test_that_exclamation_marks_etc_do_not_cause_trouble(self):
        exclamation = "this ! is bad"
        self.assertEqual(datastructures.gen_id(exclamation), "this-is-bad")
        question = "do I ? know"
        self.assertEqual(datastructures.gen_id(question), "do-i-know")

    def test_that_leading_numbers_are_ignored(self):
        self.assertEqual(datastructures.gen_id("01 hints and tips"), "hints-and-tips")

    def test_that_special_characters_are_ignored(self):
        self.assertEqual(datastructures.gen_id("$$foo##!bar"), "foobar")

    def test_numbers_in_the_middle_are_ok(self):
        self.assertEqual(datastructures.gen_id("a1b"), "a1b")

    def test_that_umlauts_are_still_contained(self):
        self.assertEqual(datastructures.gen_id("ärgerlich"), "ärgerlich")

    def test_that_case_is_converted_to_lower_case(self):
        self.assertEqual(datastructures.gen_id("uGlYWriTtEn"), "uglywritten")

    def test_that_empty_id_is_ok(self):
        # no exception, please
        self.assertEqual(datastructures.gen_id(""), "")

    def test_that_dots_at_beginning_are_ignored(self):
        self.assertFalse(datastructures.gen_id("...foo").startswith("."))

    def test_that_dots_in_middle_are_preserved(self):
        self.assertEqual(datastructures.gen_id("it . works"), "it-.-works")

    def test_that_no_double_hyphens_occur(self):
        examples = ["construct ) cases", "()foo", "a | b"]
        for text in examples:
            self.assertTrue("--" not in datastructures.gen_id(text))


################################################################################

# pylint: disable=protected-access
class TestFileCache(unittest.TestCase):
    def test_that_all_files_are_contained(self):
        files = [
            ("anh03", 0, ("anh0301.md", "anh0302.md")),
            ("k20", 0, ("k20.md",)),
            ("anh04", 0, ("anh04.md",)),
        ]
        f = datastructures.FileCache(files)
        for file in [e[2] for e in files]:
            file = file[0] if not isinstance(file, str) else file
            self.assertTrue(file in f, "%s should be contained in the cache" % file)

    def test_that_files_are_grouped_correctly(self):
        appendix = ("anh03", 0, ("anh0301.md", "anh0302.md"))
        preface = ("v04", 0, ("v04.md",))
        main = ("blatt05", 0, ("blatt05.md",))
        f = datastructures.FileCache((preface, main, appendix))
        self.assertEqual(
            f._FileCache__preface[0][1],
            preface[2][0],
            "%s should be contained in the preface group" % preface[2][0],
        )
        self.assertEqual(
            appendix[2][0],
            f._FileCache__appendix[0][1],
            "%s should be contained in the appendix group" % appendix[2][0],
        )
        self.assertEqual(
            main[2][0],
            f._FileCache__main[0][1],
            "%s should be contained in the main group" % main[2][0],
        )

    def test_that_invalid_file_names_raise_exception(self):
        with self.assertRaises(errors.StructuralError):
            datastructures.FileCache([("foo", 0, ("foobar.md",))])

    def test_that_get_neighbours_returns_correct_neighbours_or_none(self):
        files = [
            ("anh03", 0, ("anh0301.md", "anh0302.md")),
            ("v04", 0, ("v04.md",)),
            ("blatt05", 0, ("blatt05.md",)),
        ]
        f = datastructures.FileCache(files)
        # this one has two neighbours
        # ToDo: "in" must be used
        self.assertEqual(
            f.get_neighbours_for("blatt05/blatt05.md"),
            (("v04", "v04.md"), ("anh03", "anh0301.md")),
        )
        # this one has only a next
        self.assertEqual(
            f.get_neighbours_for("v04/v04.md"), (None, ("blatt05", "blatt05.md"))
        )
        # this one has only a previous
        self.assertEqual(
            f.get_neighbours_for("anh03/anh0302.md"), (("anh03", "anh0301.md"), None)
        )

    def test_requesting_neighbours_for_not_existing_files_raises_exception(self):
        f = datastructures.FileCache([("anh03", 0, ("anh0301.md",))])
        with self.assertRaises(errors.StructuralError):
            # pylint: disable=pointless-statement
            f.get_neighbours_for("fooo.md")

    def test_that_number_is_extracted_from_normal_file_name(self):
        self.assertEqual(2, datastructures.extract_chapter_number("k02.md"))

    def test_that_number_is_extracted_from_relative_paths_and_absolute_paths(self):
        self.assertEqual(
            datastructures.extract_chapter_number(os.path.join("k04", "k04.md")), 4
        )
        self.assertEqual(
            datastructures.extract_chapter_number(os.path.join("c:", "k09", "k09.md")),
            9,
        )
        self.assertEqual(datastructures.extract_chapter_number("k08/k08.md"), 8)

    def test_that_subchapter_files_work(self):
        self.assertEqual(datastructures.extract_chapter_number("k0501.md"), 5)
        self.assertEqual(datastructures.extract_chapter_number("k060201.md"), 6)

    def test_that_non_two_digit_numbers_raise_structural_error(self):
        with self.assertRaises(errors.StructuralError):
            datastructures.extract_chapter_number("k9.md")
            datastructures.extract_chapter_number("k029.md")

    def test_that_totally_wrong_file_names_raise_exception(self):
        with self.assertRaises(errors.StructuralError):
            datastructures.extract_chapter_number("paper.md")
            datastructures.extract_chapter_number("k11_old.md")
