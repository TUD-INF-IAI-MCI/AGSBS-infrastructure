#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import os
import unittest
import tempfile

from MAGSBS.config import _get_localedir

def touch(path):
    """Create the path recursively. If the argument string does not end on a
    slash, it is taken as file name and created as an empty file below the
    prefix."""
    if path.endswith('/'):
        os.makedirs(path, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w') as f:
            f.write("\n")

class test_locale(unittest.TestCase):
    def test_that_locale_is_in_programData(self):
        self.assertEqual(_get_localedir(), 'C:\ProgramData\matuc\locale')

    def test_that_locale_not_exists_in_programData(self):
        programDataPath = os.path.join(os.getenv('ProgramData'), "matuc", "locale")
        tempName = os.path.join(os.getenv('ProgramData'), "matuc", "_locale")
        if os.path.exists(programDataPath):
            os.rename(programDataPath, tempName)
        self.assertEqual(_get_localedir(), None)
        os.rename(tempName, programDataPath)
