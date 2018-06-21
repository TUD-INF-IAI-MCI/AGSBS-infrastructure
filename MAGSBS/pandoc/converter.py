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
from .formats import ConversionProfile, HtmlConverter, OutputFormat
from .. import config
from ..config import MetaInfo
from .. import common
from .. import datastructures
from .. import errors
from .. import filesystem


ACTIVE_CONVERTERS = [HtmlConverter]

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


def get_file_extension(format_):
    """Get converter file extension for a specific format."""
    try: # get new instance
        return next(filter(lambda converter: \
                converter.PANDOC_FORMAT_NAME == format_,
                ACTIVE_CONVERTERS)).FILE_EXTENSION
    except StopIteration:
        supported_formats = ', '.join(map(lambda c: c.PANDOC_FORMAT_NAME, \
            ACTIVE_CONVERTERS))
        raise NotImplementedError(("The configured format {} is not "
            "supported at the moment. Supported formats: {}").format(
            format, supported_formats))


class Pandoc:
    """Abstract the translation by pandoc into a class which add meta-information
to the output, handles errors and checks for the correct encoding.
"""
    def __init__(self, conf=None):
        self.converters = ACTIVE_CONVERTERS
        self.__conf = (config.ConfFactory().get_conf_instance(os.getcwd())
                if not conf else conf)
        self.__meta_data = {k.name: v  for k, v in self.__conf.items()}
        self.__meta_data['path'] = None
        self.__conv_profile = ConversionProfile.Blind
        self.__output_format = OutputFormat.Html

    def get_formatter_for_format(self, format_):
        """Get converter object."""
        try: # get new instance
            return next(filter(lambda converter: \
                    converter.PANDOC_FORMAT_NAME == format_,
                    ACTIVE_CONVERTERS))(
                        self.__meta_data,
                        self.__conf[MetaInfo.Language]
                    )
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

    @staticmethod
    def __get_cache(files):
        """See convert() for documentation."""
        if isinstance(files, datastructures.FileCache):
            cache = files
            files = cache.get_all_files()
        elif isinstance(files, (list, tuple)):
            try:
                lecture_root = get_lecture_root(files[0])
                file_walker = filesystem.FileWalker(lecture_root)
            except errors.StructuralError as e:
                # a single file doesn't need to be in a lecture
                if len(files) == 1:
                    file_walker = filesystem.FileWalker(os.path.abspath("."))
                else:
                    raise e from None
            cache = datastructures.FileCache(file_walker.walk())
        else:
            raise TypeError(("files argument must be either a list or tuple of "
                "file names or a FileCache object"))
        return (cache, files)

    def convert_files(self, files):
        """converts a list of files. They should share all the meta data, except
        for the title. All files must be part of one lecture.
        `files` can be either a cache object or a list of files to convert."""
        cache, files = Pandoc.__get_cache(files)
        converter = None # declare in outer scope for finally
        converter = self.get_formatter_for_format(self.__output_format.value)
        converter.set_meta_data(self.__meta_data)
        converter.setup()
        converter.set_profile(self.__conv_profile)
        converter.convert(files, cache=cache)

    def set_conversion_profile(self, profile):
        if not isinstance(profile, ConversionProfile):
            raise TypeError("Expected profile of type " + \
                    type(ConversionProfile))
        self.__conv_profile = profile

    def set_output_format(self, format_):
        if not isinstance(format_, OutputFormat):
            raise TypeError("Expected format of type " + \
                    type(OutputFormat))
        self.__output_format = format_
