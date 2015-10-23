# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2015 Sebastian Humenda <shumenda |at|gmx |dot| de>

"""Everything file system related goes in here."""

import collections
import os
import posixpath

from . import config
from . import datastructures
from . import errors
from . import mparser
_ = config._
#pylint: disable=redefined-builtin

def valid_file_bgn( cmp ):
    """Should we consider this directory or file according to the specs?"""
    cmp = os.path.split( cmp )[-1]
    for token in config.VALID_FILE_BGN:
        if(cmp.startswith( token )):
            # must be token + a number (like k01)
            if(cmp[len(token):len(token)+1].isdigit()):
                return True

def skip_dir(root, cur):
    """Check whether directory contains interesting files."""
    skip = True
    if cur == root:
        skip = False
    if valid_file_bgn(cur):
        skip = False
    return skip


def join_paths(*args):
    """os.path.join-alike function to join a arbitrari number of tokens to a
path - fixed to / as separator."""
    return '/'.join(args)


class FileWalker():
    """Abstraction class to provide functionality as offered by os.walk(), but
omit certain files and folders.

Ignored: folders like images, bilder, .git, .svn
Files picked up: ending on configured file endings."""
    def __init__(self, path):
        self.path = path
        self.black_list = ["quell",".svn",".git","bilder","images"]
        self.endings = ["md"]
        self.exclude_non_chapter_prefixed = True

    def add_blacklisted(self, new):
        self.black_list += new

    def set_endings(self, endings):
        self.endings = [(e[1:] if e.startswith('.') else e)  for e in endings]


    def set_ignore_non_chapter_prefixed(self, x):
        """Ignore files and directories which do not adhere to the common
        lecture structure."""
        self.exclude_non_chapter_prefixed = x

    def interesting_dir(self, directory):
        """Returns true, if that directory shall be searched for files."""
        directory = os.path.split(directory)[-1]
        for bad in self.black_list:
            if(directory.lower().startswith(bad)):
                return False
        return True

    def interesting_file(self, fn):
        """Filter against file endings."""
        for ending in self.endings:
            if(fn.lower().endswith(ending)):
                return True
        return False

    def walk(self):
        if not os.path.exists(self.path):
            raise OSError("Specified directory %s does not exist." % self.path)
        elif os.path.isfile(self.path):
            path, file = os.path.split(self.path)
            if path == '':
                path = '.'
            return [(path, [], [file])]
        res = []
        dirs = [self.path]
        for dir in dirs:
            if(dir == "."):
                items = os.listdir( dir )
            else:
                items = [os.path.join( dir, e)  for e in os.listdir( dir )]
            files = sorted( [e for e in items \
                        if os.path.isfile( e ) and self.interesting_file(e)])
            newdirs = sorted( [e for e in items  if os.path.isdir( e )
                        and self.interesting_dir(e)])
            if(self.exclude_non_chapter_prefixed):
                # remove those which aren't starting with a common chapter prefix
                files   = [e for e in files    if valid_file_bgn( e )]
                newdirs = [e for e in newdirs  if valid_file_bgn( e )]
            dirs += newdirs
            res.append((dir, [os.path.split(e)[-1] for e in newdirs],
                [os.path.split( e )[-1]  for e in files]) )
        return res




def get_markdown_files(dir, all_markdown_files=False):
    """os.walk(dir) -compatible function for getting all markdown files.
In fact it uses the FileWalker class and acts as a short hand.
The all_markdown_files option specifies, whether only the files adhering to the
structure or all files shall be listed ending on .md."""
    fw = FileWalker(dir)
    fw.set_ignore_non_chapter_prefixed(not all_markdown_files)
    fw.set_endings([".md"])
    return fw.walk()

def is_lecture_root(directory):
    """is_lecture_root(directory)
    Check whether the given directory is the lecture root.
    Algorithm: if dir starts with a valid chapter prefix, it is obviously not.
    for all other cases, try to obtain a list of files and if _one_
    **directory** starts with a chapter prefix, it is a valid chapter root. As
    an addition, a ".LectureMetaData.dcxml" will also mark a lecture root."""
    directory = os.path.abspath( directory )
    # if cwd starts with a chapter prefix, it is no lecture root
    if(valid_file_bgn(os.path.split( directory )[-1])):
        return False
    subdirectories = [e for e in os.listdir(directory) \
            if os.path.isdir(directory+os.sep+e)]
    for directory in subdirectories:
        if(valid_file_bgn(directory)):
            return True
    if(os.path.exists(config.CONF_FILE_NAME)):
        return True
    return False

