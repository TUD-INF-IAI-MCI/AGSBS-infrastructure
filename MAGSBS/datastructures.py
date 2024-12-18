# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""Common datastructures."""

import enum
import os
import sys
import re

from . import common
from . import errors
from . import roman

CHAPTERNUM = re.compile(r"^[a-z|A-Z]+(\d\d).*\.md")
HEADING_ATTRIBUTES = re.compile("^(#\w+\s*|\.\w+\s*|\w+=\w+\s*)+$")


def gen_id(text, attributes=None):
    """gen_id(text) -> label
This function tries to generate the same labels as pandoc for anchors.
If id is presented within list of attributes (in a form "#id"), than it is
used for generation and the text itself is ignored."""
    if attributes:  # generation of id if it is in the list of attributes
        for attr in attributes:
            if attr.startswith("#"):
                return attr[1:]

    allowed_characters = [".", "-", "_"]
    text = text.lower()
    res_id = []  # does not contain double dash
    last_processed_char = ""
    for char in text:
        # insert hyphen if it is space AND last char was not a space
        if char.isspace() and not last_processed_char.isspace():
            res_id.append("-")
        elif char.isalpha() or char.isdigit() or char in allowed_characters:
            res_id.append(char)
        else:
            continue
        # the else case explicitely does not count as processed char (all those
        # which are going to be ignored)
        last_processed_char = char
    # strip hyphens at the beginning, as well as numbers
    while res_id and not res_id[0].isalpha():
        res_id.pop(0)
    return "".join(res_id)


def get_encoding():
    """Return encoding for stdin/stdout."""
    encoding = sys.getdefaultencoding()  # fallback
    if hasattr(sys.stdout, encoding) and sys.stdout.encoding:
        encoding = sys.stdout.encoding
    return encoding


def decode(in_bytes):
    """Safe version to decode data from subprocesses."""
    if not isinstance(in_bytes, bytes):
        return in_bytes
    else:
        encodings = [get_encoding()]
        # add some more:
        import locale

        if not locale.getdefaultlocale()[1] in encodings:
            encodings.insert(0, locale.getdefaultlocale()[1])
        output = None
        while encodings and not output:
            encoding = encodings.pop()
            try:
                output = in_bytes.decode(encoding)
            except UnicodeDecodeError:
                pass
        if not output:
            output = in_bytes.decode("utf-8", errors="ignore")
        return output


def is_attributes(text):
    """This function takes the text and determines, whether it represents
    the attributes given by the PHP Markdown Extra syntax, available at
    https://michelf.ca/projects/php-markdown/extra/#spe-attr. This syntax
    is used by pandoc, see https://pandoc.org/MANUAL.html#header-identifiers.
    Note: Shortcut {-} allowed by pandoc is also considered as correct
    representation of attribute. """
    if text == "-":
        return True  # shortcut for unnumbered given by pandoc
    return re.match(HEADING_ATTRIBUTES, text)


def extract_label_and_attributes(text):
    """This function extracts the final heading label and heading attributes
    of the heading text. The extraction works in the same way as pandoc's:
    - only the last opening curly bracket is taken into account;
    - the detected curly bracket should not be escaped by backslash;
    - no text after closing curly bracket (or there is no closing curly bracket
        at all);
    - the syntax is compatible with PHP Markdown Extra:
        - https://michelf.ca/projects/php-markdown/extra/#spe-attr
        - e.g. {#identifier .class .class key=value key=value}.
    It returns the tuple. First part represents a label for heading (i.e.
    original text without extracting part that contains attributes). Second
    part of the tuple is a list of attributes (whitespaces are used as a
    separator)."""
    attributes = []  # parsed attributes
    label = text.strip()  # remove redundant whitespaces
    start_index = label.rfind("{")  # find last opening curly bracket
    # returns same string in case, that text do not contain curly brackets or
    # if the last curly bracket is escaped by a backslash
    if start_index < 1:
        # The curly bracket is not found, is the first non-whitespace char
        return label, attributes

    # count number of preceding backslashes
    backslash_counter = 0
    backslash_index = start_index - 1
    while backslash_index >= 0 and label[backslash_index] == "\\":
        backslash_counter += 1
        backslash_index -= 1
    if backslash_counter % 2 == 1:  # odd number means escape bracket
        return label, attributes

    end_index = label.find("}", start_index + 1)
    if (
        end_index == -1
        or end_index != len(label) - 1
        or not is_attributes(label[start_index + 1 : end_index])
    ):
        return label, attributes

    attributes = label[start_index + 1 : end_index].split()
    return (label[:start_index] + label[end_index + 1 :]).rstrip(), attributes


def detect_is_numbered(attributes):
    """Returns True when attributes do not contain either "-" or ".unnumbered.
    False otherwise. """
    return "-" not in attributes and ".unnumbered" not in attributes


