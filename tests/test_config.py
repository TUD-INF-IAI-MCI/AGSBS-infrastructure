#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import unittest

import distutils.version
import os
import shutil
import tempfile
from MAGSBS import config, common, errors
from MAGSBS.config import MetaInfo

conf = lambda conf, version=str(config.VERSION): config.LectureMetaData(conf,
        distutils.version.StrictVersion(version))

def write(c):
    """Change an attibute in LectureMetaData to enforce the write."""
    c[MetaInfo.SemesterOfEdit] = 'fake'
    c.write()


class Testconf(unittest.TestCase):
    def setUp(self):
        self.orig_cwd = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        os.chdir(self.tmpdir)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        shutil.rmtree(self.tmpdir)

    def test_that_version_is_written(self):
        c = conf('foo')
        write(c)
        with open('foo') as f:
            self.assertTrue('version>' + str(config.VERSION) in f.read())

    def test_that_outdated_converter_raises_exception(self):
        c = conf('path', '10.9')
        write(c)
        with self.assertRaises(errors.ConfigurationError):
            conf('path', '0.9').read()

    def test_that_outdated_conf_is_silently_upgraded(self):
        c = conf('path', '0.9')
        write(c)
        conf('path', '20.2').read() # silently upgrades?
        with open('path') as f:
            data = f.read()
            self.assertTrue('version>20.2' in data,
                    "expected version number 20.2, got: " + repr(data))

    def test_that_same_version_just_works_fine(self):
        c = conf('path', '0.9')
        write(c)
        # this does not raise:
        conf('path', '0.9').read()
        # bug fixes are treated as equal version
        conf('path', '0.9.5').read()

    def test_that_newer_bugfix_version_emits_warning(self):
        global __name__
        __name__ = '__test__'
        c = conf('path', '0.9.5')
        write(c)
        conf('path', '0.9').read() # this registers the warning
        warns = common.WarningRegistry().get_warnings()
        self.assertEqual(len(warns), 1)

    def test_unparseable_version_number_raises(self):
        c = conf('path', '6.6.6')
        write(c)
        with open('path') as f: # alter version number
            stuff = f.read()
        with open('path', 'w') as f:
            f.write(stuff.replace('6.6.6', '6.8~beta.9'))
        with self.assertRaises(errors.ConfigurationError) as e:
            conf('path').read()