def local_url2target_url( fn, fmt ):
    """Rewrite a local MarkDown file to a URL to be use din an HTML file. The md
    file extension is replaced by html and all backslashes are replaced by
    forward slashes."""
    if not fn.endswith('.md'):
        raise ValueError("File must end on .md")
    fn = fn.replace('.md', '.' + fmt)
    return posixpath.join(*fn.split('\\'))


class create_index():
    """create_index(dir)

Walk the file system tree from "dir" and have a look in all files which end on
.md. Take headings of level 1 or 2 and add it to the index.

Format of index: dict of lists: every filename is the key, the list of heading
[objects] is the value in the OeredDict()."""
    def __init__(self, path):
        if(not os.path.exists(path)):
            raise(OSError("Directory doesn't exist."))
        self.__dir = path
        self.__index = collections.OrderedDict()

    def walk(self):
        """walk()
By calling the function, the actual index is build."""
        for directory, directories, files in get_markdown_files(self.__dir):
            for file in files:
                # open with systems default encoding
                # try systems default encoding, then utf-8, then fail
                data = open(os.path.join(directory, file), 'r',
                        encoding='utf-8').read()
                m = mparser.SimpleMarkdownParser(data, directory, file)
                m.parse()
                m.fetch_headings()
                headings = []
                if os.path.split(directory)[-1].startswith("anh") :
                    for heading in m.get_headings():
                        heading.set_type(datastructures.Heading.Type.APPENDIX)
                        headings.append( heading )
                else:
                    headings = m.get_headings()
                full_fn = os.path.join( directory, file)
                self.__index[ full_fn ] = headings

    def get_index(self):
        tmp = collections.OrderedDict()
        for key in sorted(self.__index):
            tmp[key] = self.__index[ key ]
        return tmp

    def is_empty(self):
        """Check whether actual entries were collected for the table of
        contents."""
        empty = True
        for key,value in self.__index.items():
            if value:
                empty = False
        return empty


