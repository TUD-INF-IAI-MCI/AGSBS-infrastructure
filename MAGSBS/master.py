# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016-2017 Sebastian Humenda <shumenda@gmx.de>
"""For documentation about this module, please refer to its classs master."""

import os
from . import config
from .config import MetaInfo
from . import common
from . import errors
from . import filesystem
from . import pandoc
from . import toc



class Master():
    """m =Master(path)
m.run()

Take a directory and perform breath-first search to find the first
.lecture_meta_data.dcxml. In this depth, all directories are scanned for this
file so that we actually have multiple roots (a forest). This is necessary for
lectures containing e.g. lecture and exercise material.  For each root the
navigation bar and the table of contents is generated; afterwards all MarkDown
files are converted."""
    def __init__(self, path, profile):
        if os.path.exists(path):
            if os.path.isfile(path):
                raise OSError("Operation can only be applied to directories.")
            if common.is_valid_file(os.path.abspath(path)):
                raise errors.StructuralError(("The master command can only be called "
                    "on a whole lecture, not on particular chapters."), path)
        self._roots = self.__findroot(path)
        self._profile = profile

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
                if go_deeper:
                    dirs += [os.path.join(directory, e) \
                            for e in os.listdir(directory) \
                            if os.path.isdir(os.path.join(directory, e))]
        found_md = False
        for directory, _, flist in os.walk(path):
            for f in flist:
                if f.endswith(".md"):
                    found_md = True
                    break
        if roots == [] and found_md:
            # this is markdown stuff without configuration!
            raise errors.ConfigurationError(("no configuration found, but it "
                "is required"), path)
        return roots

    def get_translation(self, word, path):
        """"Return a translation for a word for a given path.
        Different paths might have different language configurations. This
        method loads the individual configuraiton."""
        conf = config.ConfFactory().get_conf_instance(path)
        trans = config.Translate()
        trans.set_language(conf[MetaInfo.Language])
        return trans.get_translation(word)

    def run(self):
        """This function should only be run from the lecture root. For other
        directories (subdirectories or unrelated directories) hopefully lead to
        a meaningful error message, but this is *not* guaranteed.

        This function creates a navigation bar, the table of contents and
        converts all files. It will raise ConfigurationError when no
        configuration has been found and there are MarkDown files."""
        try:
            self._run()
        except errors.ConfigurationError as e:
            if not e.path:
                e.path = path
            raise

    def _run(self):
        orig_cwd = os.getcwd()
        for root in self.get_roots():
            os.chdir(root)
            conf = config.ConfFactory().get_conf_instance(".")
            if conf[MetaInfo.GenerateToc]:
                # create table of contents
                c = toc.HeadingIndexer(".")
                c.walk()
                if not c.is_empty():
                    index = c.get_index()
                    md_creator = toc.TocFormatter(index, ".")
                    with open("inhalt.md", 'w', encoding="utf-8") as file:
                        file.write(md_creator.format())

            conv = pandoc.converter.Pandoc()
            files_to_convert = [os.path.join(dir, f)
                    for dir, _, flist in filesystem.get_markdown_files(".", True)
                    for f in flist]
            conv.set_conversion_profile(self._profile)
            conv.convert_files(files_to_convert)
            os.chdir(orig_cwd)
