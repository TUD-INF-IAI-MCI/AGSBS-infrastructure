#pylint: disable=too-many-public-methods,import-error,too-few-public-methods,missing-docstring,unused-variable,multiple-imports
import os
import random
import shutil
import tempfile
import unittest

import MAGSBS.quality_assurance.markdown as markdown
from MAGSBS import datastructures

def make_headings(**headings):
    """Transform {'path':[(1,2), (3, 4)]) into {'path' : [<heading_object>, ...]}, where
    heading object is a heading, the numbers in the tuple get transformed into
    (h_level, line_number).
    path must be either "kxx" or "bilder", transformation example:
        k01 -> k01/k01.md
        bilder -> k01/bilder.md.
    Directories and files are created. If the first item of the supplied list is
    a string, the file (as given by path) is created and populated with that
    content."""
    proper_headings = {}
    for path, headings in headings.items():
        if path.startswith('k'):
            path = '{}/{}.md'.format(path, path[:3])
        else:
            path = 'k01/%s.md' % path
        if isinstance(headings[0], str):
            if not os.path.exists(os.path.split(path)[0]):
                os.mkdir(os.path.split(path)[0])
            with open(path, 'w', encoding='utf-8') as f:
                f.write(headings.pop(0))
        proper_headings[path] = []
        for level, lnum in headings:
            text = 'h%s%s' % (level, random.randint(1,999999999))
            h = datastructures.Heading(text, level)
            h.set_line_number(lnum)
            proper_headings[path].append(h)
    return proper_headings

def check(headings):
    return markdown.DetectEmptyImageDescriptions().worker(headings)


class TestDetectEmptyImageDescriptions(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_that_empty_chapters_are_ignored(self):
        h = make_headings(k01 = ['jojo\n=======\n\n## 99', (1,1), (4,1)])
        self.assertFalse(check(h))

    def test_that_images_with_description_are_ignored(self):
        h = make_headings(bilder = ['# ok\n##ok II\n\ndesc\n\n## ok III\n\ndesc\n',
            (1,1), (2,2), (2,6)])
        heading = check(h)
        self.assertFalse(heading, ("expected that all descriptions got assigned "
            "to headings, so no headings would be reported, but got heading from "
            "line ") + str(heading.get_lnum() if heading else None))

    def test_that_missing_descriptions_at_end_of_file_detected(self):
        h = make_headings(bilder = ['# ok\n##ok II\n\ndesc\n\n## ok III\n\n',
            (1,1), (2,2), (2,6)])
        self.assertTrue(check(h))

    def test_that_missing_descriptions_detected_in_middle_of_file(self):
        h = make_headings(bilder = ['# ok\n##ok II\n\ndesc\n\n## blub\n\n## ok III\n\ndesc',
            (1,1), (2,2), (2,6), (2, 8)])
        self.assertTrue(check(h))

    def test_that_empty_description_detected_even_if_multiple_headings_within_paragraph(self):
        h = make_headings(bilder = ['# yup\n\n## abc\n## def\n', (1,1), (2,3),
            (2,4)])
        self.assertTrue(check(h))

    def test_that_underline_of_headings_ignored(self):
        h = make_headings(bilder = ['yup\n====\n\n## abc\n\nup\n\n## def\n\nkk\n',
            (1,2), (2,4), (2,8)])
        err = check(h)
        self.assertFalse(err, ("expected no image description to be detected as empty"
            ", but found one at line %s") % (err.get_lnum() if err else repr(err)))
        h = make_headings(bilder = ['# yup\n\nabc\n--------\n\nup\n\ndef\n-------\n\n',
            (1,2), (2,3), (2,8)])
        self.assertTrue(check(h))

    def test_that_empty_image_descriptions_file_is_file_as_well(self):
        h = make_headings(bilder = ['bla bla\nblub blub\ntricked tricked\n'])
        self.assertFalse(check(h))

