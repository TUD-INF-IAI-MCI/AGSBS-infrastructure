import unittest
import MAGSBS
import os
import MAGSBS.pagenumber as pm

class test_pagenumber(unittest.TestCase):

    ##############################################################
    # test pagenumbering
    def test_that_pagenumber_before_line_number_is_found(self):
        content = {1:['|| - Seite 1 -'], 2:['Text'], 3:['|| Text'], 4:['|| - Seite 2 -']}
        pagenum = pm.get_page_number(os.path.realpath("test_pagenumber.md"), 3)
        self.assertEqual(2, pagenum)

    
