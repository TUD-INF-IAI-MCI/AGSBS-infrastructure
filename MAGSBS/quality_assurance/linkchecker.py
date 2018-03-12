# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2018 Sebastian Humenda <shumenda |at|gmx |dot| de>
#   Jaromir Plhak <xplhak |at| gmail |dot| com>

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
import re
from urllib.parse import urlparse

from .. import mparser
from .meta import ErrorMessage
from ..common import is_within_lecture

WEB_EXTENSIONS = ["html"]
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "svg"]


def print_list(input_list):
    """ This function creates a string from the list elements that can be used
    for outputs when error occurs. Last element is treated in a special way,
    therefore simple join cannot be used. It is used specifically for
    ErrorMessage generation. """
    if not input_list:  # list should have at least one element
        raise ValueError("At least one extension should be defined for web "
                         "links and also for images.")

    output = "." + str(input_list[0])
    if len(input_list) == 1:  # return immediately single element
        return output
    for i in range(1, len(input_list) - 1):
        output += ", ." + str(input_list[i])
    return output + " or ." + input_list[len(input_list) - 1]


def get_list_of_md_files(file_tree):
    """ This method creates a list of tuples that contain paths and file
    name of .md files which links should be tested. """
    md_file_list = []
    for directory_name, _, file_list in file_tree:
        for file in file_list:
            if file.endswith(".md"):  # only .md files will be inspected
                file_path = os.path.join(directory_name, file)
                if os.path.isfile(file_path):  # check if file exists
                    md_file_list.append((file_path, file))
    return md_file_list


def replace_web_extension_with_md(path):
    """ Replace the hypertext file extension with .md extension. It takes the
    last dot in the string and if it is there, then it compares all possible
    extensions. It some of them is the same, then it is replaced by 'md' """
    for extension in WEB_EXTENSIONS:
        last_dot = path.rfind(".")
        if len(path) - last_dot - 1 == len(extension) and \
                path[last_dot + 1:] == extension:
            return path[:last_dot] + ".md"
    return path  # if no extension passed the condition


class LinkExtractor:
    """ The purpose of this class is to extract all links that have to
    be checked.
    Note: This class assumes that markdown links are correctly structured
        according to the rules specified by pandoc manual, available at
        https://pandoc.org/MANUAL.html#links """
    def __init__(self):
        self.links_list = []  # dicts of links generated in the examined files

    def parse_all_links_in_md_files(self, file_tree):
        """ Parses all links in the .md files. Each link is stored in the
        dictionary that has the following structure:
        "file": name of the file, where the link is stored
        "file_path": full path to the file, where the link is stored
        "link_type": type of the link - this should be as follows:
            "inline": basic inline link in square brackets, syntax;
            "footnote": link to the footnote that is referenced somewhere else
                in the document;
            "reference": reference to the footnote and standalone links.
                References' titles are not detected as they are not
                relevant to the link testing;
        "line_no": number of line on which link is matched;
        "is_image": 'True' if the link is a picture, 'False' otherwise
        "link": link;
        "link_text": link description, if exists.
        All dictionaries are added to the link_list attribute. """
        for file_path, file_name in get_list_of_md_files(file_tree):
            # encoding of the file should be already checked
            with open(file_path, encoding="utf-8") as file_data:
                # call the function for finding links
                data = mparser.find_links_in_markdown(file_data.read())
                for link_dict in data:
                    new_dct = self.create_dct(
                        file_name, file_path, link_dict[0], link_dict[1],
                        link_dict[2])
                    # dct can be None in specific case described in the
                    # create_dct function
                    if new_dct:
                        self.links_list.append(new_dct)


    @staticmethod
    def create_dct(file_name, file_path, line_no, link_type, link):
        """ This method generates the dictionary that contains all the
        important data for the link examination. """
        if not isinstance(link, tuple):
            raise TypeError(
                "The processed link shoud be a tuple, but {} was "
                "returned.".format(type(link)))

        link_dict = dict()
        link_dict["file"] = file_name
        link_dict["file_path"] = file_path
        link_dict["link_type"] = link_type
        link_dict["line_no"] = line_no
        link_dict["is_image"] = True if link[0] == "!" else False

        if not link[2]:  # standalone - type "text [link] text text"
            link_dict["link"] = link[1]
        else:  # other footnote links, references and inline links"
            link_dict["link_text"] = link[0]
            link_dict["link"] = link[1]
        return link_dict


