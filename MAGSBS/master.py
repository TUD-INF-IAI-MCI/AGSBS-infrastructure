# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda@gmx.de>
"""For documentation about this module, please refer to its classs master."""

import os
from . import config
from . import errors
from . import filesystem
from . import pandoc
from . import toc


class NoLectureConfigurationError(errors.MAGSBS_error):
    pass

class Master():
    """m =Master(path)
m.run()

Take a directory and perform breath-first search to find the first
.lecture_meta_data.dcxml. In this depth, all directories are scanned for this
file so that we actually have multiple roots (a forest). This is necessary for
lectures containing e.g. lecture and exercise material.  For each root the
navigation bar and the table of contents is generated; afterwards all MarkDown
files are converted."""
    def __init__(self, path):
        self._roots = self.__findroot( path )

    def get_roots(self):
        return self._roots

    def __findroot(self, path):
        roots = []
        dirs = [path]
        go_deeper = True
        for directory in dirs:
            meta = [e for e in os.listdir(directory) if e ==
                    config.CONF_FILE_NAME]
            if meta: # found, this is our root
                roots.append(directory)
                go_deeper = False
            else:
                if(go_deeper):
                    dirs += [os.path.join(directory, e) \
                            for e in os.listdir(directory) \
                            if os.path.isdir(os.path.join(directory, e))]
        found_md = False
        for directory, _, flist in os.walk(path):
            for f in flist:
                if f.endswith(".md"):
                    found_md = True
                    break
        if(roots == [] and found_md):
            # this is markdown stuff without configuration!
            raise NoLectureConfigurationError("No configuration in a directory of the path \"%s\" or its subdirectories found. As soon as there are MarkDown files present, a configuration has to exist." % path)
        return roots

    def get_translation(self, word, path):
        """"Return a translation for a word for a given path.
        Different paths might have different language configurations. This
        method loads the individual configuraiton."""
        conf = config.confFactory().get_conf_instance(path)
        trans = config.Translate()
        trans.set_language(conf['language'])
        return trans.get_translation(word)

    def run(self):
        """This function should be used with great care. It shall only be run from
the root of a lecture. All other attempts will destroy the navigation links and
result in other undefined behavior.

This function creates a navigation bar, the table of contents and converts all
files. It will raise NoLectureConfigurationError when no configuration has been
found and there are MarkDown files."""
        orig_cwd = os.getcwd()
        for root in self.get_roots():
            os.chdir(root)
            conf = config.confFactory().get_conf_instance(root)
            if conf['generateToc']:
                # create table of contents
                c = toc.HeadingIndexer(".")
                c.walk()
                if not c.is_empty():
                    index = c.get_index()
                    md_creator = toc.TOCFormatter(index, ".")
                    with open("inhalt.md", 'w', encoding="utf-8") as file:
                        file.write(md_creator.format())

            conv = pandoc.Pandoc()
            files_to_convert = [os.path.join(dir, f)
                    for dir, _, flist in filesystem.get_markdown_files(".", True)
                    for f in flist]
            conv.convert_files(files_to_convert)
            os.chdir(orig_cwd)

