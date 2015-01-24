"""Everything file system related goes in here."""

import os, sys, codecs
import collections

from MAGSBS.mparser import *
import MAGSBS.datastructures as datastructures
import MAGSBS.config as config
import MAGSBS.errors
_ = config._

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
    if(cur == root): skip = False
    if(valid_file_bgn(cur)): skip = False
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
    def set_endings(self, e):
        assert isinstance(e, list) or isinstance(e, tuple)
        self.endings = e


    def set_ignore_non_chapter_prefixed(self, x):
        """Ignore files and directories which do not adhere to the common
        lecture structure."""
        self.exclude_non_chapter_prefixed = x

    def interesting_dir(self, dir):
        """Returns true, if that directory shall be searched for files."""
        dir = os.path.split(dir)[-1]
        for bad in self.black_list:
            if(dir.lower().startswith(bad)):
                return False
        return True

    def interesting_file(self, fn):
        """Filter against file endings."""
        for ending in self.endings:
            if(fn.lower().endswith(ending)):
                return True
        return False

    def walk(self):
        if(not os.path.exists(self.path) ):
            raise OSError("Specified directory %s does not exist." % dir)
        elif os.path.isfile(self.path):
            path, file = os.path.split(self.path)
            if path == '': path = '.'
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

def is_lecture_root( dir ):
    """is_lecture_root(dir )
    Check whether the given directory is the lecture root.
    Algorithm: if dir starts with a valid chapter prefix, it is obviously not.
    for all other cases, try to obtain a list of files and if _one_
    **directory** starts with a chapter prefix, it is a valid chapter root. As
    an addition, a ".LectureMetaData.dcxml" will also mark a lecture root."""
    dir = os.path.abspath( dir )
    if( valid_file_bgn( os.path.split( dir )[-1] ) ):
        return False
    else:
        if( os.path.exists( config.CONF_FILE_NAME ) ):
            return True
        for DIR in [e for e in os.listdir( dir ) if os.path.isdir( dir+os.sep+e )]:
            if( valid_file_bgn( DIR ) ):
                return True
        return False

def fn2targetformat( fn, fmt ):
    """Alters a path to have the file name extension of the target format."""
    if( not fn.endswith('.md') ):
        raise ValueError("File must end on .md")
    return fn.replace('.md', '.'+fmt )