class LinkChecker:
    """ This class is checking the extracted links. It allows system to check
    their structure as well as the internal files, where links are pointing.
    All errors are saved in the public attribute self.errors. """
    def __init__(self, links_list):
        self.errors = []  # generated errors
        self.links_list = links_list
        # following attributes are used for loading data from files, therefore
        # it is not necessary to load and parse them repeatedly
        self.__headings_dict = {}  # dictionary with headings
        self.__html_ids_dict = {}  # dictionary with div and span ids

    def run_checks(self):
        """ This methods runs all available checks within this class. """
        for link in self.links_list:
            self.check_correct_email_address(link)
            if link.get("link_type") in {"footnote"}:
                # links should be connected somewhere
                self.find_reference_for_link(link)
            if link.get("link_type") == "reference":
                # reference should be called
                self.find_link_for_reference(link)
            if link.get("link_type") in {"reference", "inline"}:
                self.check_target_availability(link)

    @staticmethod
    def is_email_address(link):
        """ Detecting, if the link is email address. Method checks, if the
        'mailto' is the starting substring of the link. """
        return link.find("mailto:") == 0

    def check_correct_email_address(self, link):
        """ When 'mailto:' is used, the standard structure of the email address
        should be followed. Otherwise, an error message is created. """
        if self.is_email_address(link.get("link")):
            pattern = re.compile(r"[^@]+@[^@]+\.[^@]+")
            if not bool(re.match(pattern, link.get("link")[7:])):
                self.errors.append(ErrorMessage(
                    "Email address {} is not in a correct form.".format(
                        link.get("link")[7:]),
                    link.get("line_no"), link.get("file_path")))

    def find_reference_for_link(self, link):
        """ FOOTNOTE and STANDALONE links should be connected to the
        reference link with []: syntax. Otherwise it should not be paired
        together. If this is not satisfied, an error message is created.
        Note: Links are not case sensitive. """
        link_ref = link.get("link").lower()
        for tested_link in self.links_list:
            if tested_link.get("link_type") == {"reference"} \
                    and tested_link.get("link_text").lower() == link_ref:
                return  # it is ok, reference has been found
        self.errors.append(ErrorMessage("Problem with coupling a reference to "
                                        "the link [{}].".format(link_ref),
                                        link.get("line_no"),
                                        link.get("file_path")))

    def find_link_for_reference(self, link):
        """ REFERENCE links should be connected to the FOOTNOTE or STANDALONE
        link with []: syntax. Otherwise it should not be paired together.
        If this is not satisfied, an error message is created.
        Note: Links are not case sensitive. """
        link_txt = link.get("link_text").lower()
        for tested_link in self.links_list:
            if tested_link.get("link_type") in {"footnote", "standalone"} \
                    and tested_link.get("link").lower() == link_txt:
                return  # it is ok, link has been found
        self.errors.append(ErrorMessage("Problem with coupling a link to "
                                        "the reference [{}].".format(link_txt),
                                        link.get("line_no"),
                                        link.get("file_path")))

    def check_target_availability(self, link):
        """ Do the checks according to the path given in the link. This method
         executes the checks based on the given link type, its structure and
         place, where it leads. """
        parsed_url = urlparse(link.get("link"))
        inspect_fragment = False  # specify if anchor should be inspected
        if parsed_url.path:  # if something is in path
            # prepare main paths
            base_dir = os.path.dirname(link.get("file_path"))
            file_path = os.path.join(base_dir, parsed_url.path)
            # check for existence of the file
            self.target_exists(parsed_url.path, link, file_path)
            # when the link is within lecture, it should be examined in detail
            if is_within_lecture(file_path):
                if self.check_extension(parsed_url.path, link):
                    # checking .md existence and anchors only for non-images
                    if not link.get("is_image"):
                        if self.target_md_file_exists(parsed_url.path, link,
                                                      file_path):
                            inspect_fragment = True
        if (parsed_url.fragment and inspect_fragment) or not parsed_url.path:
            # check fragment only in situation when file is .md file within
            # project and when path is empty (it is the same file)
            self.target_anchor_exists(parsed_url, link)

    def check_extension(self, path, link):
        """ Checks the correct extension of the file in the given path. It
        should exist and correspond to the allowed ones. Method returns True,
        if the file in the given path has correct extension, False otherwise.
        """
        extensions = IMAGE_EXTENSIONS if link.get("is_image") \
            else WEB_EXTENSIONS  # choose the correct extension

        if path.rfind(".") < 0:  # no extension
            self.errors.append(ErrorMessage(
                "Link path {} has no extension, but it should be {}.".format(
                    path, print_list(extensions)), link.get("line_no"),
                link.get("file_path")))
            return False
        # search fo last comma and extension is what follows it
        elif path[path.rfind(".") + 1:] not in extensions:
            self.errors.append(ErrorMessage(
                "Link path {} has .{} extension, but it should be {}."
                .format(path, path[path.rfind(".") + 1:],
                        print_list(extensions)), link.get("line_no"),
                link.get("file_path")))
            return False
        return True  # everything OK

    def target_exists(self, parsed_path, link, file_path):
        """ Checks, if the target file exists. """
        if not os.path.exists(file_path):
            self.errors.append(
                ErrorMessage(
                    "The file \"{}\" given by the reference [{}] doesn't "
                    "exist.".format(parsed_path, link.get("link_text")),
                    link.get("line_no"), link.get("file_path")))

    def target_md_file_exists(self, parsed_path, link, file_path):
        """ Within the lecture structure, hypertext files are generated from
        .md files. Therefore, source .md file existence should be checked. """
        file_path_md = replace_web_extension_with_md(file_path)
        if not os.path.exists(file_path_md):
            error_message = ("The source .md file for hypertext file {} "
                             "does not exist.".format(parsed_path))
            self.errors.append(ErrorMessage(
                error_message, link.get("line_no"), link.get("file_path")))
            return False
        return True

    def target_anchor_exists(self, parsed_url, link):
        """ Detects if the anchored element within .md file exists. """
        # open file, its existence should be already checked
        path = self.get_files_full_path(parsed_url.path, link)
        if path not in self.__headings_dict:
            self.load_headings_to_dict(path)
            self.load_html_ids_to_dict(path)

        for heading in self.__headings_dict[path]:  # search in headings
            if heading.get_id() == parsed_url.fragment:
                return  # anchor was found
        for html_id in self.__html_ids_dict[path]:  # search div and span ids
            if html_id == parsed_url.fragment:
                return  # anchor was found

        self.errors.append(
            ErrorMessage("The anchor {} was not found in the {} file.".format(
                parsed_url.fragment, path), link.get("line_no"),
                link.get("file_path")))

    @staticmethod
    def get_files_full_path(path, link):
        """ This method returns the full path of the file that should be
        investigated for the anchor."""
        if not path:
            return link.get("file_path")

        full_path = os.path.realpath(os.path.join(os.path.dirname(
            link.get("file_path")), path))
        return replace_web_extension_with_md(full_path)

    def load_headings_to_dict(self, path):
        """ This method loads headings into dictionary. This dictionary
        prevents loading same files repeatedly. """
        with open(path, encoding="utf-8") as file:
            paragraphs = mparser.file2paragraphs(file.read())
        self.__headings_dict[path] = mparser.extract_headings(path, paragraphs)

    def load_html_ids_to_dict(self, path):
        """ This method loads headings into dictionary. This dictionary
        prevents loading same files repeatedly. """
        with open(path, encoding="utf-8") as file:
            self.__html_ids_dict[path] = mparser.get_ids_of_html_elements(
                file.read())


# ############ MARKDOWN ############ #


class TitleInLinkCannotContainFormatting():
    """ When using INLINE_LINK_WITH_TITLE, it is not allowed to have
    formatting information within link title. """
    pass


class TitleIsTooLong():
    """ Title should be 'reasonably' long. Long text lowers the readability
    and they also can be caused by a incorrect syntax of link. """
    pass


class TitleInInlineLinkIsCorrect():
    # check if it is correctly build using " or ' (the last
    # char should be the there at least twice - and first one
    # is the end of the link
    pass


class NoSpaceBetweenRoundAndSquareBrackets():
    """ When the inline link or footnote link is used, it is not allowed by
    pandoc to have a space/spaces between square and round brackets."""
    pass


class IncorrectImageFormattingUsingAngleBrackets():
    """It is not allowed to enter image using angle brackets."""
    pass
