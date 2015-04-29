# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2015 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""Common datastructures."""

import os, sys
import enum
from .errors import WrongFileNameError
from . import config

def path2chapter(string):
    """Convert a file name similar to as k010508.md, anh__.md or v__ to a tuple
of the corresponding chapter numbers.
Important: this function throws OsErrors which must be caught by the plugin /
frontend used; the supplied message can be displayed to the user."""
    old_fn = string[:] # back up file name for usage in error case
    string = os.path.split( string )[-1] # just take the file name
    if(string.endswith('.md')): string = string[:-3]
    else:
        raise WrongFileNameError('Not a supported file ending, must be .md.')

    found = False
    for prefix in config.VALID_FILE_BGN:
        if string.startswith(prefix):
            string = string[len(prefix):]
            found = True
    if not found:
        raise WrongFileNameError( "Wrong file name: got \"%s\", " % old_fn +\
                    "\not a valid chapter/paper prefix." )
    try:
        return int( string )
    except ValueError:
        raise WrongFileNameError( "Tried to convert %s to a " % string +\
                " number, looking at file %s." % old_fn )

def gen_id(text):
    """gen_id(text) -> an text for generating links.
This function tries to generate the same text's as pandoc."""
    text = text.lower()
    res_id = ''
    for char in text:
        if(char == ' '):
            res_id += '-'
        elif(char.isalpha() or char.isdigit()):
            res_id += char
        elif(char in ['.','_', '-']):
            res_id += char
        else:
            continue
    # strip hyphens at the beginning
    while(res_id.startswith('-')):
        res_id = res_id[1:]
    return res_id

class Heading():
    """heading(file_name)

This class represents a heading to ease the handling of headings.

- file_name is used to determine the full chapter number
- set_text must be called to set heading text and generate id
- set_level must be called to set the heading level in the source document

For specifying the type of a heading, Heading.Type is used, which is an enum.
"""
    class Type(enum.Enum):
        NORMAL = 0 # most headings are of that type
        APPENDIX = 1
        PREFACE = 2
    def __init__(self, path=None, file_name=None):
        self.__line_number = None
        self.__text = ''
        self.__id = ''
        self.__level = -1
        self.__chapter_number = None
        if file_name:
            self.__chapter_number = path2chapter(file_name)
        self.__path = path
        self.__file_name = file_name
        c = config.confFactory()
        c = c.get_conf_instance()
        self.__use_appendix_prefix = c['appendixPrefix']
        if not file_name:
            self.__type = Heading.Type.NORMAL
        else: # guess heading type
            if file_name.startswith('anh'):
                self.__type = Heading.Type.APPENDIX
            elif file_name.startswith('v'):
                self.__type = Heading.Type.PREFACE
            else:
                self.__type = Heading.Type.NORMAL
        self.__relative_heading_number = None

    def set_level(self, level):
        self.__level = level

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
        return self.__id

    def set_text(self, text):
        self.__text = text
        self.__id = gen_id(text)

    def get_text(self):
        return self.__text

    def set_relative_heading_number(self, number):
        """
set_relative_heading_number(list) -> set relative heading number in document."""
        if(not isinstance(number, list)):
            raise ValueError("List expected.")
        self.__relative_heading_number = number

    def get_relative_heading_number(self):
        return self.__relative_heading_number

    def use_appendix_prefix(self, usage):
        self.__use_appendix_prefix = usage

    def get_markdown_link(self):
        if not self.__chapter_number:
            raise ValueError("This heading got no information about the file name and hence cannot determine the chapter number used in the MarkDown link.")
        if(self.get_level() == 1):
            full_number = str(self.__chapter_number)
        elif(self.get_level() == -1):
            raise ValueError("Heading level not set.")
        else:
            # add chapter level additionally; relative chapter number has the
            # first item from the aray stripped of, because there will be always
            # *one* fist-level-heading.
            rh = self.get_relative_heading_number()[1:]
            # rh shall be .num.num.num if nested, else ''4
            rh = ('.' + '.'.join( [str(i) for i in rh] ) if len( rh ) else '' )
            full_number = str(self.__chapter_number) + rh

        # prefix full_number with a capital 'A' for appendices, if wished
        if self.get_type() == Heading.Type.APPENDIX and self.__use_appendix_prefix:
            full_number = 'A.' + full_number
        dir_above_file = os.path.split(self.__path)[1]
        return '[%s. %s](%s/%s.html#%s)' % (full_number, self.get_text(),
                dir_above_file, self.__file_name[:-3], self.get_id())

    def set_line_number(self, lnum):
        """Set the line number, e.g. if heading was taken from a file."""
        self.__line_number = lnum

    def get_line_number(self):
        return self.__line_number


def is_list_alike(obj):
    """Check whether object is iterable and supports indexing."""
    a = hasattr(obj, '__iter__')
    b = hasattr(obj, '__getitem__')
    return a and b

def get_encoding():
    """Return encoding for stdin/stdout."""
    encoding = sys.getdefaultencoding() # fallback
    if hasattr(sys.stdout, encoding):
        if sys.stdout.encoding:
            encoding = sys.st
    return encoding

def decode(input):
    """Safe version to decode data from subprocesses."""
    if not isinstance(input, bytes):
        raise TypeError("Only inputs are supported here.")
    return input.decode(get_encoding())


