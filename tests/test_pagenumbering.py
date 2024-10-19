from re import Pattern
import unittest, sys

sys.path.insert(0, ".")  # just in case
import os

import MAGSBS
from MAGSBS import pagenumbering

EXAMPLE_DOCUMENT = """|| - Seite 1 -

|| - slide XI -

|| - page 100-103 -
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
        newpnum = pagenumbering.add_page_number_from_str(EXAMPLE_DOCUMENT, 6)
        self.assertEqual(newpnum.number, 104)

    def test_that_roman_numbers_are_detected(self):
        mydocument = """|| - Seite I -

|| - Seite C -

|| - Seite 320 -


|| - Seite II-III -
"""
        newpnum = pagenumbering.add_page_number_from_str(mydocument, 2)
        self.assertEqual(newpnum.number, 2)
        self.assertFalse(newpnum.arabic)

        newpnum = pagenumbering.add_page_number_from_str(mydocument, 4)
        self.assertEqual(newpnum.number, 101)
        self.assertFalse(newpnum.arabic)

        newpnum = pagenumbering.add_page_number_from_str(mydocument, 7)
        self.assertEqual(newpnum.number, 321)
        self.assertTrue(newpnum.arabic)

        newpnum = pagenumbering.add_page_number_from_str(mydocument, 9)
        self.assertEqual(newpnum.number, 4)
        self.assertFalse(newpnum.arabic)


class TestCheckPageNumbering(unittest.TestCase):
    def test_monotonic_increasing_is_fine(self):
        pnums = [mkpnum(1, 1), mkpnum(3, 2), mkpnum(5, 3), mkpnum(20, 4)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])
        # roman numbers
        pnums = [
            mkpnum(1, 1, False),
            mkpnum(3, 2, False),
            mkpnum(5, 3, False),
            mkpnum(20, 4, False),
        ]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(2, 1),
            mkpnum(4, range(2, 5)),
            mkpnum(6, 6),
            mkpnum(7, range(7, 21)),
            mkpnum(11, range(22, 25)),
        ]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(2, 1, False),
            mkpnum(4, range(2, 5), False),
            mkpnum(6, 6, False),
            mkpnum(7, range(7, 21), False),
            mkpnum(11, range(22, 25), False),
        ]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

    def test_starting_at_arbitrary_number_works(self):
        pnums = [mkpnum(1, 10), mkpnum(3, 11), mkpnum(5, 12), mkpnum(20, 13)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])
        # roman numbers
        pnums = [
            mkpnum(1, 10, False),
            mkpnum(3, 11, False),
            mkpnum(5, 12, False),
            mkpnum(20, 13, False),
        ]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 10),
            mkpnum(3, range(11, 15)),
            mkpnum(8, range(16, 28)),
            mkpnum(20, 29),
            mkpnum(50, range(30, 31)),
        ]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 10, False),
            mkpnum(3, range(11, 15), False),
            mkpnum(8, range(16, 28), False),
            mkpnum(20, 29, False),
            mkpnum(50, range(30, 31), False),
        ]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])

    def test_jumps_are_not_tolerated(self):
        pnums = [mkpnum(1, 10), mkpnum(3, 11), mkpnum(5, 12), mkpnum(20, 19)]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])
        # roman numbers
        pnums = [
            mkpnum(1, 10, False),
            mkpnum(3, 11, False),
            mkpnum(5, 12, False),
            mkpnum(20, 18, False),
        ]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 10),
            mkpnum(3, range(11, 14)),
            mkpnum(5, 15),
            mkpnum(20, 18),
        ]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 10, False),
            mkpnum(3, range(11, 14), False),
            mkpnum(5, 15, False),
            mkpnum(20, 18, False),
        ]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 9),
            mkpnum(3, range(11, 14)),
            mkpnum(5, 15),
            mkpnum(20, 16),
        ]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 9, False),
            mkpnum(3, range(11, 14), False),
            mkpnum(5, 15, False),
            mkpnum(20, 16, False),
        ]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 10),
            mkpnum(3, range(11, 14)),
            mkpnum(5, 15),
            mkpnum(20, 16),
            mkpnum(100, range(18, 100)),
        ]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

        pnums = [
            mkpnum(1, 10, False),
            mkpnum(3, range(11, 14), False),
            mkpnum(5, 15, False),
            mkpnum(20, 16, False),
            mkpnum(100, range(18, 100), False),
        ]
        self.assertNotEqual(pagenumbering.check_page_numbering(pnums), [])

    def test_all_numbers_after_erroneous_are_reported(self):
        pnums = [mkpnum(1, 2), mkpnum(3, 11), mkpnum(5, 12), mkpnum(20, 19)]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)
        # roman numbers
        pnums = [
            mkpnum(1, 2, False),
            mkpnum(3, 11, False),
            mkpnum(5, 12, False),
            mkpnum(20, 18, False),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)

        pnums = [
            mkpnum(1, 2),
            mkpnum(3, range(12, 14)),
            mkpnum(5, 15),
            mkpnum(20, 18),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)

        pnums = [
            mkpnum(1, 2, False),
            mkpnum(3, range(12, 14), False),
            mkpnum(5, 15, False),
            mkpnum(20, 18, False),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)

        pnums = [
            mkpnum(1, range(1, 2)),
            mkpnum(3, range(12, 14)),
            mkpnum(5, 15),
            mkpnum(20, 18),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)

        pnums = [
            mkpnum(1, range(1, 2), False),
            mkpnum(3, range(12, 14), False),
            mkpnum(5, 15, False),
            mkpnum(20, 18, False),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 3)

    def test_style_changes_are_correctly_handled(self):
        # if the style changes, errors are no errors anymore
        pnums = [mkpnum(1, 10), mkpnum(3, 11), mkpnum(5, 99, False)]
        self.assertEqual(pagenumbering.check_page_numbering(pnums), [])
        # provoke error, continue normal
        pnums = [
            mkpnum(1, 10),
            mkpnum(3, 22),
            mkpnum(5, 98, False),
            mkpnum(20, 99, False),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 1)

        pnums = [
            mkpnum(1, 10),
            mkpnum(3, range(12, 16)),
            mkpnum(5, 98, False),
            mkpnum(20, 99, False),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 1)

        pnums = [
            mkpnum(1, 10),
            mkpnum(3, range(11, 16)),
            mkpnum(5, 98, False),
            mkpnum(7, range(99, 101), False),
            mkpnum(20, 103, False),
            mkpnum(23, range(105, 200)),
        ]
        self.assertEqual(len(pagenumbering.check_page_numbering(pnums)), 1)

    def test_reversed_ranges_are_correctly_handled(self):
        pnums = [
            mkpnum(1, range(2, 1)),
            mkpnum(3, range(3, 4)),
            mkpnum(6, 5),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], range(1, 2))

        pnums = [
            mkpnum(1, range(2, 1), False),
            mkpnum(3, range(3, 4), False),
            mkpnum(6, 5, False),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], range(1, 2))

        pnums = [
            mkpnum(1, range(1, 2)),
            mkpnum(3, range(3, 4)),
            mkpnum(6, 5),
            mkpnum(10, range(10, 7)),
            mkpnum(20, range(10, 20)),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], range(6, 9))

        pnums = [
            mkpnum(1, range(1, 2), False),
            mkpnum(3, range(3, 4), False),
            mkpnum(6, 5, False),
            mkpnum(10, range(10, 7), False),
            mkpnum(20, range(10, 20), False),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], range(6, 9))

        # Mixes.
        pnums = [
            mkpnum(1, range(1, 2), False),
            mkpnum(3, range(3, 4), False),
            mkpnum(6, 5, True),
            mkpnum(10, range(10, 7), False),
            mkpnum(20, range(11, 20), False),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], range(7, 10))

        pnums = [
            mkpnum(1, range(2, 1), True),
            mkpnum(3, range(3, 4), False),
            mkpnum(6, 5, True),
            mkpnum(10, range(9, 10), False),
            mkpnum(20, range(11, 20), False),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], range(1, 2))

        pnums = [
            mkpnum(1, range(1, 2), False),
            mkpnum(3, range(3, 4), False),
            mkpnum(6, 5, False),
            mkpnum(10, range(20, 10), True),
            mkpnum(20, range(11, 20), False),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], range(10, 20))

    def test_single_element_ranges_are_conflated(self):
        pnums = [
            mkpnum(24, range(4, 4)),
            mkpnum(26, 5),
            mkpnum(30, 6),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], 4)

        pnums = [
            mkpnum(24, range(4, 4), False),
            mkpnum(26, 5, False),
            mkpnum(30, 6, False),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], 4)

        pnums = [
            mkpnum(24, range(4, 7)),
            mkpnum(26, 8),
            mkpnum(30, 9),
            mkpnum(32, range(11, 11)),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], 10)

        pnums = [
            mkpnum(24, range(4, 7), False),
            mkpnum(26, 8, False),
            mkpnum(30, 9, False),
            mkpnum(32, range(11, 11), False),
        ]
        res = pagenumbering.check_page_numbering(pnums)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], 10)
