# pylint: disable=missing-docstring,invalid-name

import unittest
from urllib.parse import urlparse

from MAGSBS.quality_assurance import linkchecker


class TestHelpingFunctions(unittest.TestCase):

    def test_print_list(self):
        self.assertRaises(ValueError, linkchecker.format_extensions_list, [])
        self.assertEqual(linkchecker.format_extensions_list(["jpg"]), ".jpg")
        self.assertEqual(linkchecker.format_extensions_list(["jpg", "bmp"]),
                         ".jpg or .bmp")
        self.assertEqual(linkchecker.format_extensions_list(
            ["jpg", "bmp", "svg", "png"]), ".jpg, .bmp, .svg or .png")

    def test_replace_web_extension(self):
        self.assertEqual(linkchecker.replace_web_extension_with_md(""), "")
        self.assertEqual(linkchecker.replace_web_extension_with_md("no_dot"),
                         "no_dot")
        for ext in linkchecker.WEB_EXTENSIONS:
            self.assertEqual(linkchecker.replace_web_extension_with_md(
                "test/k01." + ext), "test/k01.md")
            self.assertEqual(linkchecker.replace_web_extension_with_md(
                "test.more.dots.k01." + ext), "test.more.dots.k01.md")


class TestLinkExtractor(unittest.TestCase):

    def test_create_dct(self):
        extractor = linkchecker.LinkExtractor()
        self.assertEqual(
            extractor.create_dct("file.md", "path", 5, "reference",
                                 (True, "text", "link")),
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 5, "is_image": True, "link_text": "text",
             "link": "link"})
        self.assertEqual(
            extractor.create_dct("file.md", "path", 5, "labeled",
                                 (False, "link", "")),
            {"file": "file.md", "file_path": "path", "link_type": "labeled",
             "line_no": 5, "is_image": False, "link": "link"})

    def test_check_dict_integrity(self):
        correct_link = {
            "file": "f", "file_path": "p", "link_type": "reference",
            "line_no": 1, "is_image": False, "link": "l", "link_text": "text"}
        string_not_dct = "I am a fake dictionary."
        empty_dict = {}
        missing_link = {
            "file": "f", "file_path": "p", "link_type": "reference",
            "line_no": 1, "is_image": False, "link_text": "text"}
        missing_file = {"file_path": "p", "link_type": "labeled",
                        "line_no": 5, "is_image": False, "link": "l"}
        missing_path = {"file": "f", "link_type": "labeled",
                        "line_no": 5, "is_image": False, "link": "l"}
        missing_type = {"file_path": "p", "file": "f",
                        "line_no": 5, "is_image": False, "link": "l"}
        missing_lineno = {"file_path": "p", "file": "f", "link": "l",
                          "link_type": "labeled", "is_image": False}
        incorrect_lineno = {"file": "f", "file_path": "p", "is_image": False,
                            "link_type": "reference", "line_no": "abc",
                            "link": "l"}
        no_link_text_in_ref = {
            "file": "f", "file_path": "p", "link_type":
            "reference", "line_no": 1, "is_image": False, "link": "l"}

        extractor = linkchecker.LinkExtractor()
        self.assertTrue(extractor.check_dict_integrity(correct_link))
        self.assertFalse(extractor.check_dict_integrity(string_not_dct))
        self.assertFalse(extractor.check_dict_integrity(empty_dict))
        self.assertFalse(extractor.check_dict_integrity(missing_link))
        self.assertFalse(extractor.check_dict_integrity(missing_file))
        self.assertFalse(extractor.check_dict_integrity(missing_path))
        self.assertFalse(extractor.check_dict_integrity(missing_type))
        self.assertFalse(extractor.check_dict_integrity(missing_lineno))
        self.assertFalse(extractor.check_dict_integrity(incorrect_lineno))
        self.assertFalse(extractor.check_dict_integrity(no_link_text_in_ref))


class TestLinkChecker(unittest.TestCase):

    @staticmethod
    def get_path(link):
        parsed = urlparse(link.get("link"))
        return parsed.path

    def test_check_correct_email(self):
        correct_link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 1, "is_image": False, "link": "mailto: jones@gmail.com"}
        wrong_link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 5, "is_image": False, "link": "mailto: fail@.@gml.com"}

        checker = linkchecker.LinkChecker([])
        checker.check_correct_email_address(correct_link)
        self.assertEqual(checker.errors, [])
        checker.check_correct_email_address(wrong_link)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 5)

    def test_coupling_references(self):
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

        checker = linkchecker.LinkChecker(test_links)
        checker.find_link_for_reference(correct_ref)
        self.assertEqual(checker.errors, [])
        checker.find_link_for_reference(wrong_ref)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 8)

        checker = linkchecker.LinkChecker(test_links)
        checker.find_reference_for_link(correct_foot)
        self.assertEqual(checker.errors, [])
        checker.find_reference_for_link(wrong_foot)
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 12)

    def test_check_extension(self):
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

        checker = linkchecker.LinkChecker([])
        checker.check_extension(self.get_path(correct_link), correct_link)
        self.assertEqual(checker.errors, [])
        checker.check_extension(self.get_path(img_instead_html),
                                img_instead_html)
        checker.check_extension(self.get_path(html_instead_img),
                                html_instead_img)
        checker.check_extension(self.get_path(incorrect_link),
                                incorrect_link)
        self.assertEqual(len(checker.errors), 3)
        for i in range(len(checker.errors)):
            self.assertEqual(checker.errors[i].lineno, i + 1)

    def test_duplicities(self):
        test_links = [
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 1, "is_image": False, "link": "k01.html",
             "link_text": "my_reference"},
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 2, "is_image": False, "link": "1",
             "link_text": "k01.html"}]

        checker = linkchecker.LinkChecker(test_links)
        checker.find_reference_duplicates()
        self.assertEqual(checker.errors, [])

        test_links.append(
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 3, "is_image": False, "link": "k01.html",
             "link_text": "my_reference"})
        test_links.append(
            {"file": "file.md", "file_path": "path", "link_type": "reference",
             "line_no": 4, "is_image": False, "link": "1",
             "link_text": "k01.html"})

        checker = linkchecker.LinkChecker(test_links)
        checker.find_reference_duplicates()
        self.assertEqual(len(checker.errors), 2)
        self.assertTrue(checker.errors[0].lineno, 1)
        self.assertTrue(checker.errors[1].lineno, 2)

    def test_target_exist(self):
        # add testing of hand-made temp file existence
        link = {
            "file": "file.md", "file_path": "path", "link_type": "reference",
            "line_no": 1, "is_image": False, "link": "nonsenspath with space",
            "link_text": "my_reference"}

        checker = linkchecker.LinkChecker([])
        checker.target_exists(self.get_path(link), link,
                              "nonsenspath with space")
        self.assertEqual(len(checker.errors), 1)
        self.assertEqual(checker.errors[0].lineno, 1)

    def test_www_unchecked(self):
        links = [
            {"file": "file.md", "file_path": "path", "link_type": "inline",
             "line_no": 1, "is_image": False, "link": "WWW.google.de",
             "link_text": "my_reference"},
            {"file": "file.md", "file_path": "path", "link_type": "inline",
             "line_no": 2, "is_image": False, "link": "www.google.cz",
             "link_text": "my_reference"}
        ]

        checker = linkchecker.LinkChecker(links)
        checker.run_checks()

        self.assertEqual(checker.errors, [])
