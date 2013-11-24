"""Everything file system related goes in here."""

import os, sys, codecs
import collections

from mparser import *
import datastructures

def get_markdown_files(dir):
    """Return all files starting with "k" and ending on ".md". Return is a list
of 3-tuples, as os.walk() produces. Sort those before returning."""
    if(not os.path.exists(dir) ):
        raise OSError("Specified directory %s does not exist." % dir)
    res = []
    for directoryname, directory_list, file_list in os.walk(dir):
        # check, whether we are currently in a k__, anh__ or in the directoy
        # "dir", if not, skip it(!)
        tmpdir = os.path.split(directoryname)[-1]
        if(not (tmpdir == dir or tmpdir.startswith('k')
                    or tmpdir.startswith('anh'))):
            continue

        file_list = [f for f in file_list    if(f.endswith('.md')
                    and (f.startswith('k') or f.startswith('anh')))]
        directory_list = [d for d in directory_list    if(d.endswith('.md')
                    and (d.startswith('k') or d.startswith('anh')))]

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
        self.pagenumbergap = int( pagenumbergap )
        self.__lang = lang
    def iterate(self):
        """Iterate over the files and call self.trail_nav and self.gen_nav. Write
back the file."""
        for directoryname, directory_list, file_list in get_markdown_files(self.__dir):
            for file in file_list:
                fullpath = directoryname + os.sep + file 
                data,enc = file_data_encoded( fullpath )
                data = self.trail_nav( data )
                data = self.gen_nav(data, file)
                codecs.open( fullpath, 'w', enc).write( data )

    def trail_nav(self, page):
        """trail_nav(page)
Trail navigation bar at top and bottom of document, if any. The navigation bar
must start with
    <!-- page navigation -->
and end again with
    <!-- end page navigation -->"""
    
        navbar_started = False
        newpage = []
        for line in page.split('\n'):
            if(line.find('<!-- page navigation -->')>=0):
                navbar_started = True
            elif(navbar_started and (line.find('<!-- end page navigation -->') >= 0)):
                navbar_started = False
            else:
                if(not navbar_started):
                    newpage.append( line )
        return '\n'.join( newpage )

    def gen_nav(self, page, file_name):
        """Generate language-specific site navigation.
English table-of-contents are referenced as ../index.html, German toc's as
../inhalt.html."""
        newpage = []
        m = markdownHeadingParser( page, self.__dir, file_name )
        m.parse()

        navbar = [('Seiten: ' if self.__lang == 'de' else 'Pages: ')]
        # first page number is necessary for calculations:
        frst_h = None
        for heading in m.get_heading_list():
            # if it's a page number:
            if(heading.get_level()==6 and heading.is_shadow_heading()):
                if(not frst_h): # its possibly the first page number
                    frst_h = heading
                    navbar.append( frst_h.get_markdown_link() )
                # if its page number is exactly x*pagenumbergap from
                # frst_h.get_text() away, print it
                elif(not (heading.get_page_number() + frst_h.get_page_number() -1)
                    % self.pagenumbergap):
                    navbar.append(' %s' % heading.get_markdown_link() )
        toc = '[%s](../%s.html)' % (\
                    ('Inhalt' if self.__lang == 'de' else 'table of contents'),
                    ('inhalt' if self.__lang == 'de' else 'index') )
        newpage += [ '<!-- page navigation -->\n\n', toc, '\n\n', ''.join(navbar) ]
        newpage += ['\n\n* * * * *\n<!-- end page navigation -->\n']
        if(not page.startswith('\n')):
            newpage.append('\n')
        elif not page.endswith('\n'):
            page += '\n'
        newpage.append( page )
        newpage += ['\n<!-- page navigation -->\n\n* * * * *\n\n' ]
        newpage += [''.join( navbar ), '\n\n', '\n\n', toc, '\n<!-- end page navigation -->']
        return ''.join(newpage)
