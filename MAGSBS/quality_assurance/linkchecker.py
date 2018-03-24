# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2018 Sebastian Humenda <shumenda |at|gmx |dot| de>
#   Jaromir Plhak <xplhak |at| gmail |dot| com>

# pylint: disable=too-few-public-methods

"""
Link checker for MarkDown documents.

When linking to another file, the link has to use the target format extension
(i.e. .html) and hence that has to be considered when looking for broken links.
This link checker is hence tailored to MarkDown.

This link checker also checks for broken image references.

This link checker does not touch the file system. It requires a list of files
(as produced by os.walk()) and all links and images provided by LinkExtractor.
"""

import os
import collections
from urllib.parse import urlparse

from .. import mparser
from .meta import ErrorMessage
from ..common import is_within_lecture
from ..datastructures import Reference


WEB_EXTENSIONS = ["html"]
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "svg"]
EXCEPTED_STRING_STARTS = ["www."]


def format_extensions_list(extensions):
    """Format a list of extensions in a human-readable way."""
    if not extensions:  # list should have at least one element
        raise ValueError("No extension defined for link, yet required")

    if len(extensions) == 1:
        return ".{}".format(extensions[0])
    return _(".{} or .{}").format(', .'.join(extensions[:-1]), extensions[-1])


def get_list_of_md_files(file_tree):
    """This method creates a list of tuples that contain paths and file
    name of .md files which links should be tested. """
    md_file_list = []
    for directory_name, _, file_list in file_tree:
        for file in file_list:
            if file.endswith(".md"):  # only .md files will be inspected
                file_path = os.path.join(directory_name, file)
                md_file_list.append((file_path, file))
    return md_file_list


def extract_links(file_tree):
    """Parses all links, images and footnotes (i.e. all references in the .md
    files. It return the list of References. """
    reference_list = []  # list of references in the examined files
    for file_path, file_name in get_list_of_md_files(file_tree):
        # encoding of the file should be already checked
        with open(file_path, encoding="utf-8") as file_data:
            # call the function for finding links
            data = mparser.find_links_in_markdown(file_data.read())
            for reference in data:
                reference.set_file_name(file_name)
                reference.set_file_path(file_path)
                reference_list.append(reference)
    return reference_list


