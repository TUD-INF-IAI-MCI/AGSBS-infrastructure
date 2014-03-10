# -*- coding: utf-8 -*-

import os, re
from errors import WrongFileNameError

def path2chapter(string):
    """Convert a file name as k010508.md or anh__.md to a tuple of the
corresponding chapter numbers.
Important: this functions throws OsErrors which must be caught by the plugin /
frontend used; the supplied message can be displyed to the user."""
    fn = string[:] # for debugging purposes
    if(string.startswith('k')):
        string = string[1:] # strip leading k
    elif(string.startswith('anh')):
        string = string[3:]

    if(string.endswith('.md')): string = string[:-3]
    elif(string.endswith('.html')): string = string[:-4]
    else:
        raise WrongFileNameError('Not a supported file ending, must be .html or .md.')
    erg = []
    while(string != ''):
        try:
            erg.append( int(string[:2]) )
            string = string[2:]
        except ValueError:
            raise WrongFileNameError("Wrong file name: got \"%s\" and \"%s\" was not expected." % (fn, string))
    return erg

def gen_id(id, use_umlauts=True):
    """gen_id(id) -> an ID for making links.

Todo: We ought to render the page (in memory) and find out the id's there, we do
here wild guessing. It MUST be reimplemented."""
    id = id.lower()
    res_id = ''
    for char in id:
        if(char == ' '):
            res_id += '-'
        elif(ord(char) >= 128):
            if(use_umlauts and char in [u'\xe4',u'\xf6',u'\xfc',u'\xDC']):
                res_id += char 
            else:
                continue # skip this character
        elif((ord(char) < 65) and (ord(char) > 57 or ord(char) < 49)):
            continue
        else:
            res_id += char 
    # strip trailing hyphens:
    while(res_id.startswith('-')):
        res_id = res_id[1:]
    return res_id 

class heading():
    """heading(file_name)

This class represents a heading to ease the handling of headings.

- file_name is used to determine the full chapter number
- set_text must be called to set heading text and generate id
- set_level must be called to set the heading level in the source document
"""
    def __init__(self, path, file_name):
        self.__text = ''
        self.__id = ''
        self.__level = -1
        self.__chapter_number = path2chapter(file_name)
        self.__path = path
        self.__file_name = file_name
        self.__is_shadow_heading = False
        self.__use_appendix_prefix = False

    def set_level(self, level):
        self.__level = level
    def get_level(self):
        return self.__level
    def set_shadow_heading(self, state):
        self.__is_shadow_heading = state
    def is_appendix(self):
        if(self.__file_name.startswith('anh')):
            return True
        else:
            return False
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
            full_number = '.'.join(map(lambda x: str(x),
                    self.__chapter_number))
        elif(self.get_level() == -1):
            raise ValueError("Heading level not set.")
        else:
            # add chapter level additionally; relative chapter number has the
            # first item from the aray stripped of, because there will be always
            # *one* fist-level-heading.
            full_number = '.'.join(map(lambda x: str(x),
                self.__chapter_number + self.get_relative_heading_number()[1:] ) )

        # prefix full_number with a capital 'A' for appendices, if wished
        if(self.is_appendix() and self.__use_appendix_prefix):
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
