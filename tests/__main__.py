# mock out warning registry
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import MAGSBS
import unittest, unittest.mock
# Running tests will load the built-in MAGSBS localisation support which is not
# available during test runtime. Hence it's better mocked out. For the few rare
# cases where the warning registry is under test, the mock can be added using a
# patch to the test function.

with unittest.mock.patch('MAGSBS.common.WarningRegistry'):
    import unittest
    sys.argv.append('discover')
    sys.argv.append('tests')
    unittest.TestProgram(module=None)
