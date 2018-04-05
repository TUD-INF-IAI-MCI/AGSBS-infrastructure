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
    name of .md files which references should be extracted and tested. """
    md_file_list = []
    for directory_name, _, file_list in file_tree:
        for file in file_list:
            if file.endswith(".md"):  # only .md files will be inspected
                file_path = os.path.join(directory_name, file)
                md_file_list.append((file_path, file))
    return md_file_list


def extract_links(file_tree):
    """Parses all links, images and footnotes (i.e. all references in the .md
    files). It return the list of instances of Reference class. """
    reference_list = []  # list of references in the examined files
    for file_path, _ in get_list_of_md_files(file_tree):
        # encoding of the file should be already checked
        with open(file_path, encoding="utf-8") as file_data:
            # call the function for finding links
            data = mparser.find_links_in_markdown(file_data.read())
            for reference in data:
                reference.file_path = file_path
                reference_list.append(reference)
    return reference_list


class LinkChecker:
    """This class is checking the extracted references. It allows system to
    check their identifiers as well as the existence of internal files,
    where links are pointing. All errors are saved in the public attribute
    self.errors. Parsed headings are taken from the mistkerl to avoid opening
    same files repeatedly. """
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
        for reference in self.reference_list:
            if reference.type == Reference.Type.IMPLICIT:
                # links should be connected somewhere
                self.find_label_for_link(reference)
            if reference.type == Reference.Type.EXPLICIT:
                # identifier should exist for it
                self.find_link_for_identifier(reference)
            if not reference.is_footnote and reference.type \
                    in {Reference.Type.EXPLICIT, Reference.Type.INLINE}:
                self.check_target_availability(reference)

    def find_label_for_link(self, reference):
        """Identifier of implicit references should be connected to the
        "identifier of the explicit reference with syntax [identifier]: link.
        Otherwise it cannot be paired together. If this is not satisfied,
        an error message is created.
        Note: Identifiers are not case sensitive. """
        ref_id = reference.id.lower()
        for tested_ref in self.reference_list:
            if tested_ref.type == Reference.Type.EXPLICIT \
                    and tested_ref.id.lower() == ref_id and \
                    tested_ref.file_path == reference.file_path:
                return  # it is ok, identifier has been found
        self.errors.append(
            ErrorMessage(_("An explicit reference with identifier \"{0}\" does"
                           " not exist. Please write an explicit reference in"
                           " a form \"[{0}]: link\" to the markdown file.")
                         .format(ref_id), reference.line_number,
                         reference.file_path))

    def find_label_duplicates(self):
        """Identifiers for explicit references should not be duplicated in
        the file, because it can cause confusion (pandoc takes the last one
        as relevant).
        Note: If the references with same identifiers are completely the same
        then they are not reported. """
        # check only explicit references
        list_of_labels = [ref for ref in self.reference_list if
                          ref.type == Reference.Type.EXPLICIT]
        seen = set()  # set of link_texts (labels) that were already checked
        for ref in list_of_labels:
            if ref.id.lower() not in seen:
                ref_id = ref.id.lower()
                seen.add(ref_id)  # add as seen
                for tested_ref in list_of_labels:
                    # refs have to be in same file and have same identifier
                    if tested_ref.file_path == ref.file_path \
                            and tested_ref.id.lower() == ref_id \
                            and ref != tested_ref:  # ignore same dicts
                        self.errors.append(ErrorMessage(
                            _("Identifier \"{}\" for reference is duplicated "
                              "on lines {} and {}.")
                            .format(ref_id, ref.line_number,
                                    tested_ref.line_number),
                            ref.line_number, ref.file_path))

    def find_link_for_identifier(self, reference):
        """Explicit reference should be connected to the implicit reference
        with the same identifier. Otherwise it should not be paired together.
        If this is not satisfied, an error message is created.
        Note: Identifiers are not case sensitive. """
        ref_id = reference.id.lower()
        for tested_ref in self.reference_list:
            if tested_ref.type == Reference.Type.IMPLICIT \
                    and tested_ref.id.lower() == ref_id and \
                    tested_ref.file_path == reference.file_path:
                return  # it is ok, same identifier has been found
        self.errors.append(
            ErrorMessage(_("Implicit reference with the identifier \"{0}\" "
                           "does not exist. Please write a reference in a form"
                           " [{0}] in the markdown file or remove the explicit"
                           " reference [{0}]: {1}.")
                         .format(ref_id, reference.link),
                         reference.line_number, reference.file_path))

    def check_target_availability(self, reference):
        """Checks the links in the explicit (not footnote) or inline
        references. This method executes the checks based on the given
        reference type, its structure and file, where the link points.
        Some tests are triggered only when they are in a lecture structure."""
        parsed_url = urlparse(reference.link)
        # True if it is a file in a file structure; excepted strings removes
        # false positives
        is_file = not parsed_url.netloc and not parsed_url.scheme and \
            not self.starts_with_excepted_string(parsed_url.path)
        inspect_fragment = False  # specify if anchor should be inspected
        if parsed_url.path and is_file:  # if something is in path
            # prepare main paths
            base_dir = os.path.dirname(reference.file_path)
            file_path = os.path.join(base_dir, parsed_url.path)
            # check for existence of the file
            self.target_exists(parsed_url.path, reference, file_path)
            # when the link is within lecture, it should be examined in detail
            if is_within_lecture(file_path):
                if self.is_correct_extension(parsed_url.path, reference):
                    # checking .md existence and anchors only for non-images
                    if not reference.is_image:
                        if self.target_md_file_exists(parsed_url.path,
                                                      reference, file_path):
                            inspect_fragment = True

        if (parsed_url.fragment and inspect_fragment) or \
                (not parsed_url.path and is_file):
            # check fragment only in situation when file exists .md file within
            # project and when path is empty (it is the same file)
            self.target_anchor_exists(parsed_url, reference)

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

    def is_correct_extension(self, path, reference):
        """Checks the correct extension of the file in the given path. It
        should exist and correspond to the allowed ones. Method returns True,
        if the file in the given path has correct extension, False otherwise.
        """
        extensions = IMAGE_EXTENSIONS if reference.is_image \
            else WEB_EXTENSIONS  # choose the correct extension

        if path.rfind(".") < 0:  # no extension
            self.errors.append(ErrorMessage(
                _("Link path \"{}\" has no extension, but it should be {}.")
                .format(path, format_extensions_list(extensions)),
                reference.line_number, reference.file_path))
            return False
        # search fo last comma and extension is what follows it
        elif path[path.rfind(".") + 1:].lower() not in extensions:
            self.errors.append(ErrorMessage(
                _("Link path \"{}\" has .{} extension, but it should be {}.")
                .format(path, path[path.rfind(".") + 1:],
                        format_extensions_list(extensions)),
                reference.line_number, reference.file_path))
            return False
        return True  # everything OK

    def target_exists(self, parsed_path, reference, file_path):
        """Checks whether the target file exists. """
        if not os.path.exists(file_path):
            self.errors.append(
                ErrorMessage(
                    _("The file \"{}\" given by the reference \"{}\" does not"
                      " exist.").format(parsed_path, reference.id),
                    reference.line_number, reference.file_path))

    def target_md_file_exists(self, parsed_path, reference, file_path):
        """Within the lecture structure, hypertext files are generated from
        .md files. Therefore, source .md file existence should be checked. """
        file_path_md = "{}.{}".format(os.path.splitext(file_path)[0], 'md')
        if not os.path.exists(file_path_md):
            error_message = _("The source .md file for hypertext file \"{}\" "
                              "does not exist.".format(parsed_path))
            self.errors.append(ErrorMessage(
                error_message, reference.line_number,
                               reference.file_path))
            return False
        return True

    def target_anchor_exists(self, parsed_url, reference):
        """Detects whether the anchored element within .md file exists. """
        path = self.get_files_full_path(parsed_url.path, reference)
        if path not in self.__cached_headings:  # if not in cache, load them
            self.load_headings(path)
        if path not in self.__cashed_html_ids:  # if not in cache, load them
            self.load_ids(path)

        for heading in self.__cached_headings[path]:  # search in headings
            if heading.get_id() == parsed_url.fragment:
                return  # anchor was found
        for html_id in self.__cashed_html_ids[path]:  # search div and span ids
            if html_id == parsed_url.fragment:
                return  # anchor was found

        if not parsed_url.path:
            self.errors.append(
                ErrorMessage(_("A link is referencing to the anchor \"#{}\" "
                               "which does not exist.").format(
                    parsed_url.fragment, path),
                    reference.line_number, reference.file_path))
        else:
            self.errors.append(
                ErrorMessage(_("A link referencing to anchor \"#{}\" which "
                               "does not exist in the file {}.").format(
                    parsed_url.fragment, parsed_url.path),
                    reference.line_number, reference.file_path))

    @staticmethod
    def get_files_full_path(path, reference):
        """This method returns the full path of the file that should be
        investigated to find the anchor."""
        if not path:
            return reference.file_path

        full_path = os.path.realpath(os.path.join(os.path.dirname(
            reference.file_path), path))
        return "{}.{}".format(os.path.splitext(full_path)[0], 'md')

    def load_headings(self, path):
        """This method loads headings into the __cached_headings attribute
        (dictionary). This dictionary prevents loading same files repeatedly
        if links are pointing to the same files.
        """
        with open(path, encoding="utf-8") as file:
            paragraphs = mparser.file2paragraphs(file.read())
        self.__cached_headings[path] = mparser.extract_headings_from_par(
            paragraphs)

    def load_ids(self, path):
        """This method loads ids of div and span elements into
        self.__cashed_html_ids attribute (dictionary). This dictionary prevents
        loading same files repeatedly if links are pointing to the same files.
        """
        with open(path, encoding="utf-8") as file:
            self.__cashed_html_ids[path] = \
                mparser.get_html_elements_identifiers(file.read())
