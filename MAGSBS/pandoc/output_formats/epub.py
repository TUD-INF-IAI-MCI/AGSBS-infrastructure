"""HTML output format."""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2017-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>
import json
import os
import shutil
from ... import errors, mparser
from .. import contentfilter
from ..formats import execute, ConversionProfile, OutputGenerator


class EpubConverter(OutputGenerator):
    """HTML output format generator. For documentation see super class;."""
    PANDOC_FORMAT_NAME = 'epub'
    FILE_EXTENSION = 'epub'
    CONTENT_FILTERS = []

    def __init__(self, meta, language):
        if not shutil.which('pandoc'):
            raise errors.SubprocessError(['pandoc'],
                _('You need to have Pandoc installed.'))

        super().__init__(meta, language)

    def set_meta_data(self, meta):
        """Overwrite parent settr to re-generate template generation."""
        super().set_meta_data(meta)
        self.setup()

    def convert(self, files, **kwargs):
        """See super class documentation."""
        if not files:
            return
        try:
            from ..converter import get_lecture_root
            path = get_lecture_root(files[0])
            document = EpubConverter.__concat_files(files)
            self.__convert_document(document, path)
        except errors.MAGSBS_error as err:
            raise err
        finally:
            self.cleanup()

    @staticmethod
    def __handle_error(file_name, err):
        # set path for error
        if not err.path:
            err.path = os.path.abspath(file_name).replace(os.getcwd(), '').\
                    lstrip(os.sep)
        if not isinstance(err, errors.MathError):
            raise err
        # recover line and pos of formula
        eqns = mparser.parse_formulas(mparser.file2paragraphs(open(file_name)))
        line, pos = list(eqns.keys())[err.formula_count - 1]
        err.line = line
        err.pos = pos
        raise err from None # no TB here

    @staticmethod
    def __concat_files(files):
        """reads all files and return all of them as one string"""
        document = ''
        for file_name in files:
            with open(file_name, 'r', encoding='utf-8') as file:
                document += file.read()
        return document

    #pylint: disable=too-many-locals
    def __convert_document(self, document, path):
        """Convert a document. It takes a converter which takes
        actual care of the underlying format."""
        if not document:
            return # skip empty documents
        json_ast = contentfilter.load_pandoc_ast(document)
        dirname = os.path.split(path)[0]
        outputf = self.get_meta_data()['LectureTitle'] + \
                  '.' + self.FILE_EXTENSION
        pandoc_args = ['-s']
        # for 'blind' see __apply_filters, doesn't need a Pandoc argument
        if self.get_profile() is ConversionProfile.VisuallyImpairedDefault:
            pandoc_args.append('--mathjax')
        execute(['pandoc'] + pandoc_args + [
            '-t', self.PANDOC_FORMAT_NAME,
            '-f', 'json', '+RTS', '-K25000000', '-RTS', # increase stack size
            '-o', outputf
        ], stdin=json.dumps(json_ast), cwd=dirname)