class page_navigation():
    """page_navigation(directory, page_gap)

Iterate through files in `directory`. Read in the page navigation (if any) and
update (or create) it. `page_gap` will specify which gap the navigation bar will
have for the pages."""
    NAVIGATION_END = '<!-- end page navigation -->'
    NAVIGATION_BEGIN = '<!-- page navigation -->'

    def __init__(self, dir):
        if not os.path.exists(dir):
            raise OSError("The directory \"%s\" doesn't exist." % dir)
        if not is_lecture_root(dir):
            raise errors.StructuralError("This command must be run from " + \
                    "the lecture root!")
        self.__dir = dir
        c = config.confFactory()
        c = c.get_conf_instance()
        self.pagenumbergap = c['pageNumberingGap']
        self.__lang = c['language']
        self.__fmt = c['format']
        self.linebreaks = '\n'

    def __preorder(self):
        preface = []
        main = []
        appendix = []
        for dir, dlist, flist in get_markdown_files(self.__dir):
            tmp = os.path.split( dir )[-1]
            stop = False
            for t in config.VALID_PREFACE_BGN:
                if( tmp.startswith( t) ):
                    preface.append( (dir, dlist, flist) )
                    stop = True
                    break
            if stop:
                continue
            for t in config.VALID_MAIN_BGN:
                if(tmp.startswith(t)):
                    main.append( (dir, dlist, flist) )
                    stop = True
                    break
            if stop:
                continue
            for t in config.VALID_APPENDIX_BGN:
                if tmp.startswith(t):
                    appendix.append( (dir, dlist, flist) )
                    stop = True
                    break
        return preface + main + appendix

    def iterate(self):
        """Iterate over the files and call self.trail_nav and self.gen_nav. Write
back the file."""
        cwd = os.getcwd()
        os.chdir( self.__dir )
        files = []
        for directoryname, directory_list, file_list in self.__preorder():
            for file in file_list:
                files.append(directoryname + os.sep + file)
        has_prev = None
        has_next = None
        for pos, file in enumerate( files ):
            if pos:
                has_prev = files[pos - 1]
            if pos == (len(files)-1):
                has_next = None
            else:
                has_next = files[ pos + 1 ]
            data = open(file, 'r', encoding='utf-8').read()
            # guess line breaks
            if data.find('\r\n')>=0:
                self.linebreaks = '\r\n'
            else:
                if len(data.split('\n')) < 2:
                    self.linebreaks = '\r'
                else:
                    self.linebreaks = '\n'
            data = self.trail_nav( data )
            data = self.gen_nav(data, file, has_prev, has_next)
            open(file, 'w', encoding='utf-8').write(data)
        os.chdir( cwd )

    def trail_nav(self, page):
        """trail_nav(page)
Trail navigation bar at top and bottom of document, if any. The navigation bar
must start with
    <!-- page navigation -->
and end again with
    <!-- end page navigation -->"""

        navbar_started = False
        newpage = []
        for line in page.split(self.linebreaks):
            if(line.find(self.NAVIGATION_BEGIN)>=0):
                navbar_started = True
            elif navbar_started and (line.find(self.NAVIGATION_END) >= 0):
                navbar_started = False
            else:
                if(not navbar_started):
                    newpage.append( line )
        return self.linebreaks.join( newpage )

    def gen_nav(self, page, file_name, has_prev, has_next):
        """Generate language-specific site navigation."""
        if has_prev:
            has_prev = local_url2target_url( has_prev, self.__fmt )
        if(has_next):
            has_next = local_url2target_url(has_next, self.__fmt)
        newpage = []
        m = mparser.SimpleMarkdownParser(page, self.__dir, file_name)
        m.parse()
        lbr = self.linebreaks

        navbar = []
        m.fetch_page_numbers()
        data = m.get_page_numbers()
        # first page number is necessary for calculations:
        if(len(data) >= 1):
            navbar.append(_('pages').title() +': ')
            pnums = list( data.keys() ) # get all page numbers
            pnums.sort()
            for pnum in pnums:
                if(pnum == pnums[0]): # in case of first page number
                    navbar.append( '[[%s]](#%s)' % (pnum, data[ pnum ]) )
                elif(pnum > (pnums[0] + (self.pagenumbergap/2))):
                    if(not (pnum%self.pagenumbergap)):
                        navbar.append( ', [[%s]](#%s)' % (pnum, data[ pnum ]) )
        chapternav = '[%s](../inhalt.html)' % _('index').title()
        if(has_prev):
            chapternav = '[%s](%s)  ' % (_('previous'),
                join_paths("..", has_prev)) + chapternav
        if(has_next):
            chapternav += "  [%s](%s)" % (_('next'),
                join_paths("..", has_next))
        newpage += [self.NAVIGATION_BEGIN, lbr, chapternav, lbr, lbr,
                ''.join(navbar)]
        newpage += [lbr,lbr, '* * * * *', lbr, self.NAVIGATION_END, lbr]
        if(not page.startswith(lbr)):
            newpage.append(lbr)
        elif not page.endswith(lbr):
            page += lbr
        newpage.append( page )
        newpage += [lbr, self.NAVIGATION_BEGIN, lbr, lbr,
                    '* * * * *', lbr,lbr]
        newpage += [''.join(navbar), lbr,lbr, chapternav, lbr,
                self.NAVIGATION_END]
        return ''.join(newpage)