class Heading:
    """heading(text, level)

This class represents a heading to ease the handling of headings.
For specifying the type of a heading, Heading.Type is used, which is an enum.
Given text is parsed in the constructor - it is divided to the label of
the heading and attributes. E.g. "Heading {#id .class key=value}" is parsed to
label "Heading" and attributes "{#id .class key=value}".
"""

    class Type(enum.Enum):
        NORMAL = 0  # most headings are of that type
        APPENDIX = 1
        PREFACE = 2

    def __init__(self, text, level):
        self.__line_number = None
        # removes attributes from the text
        self.__text, attributes = extract_label_and_attributes(text)
        # detect if heading is numbered
        self.__is_numbered = detect_is_numbered(attributes)
        # id is generated from the parsed text
        self.__id = gen_id(self.__text, attributes)
        self.__level = level
        self.__chapter_number = None
        self.__type = Heading.Type.NORMAL
        self.__chapter_number = None

    def is_numbered(self):
        return self.__is_numbered

    def get_chapter_number(self):
        return self.__chapter_number

    def set_chapter_number(self, num):
        if not isinstance(num, int):
            raise TypeError("Integer expected.")
        self.__chapter_number = num

    def get_level(self):
        return self.__level

    def get_type(self):
        """Return of which Heading.Type this heading is."""
        return self.__type

    def set_type(self, a_type):
        if not isinstance(a_type, Heading.Type):
            raise ValueError("Wrong heading type. Must be of type Heading.Type.")
        else:
            self.__type = a_type

    def get_id(self):
        """Return the id as generated by Pandoc (also called label in other
                contextes) which serves as an anchor to this link."""
        return self.__id

    def set_text(self, text):
        if not text:
            raise ValueError("Heading must have text.")
        self.__text = text

    def get_text(self):
        return self.__text

    def set_line_number(self, lnum):
        """Set the line number, e.g. if heading was taken from a file."""
        self.__line_number = lnum

    def get_line_number(self):
        return self.__line_number


def extract_chapter_number(path):
    """extract_chapter_number(path) -> return chapter number
    Examples:
    >>> extract_chapter_number('c:\\k01\\k01.md')
    1
    >>> extract_chapter_number('/path/k01/k0901.md')
    9
    The path is optional, only the file name is required, but as shown above
    both is fine. If the file name does not follow naming conventions, a
    StructuralError is raised."""
    match = re.search(r"^(?:[a-z|A-Z]+)(\d+)\.md$", os.path.basename(path))
    if not match or len(match.groups()[0]) < 2:
        raise errors.StructuralError(
            _("the file does not follow naming " "conventions"), path
        )
    return int(match.groups()[0][:2])


class FileHeading(Heading):
    """Heading which extracts chapter number and heading type from given file
    name. File name may not be a path but only the file name"""

    def __init__(self, text, level, file_name):
        super().__init__(text, level)
        self.__file_name = file_name

        def startswith(string, lst):  # does str starts with one item of list?
            for token in lst:
                if string.startswith(token):
                    return True
            return False

        if startswith(file_name, common.VALID_MAIN_BGN):
            super().set_type(Heading.Type.NORMAL)
        elif startswith(file_name, common.VALID_PREFACE_BGN):
            self.__type = Heading.Type.PREFACE
        elif startswith(file_name, common.VALID_APPENDIX_BGN):
            super().set_type(Heading.Type.APPENDIX)
        else:
            raise ValueError(
                "Couldn't extract heading type from '{}'".format(file_name)
            )

        self.set_chapter_number(extract_chapter_number(file_name))


