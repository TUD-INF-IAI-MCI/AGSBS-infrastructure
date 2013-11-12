"""Everything file system related goes in here."""

import os, sys, codecs
import collections

from mparser import *
import datastructures

def get_markdown_files(dir):
    """Return all files starting with "k" and ending on ".md". Return is a list
of 3-tuples, as os.walk() produces. Sort those before returning."""
    res = []
    for directoryname, directory_list, file_list in os.walk(dir):
        file_list = [f for f in file_list    if(f.endswith('.md')
                    and f.startswith('k'))]
        res.append( (directoryname, directory_list, file_list) )
    res.sort()
    return res


def file_data_encoded(path):
    """file_data_encoded(path)
Opens path. Tries to guess the encoding. Return is first the data, second the
encoding guessed."""
    encoding = 'utf-8'
    data = None
    try:
        data = codecs.open( path, 'r', \
                sys.getdefaultencoding()).read()
        encoding = sys.getdefaultencoding()
    except UnicodeDecodeError:
        data = codecs.open( path, 'r', 'utf-8').read()
    return (data, encoding)


class create_index():
    """create_index(dir)
    
Walk the file system tree from "dir" and have a look in all files who end on
.md. Take headings of level 1 or 2 and add it to the index.
    
Format of index: dict of lists: every filename is the key, the list of heading
[objects] is the value in the OeredDict()."""
    def __init__(self, dir):
        self.__dir = dir
        if(not os.path.exists(dir)):
            raise(OSError("Directory doesn't exist."))
        self.__index = collections.OrderedDict()

    def walk(self):
        """walk()

By calling the function, the actual index is build."""
        tmp_dict = {}
        for directoryname, directory_list, file_list in get_markdown_files(self.__dir):
            for file in file_list:
                # open with systems default encoding
                # try systems default encoding, then utf-8, then fail
                data, enc = file_data_encoded( os.path.join(directoryname, file) )
                m = markdownHeadingParser( data, directoryname, file )
                m.parse()
                self.__index[ file ] = m.get_heading_list()


    def get_index(self):
        return self.__index


class page_navigation():
    """page_index(directory, page_gap)

Iterate through files in `directory`. Read in the page navigation (if any) and
update (or create) it. `page_gap` will specify which gap the navigation bar will
have for the pages."""
    def __init__(self, dir, pagenumbergap, lang='de'):
        self.__dir = dir
        self.pagenumbergap = pagenumbergap
        self.__lang = lang
    def iterate(self):
        """Iterate over the files and call self.trail_nav and self.gen_nav. Write
back the file."""
        for directoryname, directory_list, file_list in get_markdown_files(self.__dir):
            for file in file_list:
                data,enc = file_data_encoded( directoryname + os.sep + file )
                data = fhandle.read()
                data = self.trail_nav( data )
                data = self.gen_nav(data)
                codecs.open( file, 'w', enc).write( data )

    def trail_nav(self, page):
        comment_started = True
        new_page = []
        for line in page.split('\n'):
            # search for supplied strings, if not found, start/end is -1
            start = line.find('<!-- navigation bar')
            end = line.find('-->')
            if(start > 0):
                comment_started = True
                if(start > 2):
                    new_page.append(line[:start])
            elif(comment_started and end>=0):
                comment_started = False
                if(end < (len(line)-1)):
                    new_page.append( line[end:] )
            else:
                if(comment_started):
                    continue # skip navigation
                else:
                    new_page.append( line )
        return '\n'.join( new_page )

    def gen_nav(self, page):
        """Generate language-specific site navigation.
English table-of-contents are referenced as ../index.html, German toc's as
../inhalt.html."""
        headings = create_index( self.__dir )
        headings.walk()
        list_of_page_numbers = [heading for heading in headings.get_index()
                    if(heading[0]==6)]
        toc = '[%s](../%s.html)' % (\
                    ('Inhalt' if self.__lang == 'de' else 'table of contents'),
                    ('inhalt' if self.__lang == 'de' else 'index') )
        navbar = [('Seiten: ' if self.__lang == 'de' else 'Pages: ')]
        for ref in list_of_page_numbers:
            if( not (int(ref[2])%self.pagenumbergap)):
                navbar.append( ' [%s](#%s)' % (ref[2], ref[1]))
        return '<p>' + toc + '\n' + ''.join( navbar ) + '<hr /></p>' + page \
                + '<p><hr />' + ''.join( navbar ) + toc + '</p>'
