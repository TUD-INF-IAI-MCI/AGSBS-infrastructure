#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest

from MAGSBS.quality_assurance.markdown import BrokenImageLinksAreDetected
from MAGSBS.quality_assurance.meta import ErrorMessage

def checker(text):
    """Shorthand to call checker under test."""
    c = BrokenImageLinksAreDetected()
    return c.check(9, text)


def is_error(obj):
    return isinstance(obj, ErrorMessage)


class TestBrokenImageLinksAreDetected(unittest.TestCase):
    def test_forgotten_brackets_are_recognized(self):
        missing_left = '!bla](jo)'
        missing_right = '![foo(jo)'
        self.assertTrue(is_error(checker(missing_left)), "Expected an error, got %s" % checker(missing_left))
        self.assertTrue(is_error(checker(missing_right)), "Expected an error, got %s" % checker(missing_left))
    def test_that_missing_parenthesis_are_detected(self):
        missing_left = '![jo]bilder.md)'
        missing_right = '![jo](booo.md'
        self.assertTrue(is_error(checker(missing_left)),
                "expected type error, got %s " % type(checker(missing_left)))
        self.assertTrue(is_error(checker(missing_right)),
                "expected type error, got %s " % type(checker(missing_right)))

    def test_that_valid_images_is_ok(self):
        simple = '![jo](bilder.md)'
        self.assertFalse(is_error(checker(simple)), "Did not expect error, got it anyway: %s" % checker(simple))
        self.assertFalse(is_error(checker('')), "Did not expect error, got it anyway: %s" % checker(simple))
        self.assertFalse(is_error(checker('some_text')), "Did not expect error, got it anyway: %s" % checker(simple))

    def test_that_trailing_and_leading_text_is_ok(self):
        trailing = '![foo](bar) stuff'
        leading = 'jojo ![foo](bilder.jpg)'
        self.assertTrue(not is_error(checker(trailing)), "Did not expect error, got it anyway: %s" % checker(trailing))
        self.assertTrue(not is_error(checker(leading)), "Did not expect error, got it anyway: %s" % checker(leading))

    def test_that_indentation_is_ok(self):
        indented_s = '    ![foo](jpg)'
        indented_t = '\t![foo](jpg)'
        self.assertFalse(is_error(checker(indented_s)), "Did not expect error, got it anyway: %s" % checker(indented_s))
        self.assertFalse(is_error(checker(indented_t)), "Did not expect error, got it anyway: %s" % checker(indented_t))

    def test_that_nested_structure_work(self):
        nested = '[![this one is all right](bilder/bild.jpg)](some.html#file)'
        self.assertFalse(is_error(checker(nested)), "Did not expect error, got it anyway: %s" % checker(nested))

