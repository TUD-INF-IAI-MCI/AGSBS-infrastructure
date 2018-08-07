"""HTML output format."""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2017-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>
import json
import os
import shutil
import tempfile
import pandocfilters
from ... import errors, mparser
from .. import contentfilter
from ..formats import execute, ConversionProfile, OutputGenerator


CSS_TEMPLATE = """/* This defines styles and classes used in the book */
body { margin: 5%; text-align: justify; font-size: medium; }
code { font-family: monospace; }
h1 { text-align: left; font-size: 2em; }
h2 { text-align: left; font-size: 1.5em; }
h3 { text-align: left; font-size: 1.17em; }
h4 { text-align: left; font-size: 1.12em; }
h5 { text-align: left; font-size: .83em; }
h6 { text-align: left; font-size: .75em; }
h1.title { }
h2.author { }
h3.date { }
ol.toc { padding: 0; margin-left: 1em; }
ol.toc li { list-style-type: none; margin: 0; padding: 0; }
a.footnote-ref { vertical-align: super; }
em, em em em, em em em em em { font-style: italic;}
em em, em em em em { font-style: normal; }
p.pagebreak { page-break-before: always; }
h1 + p.pagebreak { page-break-before: avoid; }
p.header { font-weight: bold; }
p.header[data-level="1"] { font-size: 2em; }
p.header[data-level="2"] { font-size: 1.5em; }
p.header[data-level="3"] { font-size: 1.17em; }
p.header[data-level="4"] { font-size: 1.12em; }
p.header[data-level="5"] { font-size: .83em; }
p.header[data-level="6"] { font-size: .75em; }
"""

YAML_TEMPLATE = """---
title: '{LectureTitle}'
creator:
- role: author
  text: {SourceAuthor}
- role: editor
  text: {Editor}
contributor: {WorkingGroup}
rights: {Rights}
publisher: {Institution}
lang: {Language}
...
"""

