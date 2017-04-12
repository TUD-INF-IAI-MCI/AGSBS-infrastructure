import unittest, sys
sys.path.insert(0, '.') # just in case
import os

from MAGSBS import pagenumbering

EXAMPLE_DOCUMENT = """|| - Seite 1 -

|| - slide XI -
"""


class test_pagenumber(unittest.TestCase):

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


        

