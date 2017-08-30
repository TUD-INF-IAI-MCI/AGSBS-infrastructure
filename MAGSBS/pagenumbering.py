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
from .config import MetaInfo

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
            conf = config.ConfFactory().get_conf_instance(path)
        else: # fall back to default configuration
            conf = config.LectureMetaData(path)
        translator = config.Translate()
        translator.set_language(conf[MetaInfo.Language])
        return datastructures.PageNumber(translator.get_translation("page"), 1)
    else:
        return datastructures.PageNumber(pagenumbers[-1].identifier,
                pagenumbers[-1].number+1, pagenumbers[-1].arabic)

def check_page_numbering(pnums):
    """This funciton checks for monotonic increasing page numbering within a
    document. Counts from the first page number onwards and will report gaps, by
    giving the page number object. When roman and arabic numbers are mixed, it
    works as follows:

    -   errors in the numbering are only reported until a style change (arabic
        to roman or vice versa)
    -   the numbering starts from the first number of a style that was detected
    -   all errors are reported, even if they rsult from a preceeding number of
        the same style far earlier
    """
    if not pnums:
        return tuple()
    errorneous = [] # tuple of page number object and expected page number (as number)
    prev = pnums[0] # previous
    for cur in pnums[1:]:
        # if previous page number was errorneous and the style is unchanged:
        if prev.arabic == cur.arabic: # same style
            if errorneous and errorneous[-1][0] == prev: # already error found
                errorneous.append((cur, errorneous[-1][1]+1))
            elif prev.number != (cur.number - 1):
                errorneous.append((cur, prev.number + 1))
        else: # different style, ignore
            pass
        prev = cur
    return errorneous