class EpubConverter(OutputGenerator):
    """HTML output format generator. For documentation see super class;."""
    PANDOC_FORMAT_NAME = 'epub'
    FILE_EXTENSION = 'epub'
    CONTENT_FILTERS = [contentfilter.epub_page_number_extractor,
                       contentfilter.epub_link_converter,
                       contentfilter.epub_collect_link_targets,
                       contentfilter.epub_create_back_links]
    IMAGE_CONTENT_FILTERS = [contentfilter.epub_convert_image_header_ids,
                             contentfilter.epub_remove_images_from_toc]
    CHAPTER_CONTENT_FILTERS = [contentfilter.epub_convert_header_ids,
                               contentfilter.epub_update_image_location]
    BACKMATTER_CONTENT_FILTERS = [contentfilter.epub_unnumbered_appendix_toc]

    def __init__(self, meta, language):
        if not shutil.which('pandoc'):
            raise errors.SubprocessError(['pandoc'],
                _('You need to have Pandoc installed.'))

        super().__init__(meta, language)
        self.css_path = None

    def setup(self):
        """Set up the EpubConverter. Prepare the css for later use."""
        self.css_path = tempfile.mktemp() + '.css'
        with open(self.css_path, "w", encoding="utf-8") as file:
            file.write(CSS_TEMPLATE)

    def set_meta_data(self, meta):
        """Overwrite parent settr to re-generate template generation."""
        super().set_meta_data(meta)
        self.setup()

    def convert(self, files, **kwargs):
        """See super class documentation."""
        if 'path' not in kwargs:
            raise ValueError('path needs to be specified to save epub.')
        if not files:
            return
        file_info = EpubConverter.__generate_file_structure(files)
        try:
            ast = self.__generate_ast(file_info, kwargs['path'])
            self.__convert_document(ast, kwargs['path'])
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
    def __generate_file_structure(files):
        """generates a structure which makes it possible to convert everything
        in order"""
        file_info = {'chapters': [], 'backmatter': [], 'images': []}
        for file_name in files:
            name = os.path.splitext(os.path.basename(file_name))[0]
            chapter = os.path.basename(os.path.dirname(file_name))
            if name == 'bilder':
                file_info['images'].append({'chapter': chapter, 'path': file_name})
            elif name == 'inhalt':
                continue  # ignore toc!
            elif name[:3] == 'anh':
                file_info['backmatter'].append({'chapter': chapter, 'path': file_name})
            else:
                file_info['chapters'].append({'chapter': chapter, 'path': file_name})
        return file_info

    def __generate_ast(self, file_info, path):
        """reads all files and generate one ast in correct order."""
        ast = {}
        for key in ['chapters', 'backmatter', 'images']:
            for entry in file_info[key]:
                with open(entry['path'], 'r', encoding='utf-8') as file:
                    json_ast = contentfilter.load_pandoc_ast(file.read())
                    contentfilter.convert_formulas(
                        os.path.join(os.path.dirname(entry['path']), 'bilder'),
                        json_ast
                    )
                    self.__apply_filters(json_ast,
                                         self.CHAPTER_CONTENT_FILTERS,
                                         path,
                                         os.path.dirname(entry['path']))
                    if key == 'images':
                        self.__apply_filters(json_ast,
                                             self.IMAGE_CONTENT_FILTERS,
                                             path)
                    elif key == 'backmatter':
                        self.__apply_filters(json_ast,
                                             self.BACKMATTER_CONTENT_FILTERS,
                                             path)
                    if ast:
                        ast['blocks'].extend(json_ast['blocks'])
                    else:
                        ast = json_ast
        meta_ast = contentfilter.load_pandoc_ast(
            YAML_TEMPLATE.format(**self.get_meta_data()))
        ast['meta'] = meta_ast['meta']
        return ast

    #pylint: disable=too-many-locals
    def __convert_document(self, json_ast, path):
        """Convert an ast. It takes a converter which takes
        actual care of the underlying format."""
        if not json_ast:
            return # skip empty asts
        # meta data which is used in more than one filter
        filter_meta = {'chapter': 1, 'ids': {}}
        self.__apply_filters(json_ast, self.CONTENT_FILTERS, path, filter_meta)
        outputf = EpubConverter.__format_filename(self.get_meta_data()['LectureTitle'] + \
                  '.' + self.FILE_EXTENSION)
        pandoc_args = ['-s', '-N',
                       '--css={}'.format(self.css_path),
                       '--toc-depth={}'.format(self.get_meta_data()['TocDepth']),
                       '--resource-path="{}"'.format(os.getcwd())]
        # for 'blind' see __apply_filters, doesn't need a Pandoc argument
        if self.get_profile() is ConversionProfile.VisuallyImpairedDefault:
            pandoc_args.append('--mathjax')
        execute(['pandoc'] + pandoc_args + [
            '-t', self.PANDOC_FORMAT_NAME,
            '-f', 'json', '+RTS', '-K25000000', '-RTS', # increase stack size
            '-o', outputf
        ], stdin=json.dumps(json_ast), cwd=path)

    def __apply_filters(self, json_ast, filters, path, meta=None):
        """add MarkDown extensions with Pandoc filters"""
        if meta is None:
            meta = []
        try:
            filter_ = None
            fmt = self.PANDOC_FORMAT_NAME
            for filter_ in filters:
                # reset chapter count for next filter which may count chapters
                if isinstance(meta, dict):
                    if 'chapter' in meta:
                        meta['chapter'] = 1
                json_ast = pandocfilters.walk(json_ast, filter_, fmt, meta)
        except KeyError as e: # API clash(?)
            raise errors.StructuralError((
                "Incompatible Pandoc API found, while "
                "applying filter %s (ABI clash?).\nKeyError: %s"
            ) % (filter.__name__, str(e)), path)

    @staticmethod
    def __format_filename(str_):
        """Take a string and return a valid filename constructed from the string.
        Uses a whitelist approach: any characters not present in valid_chars are
        removed.
         
        Note: this method may produce invalid filenames such as ``, `.` or `..`
        """
        filename = ''.join(c for c in str_
                           if c.isalpha() or c.isdigit() or c in ' _()-.')
        return filename