class FileCache:
    """FileCache(files)

    The file cache stores files and their directory of a lecture root. It is
    assumed that `files` look like a list returned by os.walk() and starts in
    the lecture root. The cache sorts the files and groups them into preface,
    appendix and main chapters. Files not ending on `.md` are ignored.

    Example:

    >>> FileCache(os.walk('/path/to/some/lecture/root'))
    >>> f.get_neighbours_for('k01/k01.md') # might return
    [(v01', 'v01.md'), ('k02', 'k02.md')]
    >>> 'k01/k01.md' in f
    True
    """

    CHAPTER_PREFIX = re.compile(r"^([A-Z|a-z]+)\d+.*")

    def __init__(self, file_list):
        # initialize three "caches" for the file names
        self.__main, self.__preface, self.__appendix = [], [], []
        self.__presort(file_list)

    def __presort(self, file_list):
        """Presort chapters into preface, main and appendix."""
        for directory, _, files in file_list:
            relative_dirname = os.path.basename(directory)
            for file in files:
                if not file.endswith(".md"):
                    continue
                prefix = self.CHAPTER_PREFIX.search(file)
                if not prefix:
                    raise errors.StructuralError(
                        (
                            "The file must be in the "
                            "following format: <chapter_prefix><chapter_number>.md"
                        ),
                        os.path.join(directory, file),
                    )
                prefix = prefix.groups()[0]
                if prefix in common.VALID_PREFACE_BGN:
                    self.__preface.append((relative_dirname, file))
                elif prefix in common.VALID_MAIN_BGN:
                    self.__main.append((relative_dirname, file))
                elif prefix in common.VALID_APPENDIX_BGN:
                    self.__appendix.append((relative_dirname, file))
                else:
                    raise errors.StructuralError(
                        ("The chapter prefix %s is " "unknown") % prefix,
                        os.path.join(directory, file),
                    )
        self.__preface.sort()
        self.__main.sort()
        self.__appendix.sort()

    def __contains__(self, file):
        """Return whether a given file is contained in the cache."""
        fns = lambda x: [dir_and_file[1] for dir_and_file in x]
        return os.path.split(file)[1] in (
            fns(self.__main) + fns(self.__preface) + fns(self.__appendix)
        )

    def get_neighbours_for(self, path):
        """Return neighbours of a given chapter. Path can be absolute (file
        system) or relative to the lecture root.
        Example:
            >>> x.get_neighbours_for('/foo/bar/k03/k03.md')
            ('k02/k02.md', None) # has no next chapter
            """
        directory, file_name = os.path.split(os.path.abspath(path))
        directory = os.path.basename(directory)
        file_path = (directory, file_name)
        files = self.__preface + self.__main + self.__appendix
        for index, other_path in enumerate(files):
            if file_path == other_path:
                previous = files[index - 1] if index > 0 else None
                succ = files[index + 1] if (index + 1) < len(files) else None
                return (previous, succ)
        # if this code fragment is reached, file was not contained in list
        raise errors.StructuralError(
            ("The file was not found in the lecture. " "This indicates a bug."), path,
        )


class PageNumber:
    """Abstract representation of a page number. It consists of a identifier (a
    string like "page" or "slide), a boolean arabic (if False, roman), a boolean
    uppercase determining the case of the number if it is roman (if False, lower
    case) and a number. Number can be a range, too. Optionally, the source code
    line number can be stored as well."""

    def __init__(self, identification, number, is_arabic=True, is_uppercase=True):
        self.arabic = is_arabic
        self.identifier = identification
        self.number = number
        self.line_no = None
        self.uppercase = is_uppercase

    def __str__(self):
        conv = str if self.arabic else roman.to_roman
        if isinstance(self.number, range):
            result = "%s-%s" % (conv(self.number.start), conv(self.number.stop))
            return result.upper() if self.uppercase else result.lower()
        else:
            return conv(self.number)

    def format(self):
        """Format this page number to a Markdown page number representation.
        Note: this is one of the MAGSBS-syntax extensions."""
        return "|| - %s %s -" % (self.identifier, str(self))


class Reference:
    """This class represents a reference to ease handling of the references.
    For specifying type of reference Reference.Type is used, which is an enum.
    """

    # Naming follows the pandoc user's guide at https://pandoc.org/MANUAL.html
    class Type(enum.Enum):
        INLINE = 0  # inline link in form [text](link)
        EXPLICIT = 1  # explicit reference link in form [label]:
        IMPLICIT = 2
        # ^ implicit reference link: [label][], [label] or [text][label]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        ref_type,
        is_image,
        identifier=None,
        link=None,
        is_footnote=False,
        line_number=None,
    ):

        self.type = ref_type  # type of reference
        self.is_image = is_image  # True if reference represents an image
        self.is_footnote = is_footnote  # True if ref is a footnote
        self.id = identifier  # identifier of the link
        self.link = self.__clear_link(link)  # link itself
        self.line_number = line_number  # line number where ref occurs
        self.file_path = None  # full path of the file where ref occurs
        self.pos_on_line = None  # position on line where ref occurs

    def get_file_name(self):
        return os.path.basename(self.file_path)

    @staticmethod
    def __clear_link(uri):
        """This method removes the opening angle bracket from the beginning
        of the link and closing angle bracket from the link end."""
        if not uri:
            return None

        if uri.startswith("<"):
            uri = uri[1:]
        if uri.endswith(">"):
            uri = uri[:-1]

        return Reference.__replace_end_of_lines(uri)

    @staticmethod
    def __replace_end_of_lines(uri):
        """This method replaces the \n and \\n with spaces.
        Note: This simulates the pandoc behavior for generating href attribute
        for references."""
        output = ""
        i = 0
        escape_next = False
        while i < len(uri):
            escape_next = True if uri[i] == "\\" and not escape_next else False
            if escape_next and i < len(uri) - 1 and uri[i + 1] == "\n":
                output += " "  # \\n is changed to space char
                i += 1  # compensate the removed \n
                escape_next = False
            elif uri[i] == "\n":
                output += " "  # replace \n with space char
            else:
                output += uri[i]  # every other character
            i += 1

        return output
