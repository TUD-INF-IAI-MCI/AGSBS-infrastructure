#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import os
import unittest
import tempfile
import sys

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
    def test_that_locale_is_available(self):
        if sys.platform == "linux":
            loc_dir = _get_localedir()
            self.assertTrue(loc_dir == '/usr/share/locale' or
                loc_dir == os.path.join(os.path.dirname(
                os.path.abspath(sys.argv[0])), 'share', 'locale')
                or os.path.join(os.path.dirname(os.path.dirname(os.environ['_'])),
                'share', 'locale'))
        elif sys.platform == "win32":
            self.assertEqual(_get_localedir(),  "C:\ProgramData\matuc\locale")
        elif sys.platform == "darwin":
            loc_dir = _get_localedir()
            self.assertTrue(loc_dir == '/usr/share/locale' or
                            loc_dir == os.path.join(os.path.dirname(
                            os.path.abspath(sys.argv[0])), 'share', 'locale'))

    def test_that_locale_not_exists_in_programData(self):
        if sys.platform == "win32":
            programDataPath = os.path.join(os.getenv('ProgramData'),
                                                    "matuc", "locale")
            tempName = os.path.join(os.getenv('ProgramData'), "matuc", "_locale")
            if os.path.exists(programDataPath):
                os.rename(programDataPath, tempName)
            # ToDo add case that magsbs is execute from source code
            self.assertEqual(_get_localedir(), None)
            os.rename(tempName, programDataPath)
