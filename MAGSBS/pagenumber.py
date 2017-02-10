# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2017 Sebastian Humenda <shumenda |at| gmx |dot| de>
#               Jens Voegler <jens-v |at| gmx |dot| de>

"""
This file generate page numbers depending on previous informations
"""

import collections
from . import mparser, roman

def get_page_number(path, line_number):
    pagenumbers = mparser.extract_page_numbers(path, line_number)
    pagenum = 1
    # increment pagenumber
    if len(pagenumbers) > 0:
        pagenum = int(pagenumbers[-1].number)+1
        if not pagenumbers[-1].arabic:
            pagenum = roman.to_roman(pagenum)
    return pagenum
