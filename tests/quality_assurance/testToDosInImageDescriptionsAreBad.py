#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable
import unittest
from MAGSBS.quality_assurance.meta import ErrorMessage
import MAGSBS.quality_assurance.markdown as ma

class TestToDosInImageDescriptionsAreBad(unittest.TestCase):
    def is_error(self, potential_error):
        self.assertTrue(isinstance(potential_error, ErrorMessage),
            "Expected an object of type quality_assurance.meta.ErrorMessage, " + \
            "got " + repr(potential_error))

    def test_lower_case_is_detected(self):
        line = 'Bildbeschreibung, todo'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))
        line = 'todo, muss beschrieben werden'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))

    def test_lower_case_with_space_is_detected(self):
        line = 'to do, muss beschrieben werden'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))
        line = 'Bildbeschreibung, to  do'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))

    def test_camel_case_is_dtected(self):
        line = 'Bildbeschreibung, ToDo'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))
        line = 'Bildbeschreibung, To Do'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))

    def test_full_caps_is_detected(self):
        line = 'Bildbeschreibung, TODO'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))
        line = 'TO DO: beschreibe mich'
        self.is_error(ma.ToDosInImageDescriptionsAreBad().check(1, line))

    def test_the_words_to_and_do_are_ignored_otherwise(self):
        line = 'This has nothing to do with incomplete descriptions.'
        self.assertTrue(ma.ToDosInImageDescriptionsAreBad().check(1, line) is None)

