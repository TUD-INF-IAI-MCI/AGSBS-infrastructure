# pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest
from MAGSBS.quality_assurance.markdown import HyphensFromJustifiedTextWereRemoved
from MAGSBS.quality_assurance.meta import ErrorMessage


def checker(pars):
    c = HyphensFromJustifiedTextWereRemoved()
    return c.worker(pars)


def str2par(string):
    """Convert string into paragraphs:
    {line_numer : [line1, line2, ...]}
    """
    return {1: string.split("\n")}


class TestHyphensFromJustifiedTextWereRemoved(unittest.TestCase):
    def test_that_normal_paragraph_is_ok(self):
        par = str2par("This is a\nlot of text\ncausing no problems.")
        self.assertEqual(checker(par), None)

    def test_that_hyphen_within_paragraph_is_detected(self):
        par = str2par("some text\nwhich is not too leng-\nthy at all.")
        self.assertTrue(isinstance(checker(par), ErrorMessage))

    def test_that_hyphens_at_beginning_of_par_detected(self):
        par = str2par("This is a stupid al-\ngorithm which\n hopefully works.")
        self.assertTrue(isinstance(checker(par), ErrorMessage))

    def test_that_hypehsns_at_end_of_paragraphs_are_all_right(self):
        par = str2par("foo foo\nbar bar-")
        self.assertEqual(checker(par), None)

    def test_that_tables_dont_trigger_error(self):
        par = str2par("--- ----\na   b\nc   d\n--- ---")
        self.assertEqual(checker(par), None)

    def test_that_hyphen_at_end_of_line_and_no_word_at_next_line_is_ignored(self,):
        par = str2par("foo bar-\n+-----+...")
        self.assertEqual(checker(par), None)

    def test_that_and_or_und_on_next_line_are_tolerated(self):
        par = str2par("hard-\nand software")
        self.assertEqual(checker(par), None)
        par = str2par("Hard-\nund Software")
        self.assertEqual(checker(par), None)
