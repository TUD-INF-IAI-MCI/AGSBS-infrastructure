# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2017 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""
This module abstracts everything related to calling pandoc and modifiying the
template for additional meta data in the output document(s).

Converter to different output formats can be easily added by adding the class to
the field converters of the pandoc class.
"""
#pylint: disable=multiple-imports

import os
import re
import pandocfilters
from .formats import ConversionProfile, HtmlConverter
from .. import config
from ..config import MetaInfo
from .. import common
from . import contentfilter
from .. import datastructures
from .. import errors
from .. import filesystem
from .. import mparser


def get_lecture_root(some_file):
    """Return lecture root for a file or raise exception if it cannot be
    determined."""
    path = os.path.abspath(some_file)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    is_fs_root = lambda path: os.path.dirname(path) == path
    while path and not is_fs_root(path) and not common.is_lecture_root(path):
        path = os.path.split(path)[0]
    # is `path` aproper path and not FS root
    if path and common.is_lecture_root(path):
        return path
    else:
        raise errors.StructuralError(("Could not guess the lecture root "
            "for this file"), path)


ACTIVE_CONVERTERS = [HtmlConverter]

class Pandoc:
    """Abstract the translation by pandoc into a class which add meta-information
to the output, handles errors and checks for the correct encoding.
The parameter `format` can be supplied to override the configured output format.
"""
    # json content filters:
    CONTENT_FILTERS = [contentfilter.page_number_extractor,
                    contentfilter.suppress_captions]
    # recognize chapter prefixes in paths, e.g. "anh01" for appendix chapter one
    IS_CHAPTER = re.compile(r'^%s\d+\.md$' % '|'.join(common.VALID_FILE_BGN))

    def __init__(self, conf=None):
        self.converters = [HtmlConverter]
        self.__conf = (config.ConfFactory().get_conf_instance(os.getcwd())
                if not conf else conf)
        self.__meta_data = {k.name: v  for k, v in self.__conf.items()}
        self.__meta_data['path'] = None
        self.__conv_profile = ConversionProfile.Blind

    def get_formatter_for_format(self, format):
        """Get converter object."""
        try: # get new instance
            return next(filter(lambda converter: \
                    converter.PANDOC_FORMAT_NAME == format,
                    ACTIVE_CONVERTERS))(self.__meta_data, self.__conf[MetaInfo.Language])
        except StopIteration:
            supported_formats = ', '.join(map(lambda c: c.PANDOC_FORMAT_NAME, \
                self.converters))
            raise NotImplementedError(("The configured format {} is not "
                "supported at the moment. Supported formats: {}").format(
                format, supported_formats))

    def __update_metadata(self, conf):
        """Set latest meta data from given configuration."""
        self.__meta_data = {key.name: val  for key, val in conf.items()}
        self.__meta_data['path'] = conf.get_path()

    def __get_cache(self, files):
        """See convert() for documentation."""
        if isinstance(files, datastructures.FileCache):
            cache = files
            files = cache.get_all_files()
        elif isinstance(files, (list, tuple)):
            try:
                lecture_root = get_lecture_root(files[0])
                fw = filesystem.FileWalker(lecture_root)
            except errors.StructuralError as e:
                # a single file doesn't need to be in a lecture
                if len(files) == 1:
                    fw = filesystem.FileWalker(os.path.abspath("."))
                else:
                    raise e from None
            cache = datastructures.FileCache(fw.walk())
        else:
            raise TypeError(("files argument must be either a list or tuple of "
                "file names or a FileCache object"))
        return (cache, files)

    def convert_files(self, files):
        """Convert a list of files. They should share all the meta data, except
        for the title. All files must be part of one lecture.
        `files` can be either a cache object or a list of files to convert."""
        cache, files = self.__get_cache(files)
        converter = None # declare in outer scope for finally
        try:
            c = config.ConfFactory()
            # configuration for current directory, directory changes, configuration might change too
            conf = None
            converter = None
            for file_name in files:
                # get correct configuration for each file
                newconf = c.get_conf_instance(os.path.dirname(file_name))
                # get new converter (and template) if config changes
                if not newconf is conf:
                    conf = newconf
                    self.__update_metadata(conf)
                    converter = self.get_formatter_for_format(conf[MetaInfo.Format])
                    converter.set_meta_data(self.__meta_data)
                    converter.setup()
                    converter.set_profile(self.__conv_profile)
                self.__convert_document(file_name, cache, converter, conf)
        except errors.MAGSBS_error as e:
            # set path for error
            if not e.path:
                e.path = os.path.abspath(file_name)
            raise e
        finally:
            if converter:
                converter.cleanup()

    def __convert_document(self, path, file_cache, converter, conf):
        """Convert a document by a given path. It takes a converter which takes
        actual care of the underlying format. The filecache caches the list of
        files in the lecture. The list of files within a lecture is required to
        build navigation links.
        This function also inserts a page navigation bar to navigate between
        chapters and the table of contents."""
        # if output file name exists and is newer than the original, it doesn need to be converted again
        if not converter.needs_update(path):
            return
        with open(path, 'r', encoding='utf-8') as f:
            document = f.read()
        if not document:
            return # skip empty documents
        if self.IS_CHAPTER.search(os.path.basename(path)):
            try:
                nav_start, nav_end = generate_page_navigation(path, file_cache,
                    mparser.extract_page_numbers_from_par(mparser.file2paragraphs(document)))
            except errors.FormattingError as e:
                e.path = path
                raise e
            document = '{}\n\n{}\n\n{}\n'.format(nav_start, document, nav_end)
        json_ast = self.load_json(document)
        # add MarkDown extensions with Pandoc filters
        try:
            filter = None
            for filter in Pandoc.CONTENT_FILTERS:
                json_ast = pandocfilters.walk(json_ast, filter,
                        conf[MetaInfo.Format], [])
            converter.convert(json_ast, path)
        except KeyError as e: # API clash(?)
            raise errors.StructuralError(("Incompatible Pandoc API found, while "
                "applying filter %s (ABI clash?).\nKeyError: %s") % \
                        (filter.__name__, str(e)), path)

    def load_json(self, document):
        """Load JSon input from ''inputf`` and return a reference to the loaded
        json document tree."""
        return contentfilter.text2json_ast(document)

    def set_conversion_profile(self, profile):
        if not isinstance(profile, ConversionProfile):
            raise TypeError("Expected profile of type " + \
                    type(ConversionProfile))
        self.__conv_profile = profile

    def get_convert_profile(self):
        """Return profile for conversion"""
        return self.__conv_profile

#pylint: disable=redefined-variable-type,too-many-locals
def generate_page_navigation(file_path, file_cache, page_numbers, conf=None):
    """generate_page_navigation(path, file_cache, page_numbers, conf=None)
    Generate the page navigation for a page. The file path must be relative to
    the lecture root. The file cache must be the datastructures.FileCache, the
    page numbers must have the format of mparser.extract_page_numbers_from.
    `conf=` should not be used, it is intended for testing purposes.
    Returned is a tuple with the start and the end navigation bar. The
    navigation bar itself is a string.
    """
    if not os.path.exists(file_path):
        raise errors.StructuralError("File doesn't exist", file_path)
    if not file_cache:
        raise ValueError("Cache with values may not be None")
    if not conf:
        conf = config.ConfFactory().get_conf_instance(os.path.split(file_path)[0])
    trans = config.Translate()
    trans.set_language(conf[MetaInfo.Language])
    relative_path = os.sep.join(file_path.rsplit(os.sep)[-2:])
    previous, next = file_cache.get_neighbours_for(relative_path)
    make_path = lambda path: '../{}/{}'.format(path[0], path[1].replace('.md',
        '.' + conf[MetaInfo.Format]))
    if previous:
        previous = '[{}]({})'.format(trans.get_translation('previous').title(),
                make_path(previous))
    if next:
        next = '[{}]({})'.format(trans.get_translation('next').title(), make_path(next))
    navbar = []
    page_numbers = [pnum for pnum in page_numbers
        if (pnum.number % conf[MetaInfo.PageNumberingGap]) == 0] # take each pnumgapth element
    if page_numbers:
        navbar.append(trans.get_translation('pages').title() + ': ')
        navbar.extend('[[{0}]](#p{0}), '.format(num) for num in page_numbers)
        navbar[-1] = navbar[-1][:-2] # strip ", " from last chunk
    navbar = ''.join(navbar)
    chapternav = '[{}](../inhalt.{})'.format(trans.get_translation(
            'table of contents').title(), conf[MetaInfo.Format])

    if previous:
        chapternav = previous + '  ' + chapternav
    if next:
        chapternav += "  " + next
    # navigation at start of page
    nav_start = '{0}\n\n{1}\n\n* * * *\n\n\n'.format(chapternav, navbar)
    # navigation bar at end of page
    nav_end = '\n\n* * * *\n\n{0}\n\n{1}\n'.format(navbar, chapternav)
    return (nav_start, nav_end)