class create_index():
    """create_index(dir)
    
Walk the file system tree from "dir" and have a look in all files who end on
.md. Take headings of level 1 or 2 and add it to the index.
    
Format of index: dict of lists: every filename is the key, the list of heading
[objects] is the value in the OeredDict()."""
    def __init__(self, dir):
        if(not os.path.exists(dir)):
            raise(OSError("Directory doesn't exist."))
        self.__dir = dir
        self.__index = collections.OrderedDict()

    def walk(self):
        """walk()
By calling the function, the actual index is build."""
        for directoryname, directory_list, file_list in get_markdown_files(self.__dir):
            for file in file_list:
                # open with systems default encoding
                # try systems default encoding, then utf-8, then fail
                data = codecs.open( os.path.join(directoryname, file), 'r',
                        'utf-8' ).read()
                m = simpleMarkdownParser( data, directoryname, file )
                m.parse()
                m.fetch_headings()
                headings = []
                if( os.path.split( directoryname )[-1].startswith("anh") ):
                    for heading in m.get_headings():
                        heading.set_type( "appendix" )
                        headings.append( heading )
                else:
                    headings = m.get_headings()
                full_fn = os.path.join( directoryname, file)
                self.__index[ full_fn ] = headings
    
    def get_index(self):
        tmp = collections.OrderedDict()
        for key in sorted( self.__index ):
            tmp[ key ] = self.__index[ key ]
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
    def __init__(self, dir):
        if( not os.path.exists( dir ) ):
            raise OSError("The directory \"%s\" doesn't exist." % dir)
        if( not is_lecture_root( dir ) ):
            raise MAGSBS.errors.StructuralError("This command must be run from the lecture root!")
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
            if( stop ): continue
            for t in config.VALID_MAIN_BGN:
                if( tmp.startswith( t) ):
                    main.append( (dir, dlist, flist) )
                    stop = True
                    break
            if( stop ): continue
            for t in config.VALID_APPENDIX_BGN:
                if( tmp.startswith( t) ):
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
                files.append( directoryname + os.sep + file )
        has_prev = None
        has_next = None
        for pos, file in enumerate( files ):
            if( pos ):  has_prev = files[ pos -1 ]
            if( pos == (len(files)-1) ): has_next = None
            else:                        has_next = files[ pos + 1 ]
            data = codecs.open( file, 'r', 'utf-8').read()
            # guess line breaks
            if(data.find('\r\n')>=0):
                self.linebreaks = '\r\n'
            else:
                if(len(data.split('\n')) < 2):
                    self.linebreaks = '\r'
                else:
                    self.linebreaks = '\n'
            data = self.trail_nav( data )
            data = self.gen_nav(data, file, has_prev, has_next)
            codecs.open( file, 'w', 'utf-8').write( data )
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
            if(line.find('<!-- page navigation -->')>=0):
                navbar_started = True
            elif(navbar_started and (line.find('<!-- end page navigation -->') >= 0)):
                navbar_started = False
            else:
                if(not navbar_started):
                    newpage.append( line )
        return self.linebreaks.join( newpage )

    def gen_nav(self, page, file_name, has_prev, has_next):
        """Generate language-specific site navigation."""
        if(has_prev):    has_prev = fn2targetformat( has_prev, self.__fmt )
        if(has_next):    has_next = fn2targetformat( has_next, self.__fmt)
        newpage = []
        m = simpleMarkdownParser( page, self.__dir, file_name )
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
        newpage += [ '<!-- page navigation -->%s' % lbr, chapternav, lbr, lbr, ''.join(navbar) ]
        newpage += [lbr,lbr, '* * * * *', lbr, '<!-- end page navigation -->', lbr]
        if(not page.startswith(lbr)):
            newpage.append(lbr)
        elif not page.endswith(lbr):
            page += lbr
        newpage.append( page )
        newpage += [lbr, '<!-- page navigation -->', lbr, lbr,
                    '* * * * *', lbr,lbr]
        newpage += [''.join( navbar ), lbr,lbr, chapternav, lbr, '<!-- end page navigation -->']
        return ''.join(newpage)

class init_lecture():
    """init_lecture()

Initialize folder structure for a lecture."""
    def __init__(self, path, numOfChapters, lang='de'):
        self.lang = lang
        self.numOfChapters = numOfChapters
        self.path = path
        self.appendixCount = 0
        self.preface = False
    def count_appendix_chapters(self, count):
        if(not isinstance(count, int)):
            raise ValueError("Integer required.")
        self.appendixCount = count
    def set_preface(self, preface):
        if(not isinstance(preface, bool)):
            raise ValueError("Boolean required.")
        self.preface = preface
    def generate_structure(self):
        """Write out structure."""
        if(not os.path.exists( self.path )):
            os.mkdir( self.path )
        def init(path):
            chap_fn = os.path.split( path )[-1]
            if(self.lang == 'de'):
                imgfn = 'bilder.md'
                imghead = 'Bildbeschreibungen von'
            else:
                imgfn = 'images.md'
                imghead = 'Image Descriptions Of'
            os.mkdir(path)
            codecs.open(os.path.join(path, imgfn), 'w', 'utf-8').\
                    write( imghead + ' ' + chap_fn + '\n==========')
            codecs.open(os.path.join(path, chap_fn+'.md'), 'w', 'utf-8').\
                    write(chap_fn+'\n======')
        if(self.preface):
            fn = ('vorwort' if self.lang == 'de' else 'preface')
            codecs.open( os.path.join(self.path, fn+'.md'), 'w').write( \
                    fn.capitalize()+'\n========')
        for nchap in range(1,self.numOfChapters+1):
            init(os.path.join(self.path,
                        'k'+str(nchap).zfill(2).replace(' ','0')))
        for napp in range(1,self.appendixCount+1):
            init(os.path.join(self.path,
                        'anh'+str(napp).zfill(2).replace(' ','0')))

