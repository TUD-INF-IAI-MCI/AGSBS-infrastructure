# pylint: disable=missing-docstring,invalid-name

import unittest
from urllib.parse import urlparse

from MAGSBS.datastructures import Reference
from MAGSBS.quality_assurance import linkchecker


class TestLinkChecker(unittest.TestCase):
    @staticmethod
    def get_path(reference):
        parsed = urlparse(reference.link)
        return parsed.path

    def test_coupling_references(self):
        reference_1 = Reference(
            Reference.Type.EXPLICIT,
            False,
            link="k01.html",
            identifier="1",
            line_number=1,
        )
        reference_2 = Reference(
            Reference.Type.IMPLICIT, False, identifier="2", line_number=2
        )

        reference_expl_ok = Reference(
            Reference.Type.EXPLICIT, False, identifier="2", link="k01.html"
        )
        reference_expl_nok = Reference(
            Reference.Type.EXPLICIT,
            False,
            identifier="non-existing-link",
            link="k01.html",
            line_number=8,
        )
        reference_impl_ok = Reference(
            Reference.Type.IMPLICIT,
            False,
            identifier="1",
            link="k01.html",
            line_number=10,
        )
        reference_impl_nok = Reference(
            Reference.Type.IMPLICIT, False, identifier="incorrect", line_number=12,
        )

        checker = linkchecker.LinkChecker([reference_2], {})
        checker.find_link_for_identifier(reference_expl_ok)
        self.assertEqual(checker.errors, [])
        checker.find_link_for_identifier(reference_expl_nok)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 8)

        checker = linkchecker.LinkChecker([reference_1], {})
        checker.find_label_for_link(reference_impl_ok)
        self.assertEqual(checker.errors, [])
        checker.find_label_for_link(reference_impl_nok)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 12)

    def test_correct_extension(self):
        correct_ref = Reference(
            Reference.Type.EXPLICIT, False, link="k01.html", line_number=10
        )
        html_instead_img = Reference(
            Reference.Type.EXPLICIT, True, link="k01.html", line_number=1
        )
        jpq_instead_html = Reference(
            Reference.Type.EXPLICIT, False, link="k01.jpg", line_number=2
        )
        md_instead_html = Reference(
            Reference.Type.EXPLICIT, False, link="k01.md", line_number=3
        )

        checker = linkchecker.LinkChecker([], {})
        checker.is_correct_extension(self.get_path(correct_ref), correct_ref)
        self.assertEqual(checker.errors, [])
        checker.is_correct_extension(self.get_path(html_instead_img), html_instead_img)
        checker.is_correct_extension(self.get_path(jpq_instead_html), jpq_instead_html)
        checker.is_correct_extension(self.get_path(md_instead_html), md_instead_html)
        self.assertEqual(len(checker.errors), 3)
        for i in range(len(checker.errors)):
            self.assertEqual(checker.errors[i].lineno, i + 1)

    def test_duplicities(self):
        ref_1 = Reference(
            Reference.Type.EXPLICIT,
            False,
            identifier="link_1",
            link="k01.html",
            line_number=1,
        )
        ref_2 = Reference(
            Reference.Type.EXPLICIT,
            False,
            identifier="link_2",
            link="k01.html",
            line_number=2,
        )

        checker = linkchecker.LinkChecker([ref_1, ref_2], {})
        checker.find_label_duplicates()
        self.assertEqual(checker.errors, [])

        ref_3 = Reference(
            Reference.Type.EXPLICIT,
            False,
            identifier="link_1",
            link="k01.html",
            line_number=1,
        )
        ref_4 = Reference(
            Reference.Type.EXPLICIT,
            False,
            identifier="link_2",
            link="k01.html",
            line_number=2,
        )

        checker = linkchecker.LinkChecker([ref_1, ref_2, ref_3], {})
        checker.find_label_duplicates()
        self.assertEqual(len(checker.errors), 1)
        self.assertTrue(checker.errors[0].lineno, 1)

        checker = linkchecker.LinkChecker([ref_1, ref_2, ref_3, ref_4], {})
        checker.find_label_duplicates()
        self.assertTrue(checker.errors[0].lineno, 1)
        self.assertTrue(checker.errors[1].lineno, 2)

    def test_target_exist(self):
        # add testing of hand-made temp file existence
        ref_1 = Reference(
            Reference.Type.EXPLICIT,
            False,
            identifier="link_1",
            link="nonsense path with space",
            line_number=1,
        )

        checker = linkchecker.LinkChecker([], {})
        checker.target_exists(self.get_path(ref_1), ref_1, "nonsenspath with space")
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 1)

    def test_www_unchecked(self):
        ref_1 = Reference(
            Reference.Type.INLINE,
            False,
            identifier="link_1",
            link="WWW.google.de",
            line_number=1,
        )
        ref_2 = Reference(
            Reference.Type.INLINE,
            False,
            identifier="link_2",
            link="www.google.cz",
            line_number=2,
        )
        for ref in [ref_1, ref_2]:
            ref.file_path = "path"

        checker = linkchecker.LinkChecker([ref_1, ref_2], {})
        checker.run_checks()

        self.assertEqual(checker.errors, [])
