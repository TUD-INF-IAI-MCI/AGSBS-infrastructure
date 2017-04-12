import unittest, sys
sys.path.insert(0, '.') # just in case
import os

import MAGSBS
from MAGSBS import pagenumbering

EXAMPLE_DOCUMENT = """|| - Seite 1 -

|| - slide XI -
"""


def mkpnum(line, num, arabic=True):
    """Shortcut for creating a page number."""
    p = MAGSBS.datastructures.PageNumber("Slide", num, is_arabic=arabic)
    p.line_no = num
    return p

class test_add_pagenumber(unittest.TestCase):

    ##############################################################
    # test pagenumbering
    def test_that_pagenumber_before_line_number_is_found(self):
        newpnum = pagenumbering.add_page_number_from_str(EXAMPLE_DOCUMENT, 2)
        self.assertEqual(newpnum.number, 2)
        newpnum = pagenumbering.add_page_number_from_str(EXAMPLE_DOCUMENT, 4)
        self.assertEqual(newpnum.number, 12)

    def test_that_roman_numbers_are_detected(self):
        mydocument = """|| - Seite I -

|| - Seite C -

|| - Seite 320 -\n"""
        newpnum = pagenumbering.add_page_number_from_str(mydocument, 2)
        self.assertEqual(newpnum.number, 2)
        self.assertFalse(newpnum.arabic)

        newpnum = pagenumbering.add_page_number_from_str(mydocument, 4)
        self.assertEqual(newpnum.number, 101)
        self.assertFalse(newpnum.arabic)

        newpnum = pagenumbering.add_page_number_from_str(mydocument, 7)
        self.assertEqual(newpnum.number, 321)
        self.assertTrue(newpnum.arabic)


class TestCheckPageNumbering(unittest.TestCase):
    def test_monotonic_increasing_is_fine(self):
        pnums = [mkpnum(1, 1), mkpnum(3, 2), mkpnum(5, 3), mkpnum(20, 4)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])
        # roman numbers
        pnums = [mkpnum(1, 1, False), mkpnum(3, 2, False),
                mkpnum(5, 3, False), mkpnum(20, 4, False)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

    def test_starting_at_arbitrary_number_works(self):
        pnums = [mkpnum(1, 10), mkpnum(3, 11), mkpnum(5, 12), mkpnum(20, 13)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])
        # roman numbers
        pnums = [mkpnum(1, 10, False), mkpnum(3, 11, False), mkpnum(5, 12, False),
                mkpnum(20, 13, False)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

    def test_jumps_are_not_tolerated(self):
        pnums = [mkpnum(1, 10), mkpnum(3, 11), mkpnum(5, 12), mkpnum(20, 19)]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])
        # roman numbers
        pnums = [mkpnum(1, 10, False), mkpnum(3, 11, False), mkpnum(5, 12, False),
                mkpnum(20, 18, False)]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

    def test_all_numbers_after_errneous_are_reported(self):
        pnums = [mkpnum(1, 2), mkpnum(3, 11), mkpnum(5, 12), mkpnum(20, 19)]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)
        # roman numbers
        pnums = [mkpnum(1, 2, False), mkpnum(3, 11, False), mkpnum(5, 12, False),
                mkpnum(20, 18, False)]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)

    def test_style_changes_are_correctly_handled(self):
        # if the style changes, errors are no errors anymore
        pnums = [mkpnum(1, 10), mkpnum(3, 11), mkpnum(5, 99, False)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])
        # provoke error, continue normal
        pnums = [mkpnum(1, 10), mkpnum(3, 22), mkpnum(5, 98, False),
                mkpnum(20, 99, False)]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 1)
       

