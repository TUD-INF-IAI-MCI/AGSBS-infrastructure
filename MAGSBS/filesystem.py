"""Everything file system related goes in here."""

import os, sys, codecs
import collections

from mparser import *

def get_markdown_files(dir):
    """Return all files starting with "k" and ending on ".md". Return is a list
of 3-tuples, as os.walk() produces."""
    res = []
    for directoryname, directory_list, file_list in os.walk(dir):
        file_list = [f for f in files    if(not file.endswith('.md')
                    and not file.startswith('k'))]
        res.append( (directoryname, directory_list, file_list) )
    return res


def open_file(path, mode='r'):
"""Wrapper for encoding stuff."""
    try:
        filehandle = codecs.open( directoryname + os.sep + file, mode, \
                sys.getdefaultencoding())
    except UnicodeEncodeError:
        filehandle = codecs.open( directoryname + os.sep + file, mode,
                'utf-8')
    return filehandle


class create_index():
    """create_index(dir)
    
Walk the file system tree from "dir" and have a look in all files who end on
.md. Take headings of level 1 or 2 and add it to the index.
    
Format of index: dict of lists: every file is a list of headings, each heading
is a tuple of heading level, id and actual name. Thos are then stored in a
OrderedDict with the key being the file name and the value being the list just
described.

E.g. { 'k01.html' : [(1,'art','art'), (6,'seite-1--',' -Seite 1 -')], [...] }
"""
    def __init__(self, dir):
        self.__dir = dir
        if(not os.path.exists(dir)):
            raise(OsError("Directory doesn't exist."))
        self.__index = collections.OrderedDict()

    def walk(self):
        """walk()

By calling the function, the actual index is build."""
        tmp_dict = {}
        for directoryname, directory_list, file_list in get_markdown_files(self.__dir):
            for file in file_list:
                # open with systems default encoding
                # try systems default encoding, then utf-8, then fail
                data = open_file( file ).read()
                m = markdownHeadingParser( data )
                m.parse()
                tmp_dict[ file ] = m.get_data()
        # dicts do not keep the order of their keys (we need such for the TOC)
        # and os.walk does not read files/directories alphabetically either, so
        # sort it:

        keys = list(tmp_dict.keys())
        keys.sort()
        for key in keys:
            self.__index[key] = tmp_dict[key]


    def get_index(self):
        return self.__index


class page_index():
    """page_index(directory, page_gap)

Iterate through files in `directory`. Read in the page navigation (if any) and
update (or create) it. `page_gap` will specify which gap the navigation bar will
have for the pages."""
    def __init__(self, dir):
        self.__dir = dir
    def iterate(elf):
        """Iterate over the files and call self.trail_nav and self.gen_nav. Write
back the file."""
        for directoryname, directory_list, file_list in get_markdown_files(self.__dir):
            for file in file_list:
                fhandle = open_file( file )
                data = fhandle.read()
                data = data.trail_nav( data )
                data = data.gen_nav(data)
                codecs.open( file, 'w', fhandle.encoding).write( data )

    def trail_nav(self, page):
        comment_started = True
        new_page = []
        for line in page.split('\n')
            if(start = line.find('<!-- navigation bar') > 0):
                comment_started = True
                if(start > 2):
                    new_page.append(line:start])
            elif(comment_started and (end = line.find('-->')>0)):
                comment_started = False
                if(end < (len(line)-1)):
                    new_page.append( line[end:] ))
            else:
                if(comment_started):
                    continue # skip navigation
                else:
                    new_page.append( line )
        return page
    def gen_nav(self, page):
        return page