class LinkChecker:
    """This class is checking the extracted references. It allows system to
    check their structure as well as the internal files, where links are
    pointing. All errors are saved in the public attribute self.errors.
    Parsed headings are taken from the mistkerl to avoid opening same files
    repeatedly. """
    def __init__(self, reference_list, headings):
        self.errors = []  # generated errors
        self.reference_list = reference_list
        # following attributes are used for loading data from files, therefore
        # it is not necessary to load and parse them repeatedly
        # dictionary with headings
        self.__cached_headings = headings
        # dictionary with div and span ids
        self.__cashed_html_ids = collections.OrderedDict()

    def run_checks(self):
        """This methods runs all available checks within this class. """
        self.find_label_duplicates()  # check duplicate labels
        for reference_dict in self.reference_list:
            reference = reference_dict.get("reference")
            if reference.get_type() == "labeled":
                # links should be connected somewhere
                self.find_label_for_link(reference_dict)
            if reference.get_type() == {"reference"}:
                # reference should be called
                self.find_link_for_reference(reference_dict)
            if reference.get_type() in {"reference", "inline"}:
                self.check_target_availability(reference_dict)

    def find_label_for_link(self, reference_dct):
        """Labels (shortcut reference link) should be connected to the
        "reference(_footnote)" label with []: syntax. Otherwise it cannot be
        paired together. If this is not satisfied, an error message is created.
        Note: Links are not case sensitive. """
        reference_id = reference_dct.get("reference").get_link().lower()
        for tested_reference_dct in self.reference_list:
            tested_reference = tested_reference_dct.get("reference")
            if tested_reference.get_type() == "reference" \
                    and tested_reference.get_id().lower() == reference_id:
                return  # it is ok, reference has been found
        self.errors.append(
            ErrorMessage(_("A link with label \"{0}\" does not exist. "
                           "Please write a link in a form [{0}]: link to "
                           "the markdown file.").format(reference_id),
                         reference_dct.get("line_no"),
                         reference_dct.get("file_path")))

    def find_label_duplicates(self):
        """Labels for reference links should not be duplicated in the file,
        because it can cause confusion (pandoc takes the last one as relevant).
        Note: If the links with same label are completely the same then they
        are not reported. """
        # check only references
        list_of_labels = [link for link in self.reference_list if
                          link.get("link_type") == "reference"]
        seen = set()  # set of link_texts (labels) that were already checked
        for link in list_of_labels:
            if link.get("link_text").lower() not in seen:
                link_txt = link.get("link_text").lower()
                seen.add(link_txt)  # add as seen
                for tested_link in list_of_labels:
                    if tested_link.get("link_text").lower() == link_txt \
                            and link != tested_link:  # ignore same dicts
                        self.errors.append(ErrorMessage(
                            _("Reference \"{}\" is duplicated on lines {} "
                              "and {}.").format(link.get("link_text"),
                                                link.get("line_no"),
                                                tested_link.get("line_no")),
                            link.get("line_no"),
                            link.get("file_path")))

    def find_link_for_reference(self, link):
        """Reference(_footnote) links should be connected to the labeled link.
        Otherwise it should not be paired together. If this is not satisfied,
        an error message is created.
        Note: Links are not case sensitive. """
        link_txt = link.get("link_text").lower()
        for tested_link in self.reference_list:
            if tested_link.get("link_type") == "labeled" \
                    and tested_link.get("link").lower() == link_txt:
                return  # it is ok, link has been found
        self.errors.append(
            ErrorMessage(_("A link for the reference \"{}\" does not exist. "
                           "Please write a link in a form [{}] link to the "
                           "markdown file or remove the reference.")
                         .format(link_txt, link_txt), link.get("line_no"),
                         link.get("file_path")))

    def check_target_availability(self, link):
        """Makes the checks according to the path given in the link.
        This method executes the checks based on the given link type,
        its structure and place, where it leads. It takes only files to be
        tested. Moreover, some tests are triggered only when they are in a
        lecture structure. """
        parsed_url = urlparse(link.get("link"))
        # True if it is a file in a file structure; excepted strings removes
        # false positives
        is_file = not parsed_url.netloc and not parsed_url.scheme and \
            not self.starts_with_excepted_string(parsed_url.path)
        inspect_fragment = False  # specify if anchor should be inspected
        if parsed_url.path and is_file:  # if something is in path
            # prepare main paths
            base_dir = os.path.dirname(link.get("file_path"))
            file_path = os.path.join(base_dir, parsed_url.path)
            # check for existence of the file
            self.target_exists(parsed_url.path, link, file_path)
            # when the link is within lecture, it should be examined in detail
            if is_within_lecture(file_path):
                if self.is_correct_extension(parsed_url.path, link):
                    # checking .md existence and anchors only for non-images
                    if not link.get("is_image"):
                        if self.target_md_file_exists(parsed_url.path, link,
                                                      file_path):
                            inspect_fragment = True

        if (parsed_url.fragment and inspect_fragment) or \
                (not parsed_url.path and is_file):
            # check fragment only in situation when file exists .md file within
            # project and when path is empty (it is the same file)
            self.target_anchor_exists(parsed_url, link)

    @staticmethod
    def starts_with_excepted_string(string):
        """This method detect whether the string is not false positively
        detected as a path by urlparse. This could happen, e.g. when somebody
        forgets to write http:// and write www.google.de. String that should be
        ignored are saved in the EXCEPTED_STRING_STARTS as regex patterns."""
        for start in EXCEPTED_STRING_STARTS:
            if string.lower().startswith(start):
                return True
        return False

    def is_correct_extension(self, path, link):
        """Checks the correct extension of the file in the given path. It
        should exist and correspond to the allowed ones. Method returns True,
        if the file in the given path has correct extension, False otherwise.
        """
        extensions = IMAGE_EXTENSIONS if link.get("is_image") \
            else WEB_EXTENSIONS  # choose the correct extension

        if path.rfind(".") < 0:  # no extension
            self.errors.append(ErrorMessage(
                _("Link path \"{}\" has no extension, but it should be {}.")
                .format(path, format_extensions_list(extensions)),
                link.get("line_no"), link.get("file_path")))
            return False
        # search fo last comma and extension is what follows it
        elif path[path.rfind(".") + 1:].lower() not in extensions:
            self.errors.append(ErrorMessage(
                _("Link path \"{}\" has .{} extension, but it should be {}.")
                .format(path, path[path.rfind(".") + 1:],
                        format_extensions_list(extensions)),
                link.get("line_no"), link.get("file_path")))
            return False
        return True  # everything OK

    def target_exists(self, parsed_path, link, file_path):
        """Checks whether the target file exists. """
        if not os.path.exists(file_path):
            self.errors.append(
                ErrorMessage(
                    _("The file \"{}\" given by the reference \"{}\" does not "
                      "exist.").format(parsed_path, link.get("link_text")),
                    link.get("line_no"), link.get("file_path")))

    def target_md_file_exists(self, parsed_path, link, file_path):
        """Within the lecture structure, hypertext files are generated from
        .md files. Therefore, source .md file existence should be checked. """
        file_path_md = "{}.{}".format(os.path.splitext(file_path)[0], 'md')
        if not os.path.exists(file_path_md):
            error_message = _("The source .md file for hypertext file \"{}\" "
                              "does not exist.".format(parsed_path))
            self.errors.append(ErrorMessage(
                error_message, link.get("line_no"), link.get("file_path")))
            return False
        return True

    def target_anchor_exists(self, parsed_url, link):
        """Detects if the anchored element within .md file exists. """
        # open file, its existence should be already checked
        path = self.get_files_full_path(parsed_url.path, link)
        if path not in self.__cached_headings:
            self.load_headings(path)
            self.load_ids(path)

        for heading in self.__cached_headings[path]:  # search in headings
            if heading.get_id() == parsed_url.fragment:
                return  # anchor was found
        for html_id in self.__cashed_html_ids[path]:  # search div and span ids
            if html_id == parsed_url.fragment:
                return  # anchor was found

        self.errors.append(
            ErrorMessage(_("The anchor \"{}\" was not found in the \"{}\" "
                         "file.").format(parsed_url.fragment, path),
                         link.get("line_no"), link.get("file_path")))

    @staticmethod
    def get_files_full_path(path, link):
        """This method returns the full path of the file that should be
        investigated for the anchor."""
        if not path:
            return link.get("file_path")

        full_path = os.path.realpath(os.path.join(os.path.dirname(
            link.get("file_path")), path))
        return "{}.{}".format(os.path.splitext(full_path)[0], 'md')

    def load_headings(self, path):
        """This method loads headings into the __cached_headings attribute
        (dictionary). This dictionary prevents loading same files repeatedly
        if links are pointing on the same files.
        """
        with open(path, encoding="utf-8") as file:
            paragraphs = mparser.file2paragraphs(file.read())
        self.__cached_headings[path] = mparser.extract_headings_from_par(
            paragraphs)

    def load_ids(self, path):
        """This method loads ids of div and span elements into
        self.__cashed_html_ids attribute (dictionary). This dictionary prevents
        loading same files repeatedly if links are pointing on the same files.
        """
        with open(path, encoding="utf-8") as file:
            self.__cashed_html_ids[path] = \
                mparser.get_html_elements_ids_from_document(file.read())
