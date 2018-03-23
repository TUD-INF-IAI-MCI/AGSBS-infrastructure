# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""Common datastructures."""

import enum
import os
import sys
import re
from . import errors
from . import common
from . import roman

CHAPTERNUM = re.compile(r'^[a-z|A-Z]+(\d\d).*\.md')

def gen_id(text):
    """gen_id(text) -> an text for generating links.
This function tries to generate the same text's as pandoc."""
    allowed_characters = ['.', '-', '_']
    text = text.lower()
    res_id = [] # does not contain double dash
    last_processed_char = ''
    for char in text:
        # insert hyphen if it is space AND last char was not a space
        if char.isspace() and not last_processed_char.isspace():
            res_id.append('-')
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
    return ''.join(res_id)


def get_encoding():
    """Return encoding for stdin/stdout."""
    encoding = sys.getdefaultencoding() # fallback
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
            output = in_bytes.decode("utf-8", errors='ignore')
        return output



class Heading:
    """heading(text, level)

This class represents a heading to ease the handling of headings.

For specifying the type of a heading, Heading.Type is used, which is an enum.
"""
    class Type(enum.Enum):
        NORMAL = 0 # most headings are of that type
        APPENDIX = 1
        PREFACE = 2
    def __init__(self, text, level):
        self.__line_number = None
        self.__text = text
        self.__id = gen_id(text)
        self.__level = level
        self.__chapter_number = None
        self.__type = Heading.Type.NORMAL
        self.__chapter_number = None


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
    match = re.search(r'^(?:[a-z|A-Z]+)(\d+)\.md$', os.path.basename(path))
    if not match or len(match.groups()[0]) < 2:
        raise errors.StructuralError(_("the file does not follow naming "
                "conventions"), path)
    return int(match.groups()[0][:2])


class FileHeading(Heading):
    """Heading which extracts chapter number and heading type from given file
    name. File name may not be a path but only the file name"""
    def __init__(self, text, level, file_name):
        super().__init__(text, level)
        self.__file_name = file_name
        def startswith(string, lst): # does str starts with one item of list?
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
            raise ValueError("Couldn't extract heading type from '{}'". \
                    format(file_name))

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
    CHAPTER_PREFIX = re.compile(r'^([A-Z|a-z]+)\d+.*')
    def __init__(self, file_list):
        # initialize three "caches" for the file names
        self.__main, self.__preface, self.__appendix = [], [], []
        self.__presort(file_list)

    def __presort(self, file_list):
        """Presort chapters into preface, main and appendix."""
        for directory, _, files in file_list:
            relative_dirname = os.path.split(directory)[1]
            for file in files:
                if not file.endswith('.md'):
                    continue
                prefix = self.CHAPTER_PREFIX.search(file)
                if not prefix:
                    raise errors.StructuralError(("The file must be in the "
                        "following format: <chapter_prefix><chapter_number>.md"),
                        os.path.join(directory, file))
                prefix = prefix.groups()[0]
                if prefix in common.VALID_PREFACE_BGN:
                    self.__preface.append((relative_dirname, file))
                elif prefix in common.VALID_MAIN_BGN:
                    self.__main.append((relative_dirname, file))
                elif prefix in common.VALID_APPENDIX_BGN:
                    self.__appendix.append((relative_dirname, file))
                else:
                    raise errors.StructuralError(("The chapter prefix %s is "
                        "unknown") % prefix, os.path.join(directory, file))
        self.__preface.sort()
        self.__main.sort()
        self.__appendix.sort()

    def __contains__(self, file):
        """Return whether a given file is contained in the cache."""
        fns = lambda x: [dir_and_file[1] for dir_and_file in x]
        return os.path.split(file)[1] in (fns(self.__main) + fns(self.__preface)
                + fns(self.__appendix))

    def get_neighbours_for(self, path):
        """Return neighbours of a given chapter. Path can be absolute (file
        system) or relative to the lecture root.
        Example:
            >>> x.get_neighbours_for('/foo/bar/k03/k03.md')
            ('k02/k02.md', None) # has no next chapter
            """
        directory, file_name = os.path.split(os.path.abspath(path))
        _, directory = os.path.split(directory)
        file_path = (directory, file_name)
        files = self.__preface + self.__main + self.__appendix
        for index, other_path in enumerate(files):
            if file_path == other_path:
                previous = (files[index-1] if index > 0 else None)
                succ = (files[index+1] if (index+1) < len(files) else None)
                return (previous, succ)
        # if this code fragment is reached, file was not contained in list
        raise errors.StructuralError(("The file was not found in the lecture. "
            "This indicates a bug."), path)



class PageNumber:
    """Abstract representation of a page number. It consists of a identifier (a
    string like "page" or "slide), a boolean arabic (if False, roman) and a
    number. Number can be a range, too. Optionally, the source code line number
    can be stored as well."""
    def __init__(self, identification, number, is_arabic=True):
        self.arabic = is_arabic
        self.identifier = identification
        self.number = number
        self.line_no = None

    def __str__(self):
        conv = (str if self.arabic else roman.to_roman)
        if isinstance(self.number, range):
            return '%s-%s' % (conv(self.number.start), conv(self.number.stop))
        else:
            return conv(self.number)

    def format(self):
        """Format this page number to a Markdown page number representation.
        Note: this is one of the MAGSBS-syntax extensions."""
        return '|| - %s %s -' % (self.identifier, str(self))


class Reference:
    """This class represents a reference to ease handling of the references."""
    def __init__(self, ref_type, is_image, identifier=None, link=None,
                 is_footnote=False, line_number=None):
        self.__type = ref_type
        self.__is_image = is_image
        self.__is_footnote = is_footnote
        self.__id = identifier
        self.__link = self.clear_link(link)
        self.__line_number = line_number

    def get_line_number(self):
        return self.__line_number

    def get_type(self):
        return self.__type

    def get_is_image(self):
        return self.__is_image

    def get_is_footnote(self):
        return self.__is_footnote

    def get_id(self):
        return self.__id

    def get_link(self):
        return self.__link

    def set_line_number(self, line_number):
        self.__line_number = line_number

    def clear_link(self, link):
        """This function removes the opening angle bracket from the beginning
        of the link and closing angle bracket from the link end. """
        if not link or len(link) < 2:
            return None

        if link[0] == "<":
            link = link[1:]
        if link[len(link) - 1] == ">":
            link = link[:len(link) - 1]
        return link
