# pylint: disable=missing-docstring,invalid-name

import unittest
from urllib.parse import urlparse

from MAGSBS.datastructures import Reference

from MAGSBS.quality_assurance import linkchecker


class TestHelpingFunctions(unittest.TestCase):

    def test_print_list(self):
        self.assertRaises(ValueError, linkchecker.format_extensions_list, [])
        self.assertEqual(linkchecker.format_extensions_list(["jpg"]), ".jpg")
        self.assertEqual(linkchecker.format_extensions_list(["jpg", "bmp"]),
                         ".jpg or .bmp")
        self.assertEqual(linkchecker.format_extensions_list(
            ["jpg", "bmp", "svg", "png"]), ".jpg, .bmp, .svg or .png")


class TestLinkExtractor(unittest.TestCase):

    def test_create_dct(self):
        extractor = linkchecker.LinkExtractor([])
        reference = Reference("inline", True)
        self.assertEqual(
            extractor.create_dct("file.md", "path", reference),
            {"file": "file.md", "file_path": "path", "reference": reference})


class TestLinkChecker(unittest.TestCase):

    @staticmethod
    def get_path(link):
        parsed = urlparse(link.get("link"))
        return parsed.path

    def atest_coupling_references(self):
        test_links = [
            {"file": "file.md", "file_path": "path", "line_no": 1,
             "link_type": "reference_footnote", "is_image": False,
             "link": "k01.html", "link_text": "my_reference"},
            {"file": "file.md", "file_path": "path", "link_type": "labeled",
             "line_no": 3, "is_image": False, "link": "1"}]

        correct_ref = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 6, "is_image": False, "link": "k01.html",
            "link_text": "1"}
        wrong_ref = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 8, "is_image": False, "link": "k01.html",
            "link_text": "non-existing link"}
        correct_foot = {
            "file": "file.md", "file_path": "path", "link_type": "labeled",
            "line_no": 10, "is_image": False, "link": "my_reference"}
        wrong_foot = {
            "file": "file.md", "file_path": "path", "link_type": "labeled",
            "line_no": 12, "is_image": False, "link": "incorrect_reference"}

        checker = linkchecker.LinkChecker(test_links, {})
        checker.find_link_for_reference(correct_ref)
        self.assertEqual(checker.errors, [])
        checker.find_link_for_reference(wrong_ref)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 8)

        checker = linkchecker.LinkChecker(test_links, {})
        checker.find_label_for_link(correct_foot)
        self.assertEqual(checker.errors, [])
        checker.find_label_for_link(wrong_foot)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 12)

    def atest_correct_extension(self):
        correct_link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 10, "is_image": False, "link": "k01.html",
            "link_text": "1"}
        img_instead_html = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 1, "is_image": True, "link": "k01.html",
            "link_text": "1"}
        html_instead_img = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 2, "is_image": False, "link": "k01.jpg",
            "link_text": "1"}
        incorrect_link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 3, "is_image": True, "link": "k01.md",
            "link_text": "1"}

        checker = linkchecker.LinkChecker([], {})
        checker.is_correct_extension(self.get_path(correct_link), correct_link)
        self.assertEqual(checker.errors, [])
        checker.is_correct_extension(self.get_path(img_instead_html),
                                img_instead_html)
        checker.is_correct_extension(self.get_path(html_instead_img),
                                html_instead_img)
        checker.is_correct_extension(self.get_path(incorrect_link),
                                incorrect_link)
        self.assertEqual(len(checker.errors), 3)
        for i in range(len(checker.errors)):
            self.assertEqual(checker.errors[i].lineno, i + 1)

    def atest_duplicities(self):
        test_links = [
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 1, "is_image": False, "link": "k01.html",
             "link_text": "my_reference"},
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 2, "is_image": False, "link": "1",
             "link_text": "k01.html"}]

        checker = linkchecker.LinkChecker(test_links, {})
        checker.find_label_duplicates()
        self.assertEqual(checker.errors, [])

        test_links.append(
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 3, "is_image": False, "link": "k01.html",
             "link_text": "my_reference"})
        test_links.append(
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 4, "is_image": False, "link": "1",
             "link_text": "k01.html"})

        checker = linkchecker.LinkChecker(test_links, {})
        checker.find_label_duplicates()
        self.assertEqual(len(checker.errors), 2)
        self.assertTrue(checker.errors[0].lineno, 1)
        self.assertTrue(checker.errors[1].lineno, 2)

    def atest_target_exist(self):
        # add testing of hand-made temp file existence
        link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 1, "is_image": False, "link": "nonsenspath with space",
            "link_text": "my_reference"}

        checker = linkchecker.LinkChecker([], {})
        checker.target_exists(self.get_path(link), link,
                              "nonsenspath with space")
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 1)

    def atest_www_unchecked(self):
        links = [
            {"file": "file.md", "file_path": "path", "link_type": "inline",
             "line_no": 1, "is_image": False, "link": "WWW.google.de",
             "link_text": "my_reference"},
            {"file": "file.md", "file_path": "path", "link_type": "inline",
             "line_no": 2, "is_image": False, "link": "www.google.cz",
             "link_text": "my_reference"}
        ]

        checker = linkchecker.LinkChecker(links, {})
        checker.run_checks()

        self.assertEqual(checker.errors, [])
