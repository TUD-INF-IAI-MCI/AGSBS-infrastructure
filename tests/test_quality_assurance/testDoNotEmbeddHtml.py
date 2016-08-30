#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest

import MAGSBS.quality_assurance

def check(text):
    return MAGSBS.quality_assurance.DoNotEmbedHtml().check(1, text)

class testDoNotEmbeddHtml(unittest.TestCase):
    def test_normal_text_does_not_trigger_error(self):
        self.assertFalse(check('Dies ist < als das > hier.'))

    def test_that_lesser_and_greater_in_formula_are_ignored(self):
        self.assertFalse(check('Ok: $f<a/b; b/c>d$'))

    def test_that_line_breaks_are_recognized(self):
        self.assertTrue(check('<br>'))
        self.assertTrue(check('<br/>'))
        self.assertTrue(check('<br />'))
        self.assertTrue(check('<BR />'))

    def test_that_div_and_span_are_ignored(self):
        self.assertFalse(check('<div>foo</div>'))
        self.assertFalse(check('<DIV>FOO</DIV>'))
        self.assertFalse(check('<div class="foobar" attr="9">foo</div>'))
        self.assertFalse(check('<span>foo</span>'))
        self.assertFalse(check('<span>FOO</span>'))
        self.assertFalse(check('<span class="foobar" attr="9">foo</span>'))

    def test_that_opening_and_closing_tags_are_recognized(self):
        self.assertTrue(check('<body>foo</body>'))
        self.assertTrue(check('<a id="foobar">whatever</a>'))
        self.assertTrue(check('<A id="foobar">whatever</A>'))
        self.assertTrue(check('<A id="foobar" >whatever</ A>'))

    def test_that_stand_alone_tags_are_recognized(self):
        self.assertTrue(check('<p/>'))
        self.assertTrue(check('<P/>'))
        self.assertTrue(check('<p/ >'))
        self.assertTrue(check('<p />'))

