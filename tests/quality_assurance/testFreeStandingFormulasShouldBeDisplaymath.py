#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest

from MAGSBS.quality_assurance import latex

def check(formula):
    return latex.FreeStandingFormulasShouldBeDisplaymath().worker({1:
        formula.split('\n')})

class testFormulasSpanningAParagraphShouldBeDisplayMath(unittest.TestCase):
    def test_that_normal_paragraphs_are_ignored(self):
        result = check('bla\nblub\ndfdfkj')
        self.assertFalse(result, "expected that normal text is ignored, but got " + repr(result))

    def test_that_single_dollars_ignored(self):
        for text in ['This is $6', '$ should rule', 'I need $']:
            result = check(text)
            self.assertFalse(result,
                    "expected no error when checking {}, got {}".format(text, repr(result)))

    def test_that_display_math_not_detected_by_chance(self):
        self.assertFalse(check('$$\\pi\\tau$$'))

    def test_that_inline_maths_spanning_par_detected(self):
        self.assertTrue(check('$ok this is rather lengthy$'))

    def test_that_surrounding_spaces_dont_matter_and_still_trigger(self):
        self.assertTrue(check('    $ok this is rather lengthy$    '))
        self.assertTrue(check('\t$ok this is rather lengthy$\t'))
        self.assertTrue(check('   $mr hard$'))

    def test_that_proper_inline_math_envs_dont_trigger(self):
        self.assertFalse(check('\t$\\pi$ I do like.'))

    def test_that_multiple_inline_maths_on_a_line_dont_trigger(self):
        self.assertFalse(check('$abc$; we\'re tricking: $you$ '))
        