class init_lecture():
    """init_lecture()

Initialize folder structure for a lecture.

builder = init_lecture(path, numOfChapters, lang='de')
builder.set_no_chapters(True|False) # use kxx or blattxx
# number of appendix chapters, 0 by default
builder.set_amount_appendix_chapters(2)
builder.set_has_preface(True) # create preface chapter
builder.generate_structure() # also inits a basic configuration
"""
    def __init__(self, path, numOfChapters, lang='de'):
        self.__lang = lang
        self.__amountChapters = numOfChapters
        self.__path = path
        self.__appendix_count = 0
        self.__preface = False
        self.__no_chapters = False

    def set_no_chapters(self, ex):
        self.__no_chapters = ex

    def set_amount_appendix_chapters(self, count):
        if(not isinstance(count, int)):
            raise TypeError("Integer required.")
        self.__appendix_count = count

    def set_has_preface(self, preface):
        if(not isinstance(preface, bool)):
            raise ValueError("Boolean required.")
        self.__preface = preface

    def __create_chapter(self, prefix, number, images_file=False):
        """Init a chapter, the corresponding MarkDown file and optionally a
image description file as well. This method assums that it is called from the
new lecture root."""
        path = prefix + str(number).zfill(2)
        if not os.path.exists(path):
            os.mkdir(path)
        chap_file = os.path.join(path, prefix + str(number).zfill(2)) + '.md'
        with open(chap_file, 'w', encoding='utf-8') as f:
            heading = _('chapter') + ' ' + str(number)
            if self.__no_chapters: # use different heading
                heading = _('paper') + ' ' + str(number)
            f.write(heading.capitalize())
            f.write('\n')
            f.write('=' * len(heading))
            f.write("\n\n")
        if images_file:
            imgpath = os.path.join(path, _('images') + '.md')
            with open(imgpath, 'w', encoding='utf-8') as f:
                f.write(_("image descriptions").capitalize())
                f.write("\n")
                f.write('=' * len(_("image descriptions")))
                f.write("\n\n")


    def generate_structure(self):
        """Create file system structure for the lecture, as configured.
Initialize basic configuration as well."""
        if not os.path.exists(self.__path):
            os.mkdir( self.__path )
        cwd = os.getcwd()
        os.chdir(self.__path)
        # initialize configuration:
        inst = config.LectureMetaData(config.CONF_FILE_NAME)
        inst.write()
        # read this configuration back in again using singleton
        inst = config.confFactory().get_conf_instance()

        if(self.__preface):
            self.__create_chapter('v', '1', False)
        for index in range(1, self.__amountChapters + 1):
            if self.__no_chapters:
                self.__create_chapter('blatt', index, False)
            else:
                self.__create_chapter('k', index, False)
        for index in range(1, self.__appendix_count + 1):
            self.__create_chapter('anh', index, False)
        os.chdir(cwd)

def newline_wrapper(lines):
    """Wrapper which wraps around an iterator emitting lines of text. If a line
    ends on \\, that will be joined with the next line before it is returned.

    If a line has been joined, another empty line is inserted to retain the line
    number count. They are inserted at the end of the just encountered paragraph
    to not cause confusion.

    This method is useful for Mistkerl checkers so they don't need to bother
    about line continuation
    This method behaves as an iterator."""
    has_next = True
    myiter = iter(lines)
    lines_to_insert = 0
    insert_blank_lines_now = False
    while has_next:
        try: # try to fetch next line
            line = next(myiter)
        except StopIteration:
            has_next = False
            break
        # join as long as a \ is at the end
        while line.rstrip().endswith('\\'): # rstrip strips \n
            line = line.rstrip()[:-1] + ' ' # strip \
            try:
                nextline = next(myiter)
            except StopIteration:
                break
            lines_to_insert += 1
            if nextline.strip() == '': # empty lines don't get appended at the end of previous line
                insert_blank_lines_now = True
                line = '' # reset it to '' so that following code inserts blank lines
                break
            line += nextline
        # return line
        yield line
        if insert_blank_lines_now:
            insert_blank_lines_now = False
            line = '' # trigger line insertion for missing joined lines
        if lines_to_insert > 0 and line.strip() == '':
            # insert as many lines as were joined to retain line numbering
            for i in range(0, lines_to_insert):
                yield ''
            lines_to_insert = 0
    raise StopIteration()

def file2paragraphs(lines, join_lines=False):
    """
file2paragraphs(lines, join_lines=False)

Return a dictionary mapping from line numbers (where paragraph started) to a
paragraph. The paragraph itself is a list of lines, not ending on\\n. The
parameter must  be iterable, so can be a file object or a list of lines.
If join_lines is set, lines ending on \\ will we joined with the next one.
"""
    paragraphs = collections.OrderedDict()
    paragraphs[1] = []
    iterator_wrappper = (newline_wrapper if join_lines else iter)
    for lnum, line in enumerate(iterator_wrappper(lines)):
        current_paragraph = next(reversed(paragraphs))
        if line.endswith('\n'):
            line = line[:-1]
        if not line.strip(): # empty line
            # if previous paragraph is empty, this line as well, theere are
            # multiple blank lines; update line number
            if not paragraphs[current_paragraph]:
                del paragraphs[current_paragraph]
            # +1, because count starts from 1 and paragraph starts on _next_
            # line
            paragraphs[lnum+2] = []
        else:
            paragraphs[current_paragraph].append(line)
    # strip empty paragraphs at the end (\n at EOF)
    last = next(reversed(paragraphs))
    if not paragraphs[last]:
        del paragraphs[last]
    return paragraphs


