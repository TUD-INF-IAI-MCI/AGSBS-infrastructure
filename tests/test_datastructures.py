#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest, sys
sys.path.insert(0, '.') # just in case
import MAGSBS.datastructures as datastructures

class test_gen_id(unittest.TestCase):
    def test_that_spaces_are_replaced_by_hyphens(self):
        self.assertEqual(datastructures.gen_id('hey du da'), 'hey-du-da')

    def test_that_leading_hyphens_or_spaces_are_ignored(self):
        self.assertEqual(datastructures.gen_id('  - kk'), 'kk')

    def test_that_leading_numbers_are_ignored(self):
        self.assertEqual(datastructures.gen_id('01 hints and tips'),
            'hints-and-tips')

    def test_that_special_characters_are_ignored(self):
        self.assertEqual(datastructures.gen_id('$$foo##!bar'), 'foobar')

    def test_numbers_in_the_middle_are_ok(self):
        self.assertEqual(datastructures.gen_id('a1b'), 'a1b')


    def test_that_umlauts_are_still_contained(self):
        self.assertEqual(datastructures.gen_id('ärgerlich'), 'ärgerlich')

    def test_that_case_is_converted_to_lower_case(self):
        self.assertEqual(datastructures.gen_id('uGlYWriTtEn'), 'uglywritten')

    def test_that_empty_id_is_ok(self):
        # no exception, please
        self.assertEqual(datastructures.gen_id(''), '')

    def test_that_dots_at_beginning_are_ignored(self):
        self.assertFalse(datastructures.gen_id('...foo').startswith('.'))

