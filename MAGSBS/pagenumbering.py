# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2017 Sebastian Humenda <shumenda |at| gmx |dot| de>
#               Jens Voegler <jens-v |at| gmx |dot| de>

"""
This file generates and enumerates page numbers, depending on their predecessors.
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
    with open(path, "r", encoding="utf-8") as f:
        return add_page_number_from_str(f.read(), line_number, path)


def add_page_number_from_str(data, line_number, path=None):
    """This function parses all page numbers from the given string and adds a new
    page number at the specified line. It parses all page numbers until this
    line and then decides what the next number is and whether it is roman or
    arabic (depending on its predecessors).
    It does not actually insert the new page number, but returns it, so that it can be inserted.
    Passing a path to the file (or its parent directory) being processed is not
    mandatory, but strongly advised. It is used to load the lecture
    configuration for localisation."""
    paragraphs = mparser.file2paragraphs(data)
    pagenumbers = mparser.extract_page_numbers_from_par(
        paragraphs, ignore_after_lnum=line_number
    )
    if not pagenumbers:
        if path:
            if os.path.isfile(path):
                path = os.path.dirname(os.path.abspath(path))
            conf = config.ConfFactory().get_conf_instance(path)
        else:  # fall back to default configuration
            conf = config.LectureMetaData(path)
        translator = config.Translate()
        translator.set_language(conf[MetaInfo.Language])
        return datastructures.PageNumber(translator.get_translation("page"), 1)
    else:
        last_pnum = pagenumbers[-1]
        return datastructures.PageNumber(
            last_pnum.identifier,
            (
                last_pnum.number.stop
                if isinstance(last_pnum.number, range)
                else last_pnum.number
            )
            + 1,
            last_pnum.arabic,
        )


def check_page_numbering(pnums):
    """This function checks for monotonic increasing page numbering within a
    document. Counts from the first page number onwards and will report gaps, by
    giving the page number object. When roman and arabic numbers are mixed, it
    works as follows:

    -   errors in the numbering are only reported until a style change (arabic
        to roman or vice versa)
    -   the numbering starts from the first number of a style that was detected
    -   all errors are reported, even if they result from a preceding number of
        the same style far earlier
    """
    if not pnums:
        return ()

    erroneous = []  # tuple of page number object and expected page number (as number)

    # Check first number as special case.
    first_num = pnums[0].number
    if isinstance(first_num, range) and first_num.start >= first_num.stop:
        # Only allow increasing ranges; reverse range (one simple possible fix).
        start = first_num.stop
        diff = first_num.start - first_num.stop    # `.start` >= `.stop`
        erroneous.append((pnums[0], range(start, start + diff) if diff != 0 else start))

    for prev, cur in zip(pnums, pnums[1:]):
        different_style = prev.arabic != cur.arabic

        prev_num = prev.number
        if different_style:
            # No previous number as orientation on style reset.
            prev_num = cur.number
        elif erroneous and erroneous[-1][0] == prev:
            # Override expectation with potentially more precise value.
            prev_num = erroneous[-1][1]

        expected = (
            prev_num.stop if isinstance(prev_num, range) else prev_num
        ) + 1 * (not different_style)    # Only add one when style stays the same.

        cur_num, cur_diff = (
            (cur.number.start, cur.number.stop - cur.number.start)
            if isinstance(cur.number, range)
            else (cur.number, 0)
        )

        if cur_diff < 0:
            # Reverse range to only allow increasing ranges.
            cur_diff *= -1
        elif different_style or cur_num == expected:
            # Different style, expected value and correct range.
            continue

        erroneous.append((
            cur,
            range(expected, expected + cur_diff) if cur_diff != 0 else expected,
        ))

    return erroneous
