# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2017 Sebastian Humenda <shumenda |at| gmx |dot| de>

import os
import re

from .. import datastructures, errors

_hashed_heading = re.compile(r'^#{1,6}(?!\.)\s*\w+')

def extract_chapter_from_path(path):
    """extract_chapter_from_path(path) -> return chapter number
    Examples:
    >>> extract_chapter_from_path('c:\\k01\\k01.md')
    1
    >>> extract_chapter_from_path('/path/k01/k0901.md')
    9
    The path is optional, only the file name is required, but as shown above
    both is fine. If the file name does not follow naming conventions, a
    StructuralError is raised."""
    chapter_number = os.path.split(path)[-1].replace('.md', '')
    while chapter_number and chapter_number[0].isalpha():
        chapter_number = chapter_number[1:]
    if (len(chapter_number)%2) != 0 or not chapter_number or \
            not chapter_number[0].isdigit():
        raise errors.StructuralError("the file does not follow naming conventions", path)
    if len(chapter_number) > 2:
        chapter_number = chapter_number[:2] # only keep first two digits (main chapter number)
    return int(chapter_number)




def parse_hashed_headings(text):
    """For markdown headings starting with #, return level and text as tuple.
    Example:
    >>>> parse_hashed_headings("### foo bar")
    (3, 'foo bar')"""
    level = 0
    while text.startswith('#'):
        level += 1
        text = text[1:]
    while text.endswith('#'):
        text = text[:-1]
    text = text.lstrip().rstrip()
    return (text, level)


def is_hashed_heading(line):
    r"""Return whether line is a heading of the form r"#{1,6}\s+\w+"."""
    return bool(_hashed_heading.search(line))



def __extract_hashed(start_line, paragraph):
    prevline = []
    for lnum, line in enumerate(paragraph):
        if prevline:
            prevline[1] += '\n' + line
            if line.rstrip().endswith('\\'):
                continue
            else: # continuation ended
                h = datastructures.Heading(*parse_hashed_headings(prevline[1]))
                h.set_line_number(start_line + prevline[0])
                prevline = None
                yield h
        elif is_hashed_heading(line):
            if line.endswith('\\'):
                prevline = [lnum, line[:-1].rstrip()]
            else:
                h = datastructures.Heading(*parse_hashed_headings(line))
                h.set_line_number(start_line + lnum)
                yield h
        else:
            break

def extract_headings_from_par(paragraphs, max_headings=-1):
    """extract_headings_from_par(list_of_paragraphs, max_headings=-1)
    Return list of heading objects; if max_headings is set to a value > -1, only
    this number of headings will be parsed.
    These headings contain only the text, the level and the line number.
    Please note: certain properties of the Heading objects like chapter_number
    won't be set. Please use extract_headings instead.
    """
    headings = []
    def add_heading(start_line, text, level):
        h = datastructures.Heading(text, level)
        h.set_line_number(start_line)
        headings.append(h)

    for start_line, paragraph in paragraphs.items():
        if max_headings > -1 and len(headings) >= max_headings:
            break
        if not paragraphs:
            continue
        if is_hashed_heading(paragraph[0]):
            headings.extend(__extract_hashed(start_line, paragraph))
            continue
        # find --- or ===, for this, read the "first line", including line
        # continuation instructions
        potential_underline_at = 0 # second line
        text = ''
        if paragraph[0].endswith('\\'):
            while potential_underline_at < len(paragraph) and \
                    paragraph[potential_underline_at].endswith('\\'):
                text += paragraph[potential_underline_at].rstrip('\\') + '\n'
                potential_underline_at += 1
        text += paragraph[potential_underline_at] # get last line without backslash
        potential_underline_at += 1 # ended on last line of text, need to be at underline
        if potential_underline_at >= len(paragraph):
            continue # no underline
        if paragraph[potential_underline_at].startswith('==='):
            add_heading(start_line, text, 1)
        elif paragraph[potential_underline_at].startswith('---') and \
                not ' ' in paragraph[potential_underline_at]:
            add_heading(start_line, text, 2)
    return headings


def extract_headings(path, paragraphs):
    """Extract headings from given paragraphs with given path. Internally,
    extract_headings_from_par is called.
    The difference to extract_headings_from_par is that it'll annotate the
    chapter number form the given path."""
    headings = []
    chapter_number = extract_chapter_from_path(path)
    for heading in extract_headings_from_par(paragraphs):
        heading.set_chapter_number(chapter_number)
        headings.append(heading)
    return headings


