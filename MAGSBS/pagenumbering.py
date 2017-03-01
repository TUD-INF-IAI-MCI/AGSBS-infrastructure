# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2017 Sebastian Humenda <shumenda |at| gmx |dot| de>
#               Jens Voegler <jens-v |at| gmx |dot| de>

"""
This file generates and enumerates page numbers, depending on theirpredecessors.
"""

import os

from . import config, datastructures, mparser

def add_page_number(path, line_number):
    """This function parses all page numbers from the given path and adds a new
    page number at the specified line. It parses all page numbers until this
    line and then decides what the next number is and whether it is roman or
    arabic (depending on its predecessors).
    It does not actually insert the new page number, but returns it, so that it can be inserted."""
    with open(path, 'r', encoding='utf-8') as f:
        return add_page_number_from_str(f.read(), line_number)

def add_page_number_from_str(data, line_number, path=None):
    """This function parses all page numbers from the given string and adds a new
    page number at the specified line. It parses all page numbers until this
    line and then decides what the next number is and whether it is roman or
    arabic (depending on its predecessors).
    It does not actually insert the new page number, but returns it, so that it can be inserted.
    Passing a path to the file (or its parent directory) being processed is not
    mandatory, but strongly adviced. It is used to load the lecture
    configuration for localisation."""
    paragraphs = mparser.file2paragraphs(data)
    pagenumbers = mparser.extract_page_numbers_from_par(paragraphs,
            ignore_after_lnum=line_number)
    if not pagenumbers:
        if path:
            if os.path.isfile(path):
                path = os.path.dirname(os.path.abspath(path))
            conf = config.confFactory().get_conf_instance(path)
        else: # fall back to default configuration
            conf = config.LectureMetaData(path)
        translator = config.Translate()
        translator.set_language(conf['language'])
        return datastructures.PageNumber(translator.get_translation("page"), 1)
    else:
        return datastructures.PageNumber(pagenumbers[-1].identifier,
                pagenumbers[-1].number+1, pagenumbers[-1].arabic)

