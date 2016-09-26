# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at|gmx |dot| de>

"""Everything file system related belongs here."""

import os

from . import config
from.common import is_valid_file
from . import errors
#pylint: disable=redefined-builtin

class FileWalker():
    """Abstraction class to provide functionality as offered by os.walk(), but
omit certain files and folders.

Ignored: folders like images, bilder, .git, .svn
Files picked up: ending on configured file endings."""
    def __init__(self, path):
        if not os.path.exists(path):
            raise errors.StructuralError("Directory not found", path)
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
        if os.path.isfile(self.path):
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
                files   = [e for e in files    if is_valid_file( e )]
                newdirs = [e for e in newdirs  if is_valid_file( e )]
            dirs += newdirs
            res.append((dir, [os.path.basename(e) for e in newdirs],
                [os.path.basename( e )  for e in files]))
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

class InitLecture:
    """InitLecture()

Initialize folder structure for a lecture.

builder = InitLecture(path, numOfChapters, lang='de')
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

    def __create_chapter(self, prefix, number, images_file, translator):
        """Init a chapter, the corresponding MarkDown file and optionally a
image description file as well. This method assums that it is called from the
new lecture root."""
        _ = translator
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
            imgpath = os.path.join(path, 'bilder.md')
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
        inst['language'] = self.__lang
        inst.write()
        # read this configuration back in again using singleton
        inst = config.confFactory().get_conf_instance(".")
        trans = config.Translate()
        trans.set_language(inst['language'])
        _ = trans.get_translation

        if self.__preface:
            self.__create_chapter('v', '1', False, _)
        for index in range(1, self.__amountChapters + 1):
            if self.__no_chapters:
                self.__create_chapter('blatt', index, False, _)
            else:
                self.__create_chapter('k', index, False, _)
        for index in range(1, self.__appendix_count + 1):
            self.__create_chapter('anh', index, False, _)
        os.chdir(cwd)

