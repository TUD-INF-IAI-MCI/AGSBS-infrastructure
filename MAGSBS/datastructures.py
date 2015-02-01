# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

import os, re
from .errors import WrongFileNameError
from . import config

def path2chapter(string):
    """Convert a file name similar to as k010508.md, anh__.md or v__ to a tuple of the
corresponding chapter numbers.
Important: this function throws OsErrors which must be caught by the plugin /
frontend used; the supplied message can be displayed to the user."""
    old_fn = string[:] # back up file name for usage in error case
    string = os.path.split( string )[-1] # just take the file name
    if(string.endswith('.md')): string = string[:-3]
    else:
        raise WrongFileNameError('Not a supported file ending, must be .md.')

    found = False
    for prefix in config.VALID_FILE_BGN:
        if( string.startswith( prefix ) ):
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

def gen_id(id):
    """gen_id(id) -> an ID for making links.

The id's are wild-guessed. It'll fail as soon as non-German texts occure. One
way is to make the code more robust, the other is to render the HTML-page in
memory and parse the id's from there."""
    id = id.lower()
    res_id = ''
    for char in id:
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

class heading():
    """heading(file_name)

This class represents a heading to ease the handling of headings.

- file_name is used to determine the full chapter number
- set_text must be called to set heading text and generate id
- set_level must be called to set the heading level in the source document

There is a list of valid types (heading.types) containing all possible types of
a heading. heading.get_type() will only return those. set_type() however will
raise a type error, if the type is not recognized.
"""
    def __init__(self, path, file_name):
        self.__text = ''
        self.__id = ''
        self.__level = -1
        self.__chapter_number = path2chapter(file_name)
        self.__path = path
        self.__file_name = file_name
        self.__is_shadow_heading = False
        c = config.confFactory()
        c = c.get_conf_instance()
        self.__use_appendix_prefix = c['appendixPrefix']
        self.types = ['main', # usual headings
                'appendix', 'preface']
        if(file_name.startswith('anh')):
            self.__type = 'main'
        elif(file_name.startswith('v')):
            self.__type = 'preface'
        else:
            self.__type = '__main__'

    def set_level(self, level):
        self.__level = level
    def get_level(self):
        return self.__level
    def set_shadow_heading(self, state):
        self.__is_shadow_heading = state
    def get_type(self):
        return self.__type
    def set_type(self, type):
        if(not type in self.types):
            raise ValueError("Wrong heading type. Must be either main, appendix or preface.")
        else:
            self.__type = type

    def is_shadow_heading(self):
        """Headings, marked as such, but not real headings. Example: page numbers."""
        return self.__is_shadow_heading
    def get_id(self):            return self.__id
    def set_text(self, text):
        self.__text = text
        self.__id = gen_id(text)
    def get_text(self):            return self.__text
    def set_relative_heading_number(self, number):
        """
set_relative_heading_number(list) -> set relative heading number in document."""
        if(not isinstance(number, list)):
            raise ValueError("List expected.")
        self.__relative_heading_number = number

    def get_page_number(self):
        """Return page number, if it's a page heading, else raise ValueError."""
        if(not self.is_shadow_heading() or not self.get_level() == 6):
            raise ValueError("Not a page number heading, so no page number available.")
        pgn = re.search('.*?(\d+).*', self.get_text()).groups()[0]
        return int(pgn)

    def get_relative_heading_number(self):
        return self.__relative_heading_number
    def use_appendix_prefix(self, usage):
        self.__use_appendix_prefix = usage

    def get_markdown_link(self):
        if(self.get_level() == 1):
            full_number = str( self.__chapter_number )
        elif(self.get_level() == -1):
            raise ValueError("Heading level not set.")
        else:
            # add chapter level additionally; relative chapter number has the
            # first item from the aray stripped of, because there will be always
            # *one* fist-level-heading.
            rh = self.get_relative_heading_number()[1:]
            # rh shall be .num.num.num if nested, else ''4
            rh = ('.' + '.'.join( [str(i) for i in rh] ) if len( rh ) else '' )
            full_number = str( self.__chapter_number ) + rh

        # prefix full_number with a capital 'A' for appendices, if wished
        if(self.get_type() == 'appendix' and self.__use_appendix_prefix):
            full_number = 'A.' + full_number
        if(self.is_shadow_heading()):
            # output a link like used in navigation bar
            number = re.search('.*?(\d+).*', self.get_text()).groups()[0]
            return '[%s](#%s)' % (number, self.get_id())
        else:
            dir_above_file = os.path.split( self.__path )[1]
            return '[%s. %s](%s#%s)' % ( \
                    full_number,
                    self.get_text(),
                    dir_above_file + '/' + self.__file_name.replace('.md','.html'),
                    self.get_id()
                    )
def is_list_alike(type):
    """Check whether object is iterable and supports indexing."""
    a = hasattr(type, '__iter__')
    b = hasattr(type, '__getitem__')
    return a and b
