# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""
This file contains a parser parsing certain syntactical structures of MarkDown
to be used for further post-processing. It is not a full MarkDown parser, but a
specialized subset parser.
"""

import collections
import os
import re

from .. import config, datastructures, errors, roman

from .headings import extract_headings_from_par, extract_headings
from .remove_codeblocks import rm_codeblocks
from .links import get_html_elements_identifiers, find_links_in_markdown

# this has to be in mparser, because otherwise there will be a cyclic dependency
# between mparser and filesystem
def joined_line_iterator(lines):
    """joined_line_iterator(iterable)
    The joined_line_iterator iterates over `iterable` (should emit strings) and
    joins those which end on `\\`. So:

        joined_line_iterator['a','b\\','c','d']) = ['a','b c', 'd']

    If a line has been joined, another empty line is inserted at the end of the
    paragraph to retain the line number count.

    This method is useful for Mistkerl checkers so they don't need to bother
    about line continuation"""
    has_next = True
    myiter = iter(lines)
    lines_to_insert = 0
    insert_blank_lines_now = False
    while has_next:
        try:  # try to fetch next line
            line = next(myiter)
        except StopIteration:
            has_next = False
            break
        # join as long as a \ is at the end
        while line.rstrip().endswith("\\"):  # rstrip strips \n
            line = line.rstrip()[:-1] + " "  # strip \
            try:
                nextline = next(myiter)
            except StopIteration:
                break
            lines_to_insert += 1
            if (
                nextline.strip() == ""
            ):  # empty lines don't get appended at the end of previous line
                insert_blank_lines_now = True
                line = ""  # reset it to '' so that following code inserts blank lines
                break
            line += nextline
        # return line
        yield line
        if insert_blank_lines_now:
            insert_blank_lines_now = False
            line = ""  # trigger line insertion for missing joined lines
        if lines_to_insert > 0 and line.strip() == "":
            # insert as many lines as were joined to retain line numbering
            for _ in range(0, lines_to_insert):
                yield ""
            lines_to_insert = 0


def file2paragraphs(lines, join_lines=False):
    """
file2paragraphs(lines, last_line=0, join_lines=False)

Return a dictionary mapping from line numbers (where paragraph started) to a
paragraph. The paragraph itself is a list of lines, not ending on\\n. The
parameter must  be iterable, so can be a file object or a list of lines. It can
be a string, in this case it's split on \\n.
If join_lines is set, lines ending on \\ will we joined with the next one.
"""
    # pylint: disable=bad-reversed-sequence
    if isinstance(lines, str):
        lines = lines.split("\n")
    paragraphs = collections.OrderedDict()
    paragraphs[1] = []

    iterator_wrappper = joined_line_iterator if join_lines else iter
    for lnum, line in enumerate(iterator_wrappper(lines)):
        current_paragraph = next(reversed(paragraphs))
        line = line.rstrip()  # remove \n, if it exists
        if not line:  # empty line
            # if previous paragraph is empty, this line as well, theere are
            # multiple blank lines; update line number
            if not paragraphs[current_paragraph]:
                del paragraphs[current_paragraph]
            # +1, because count starts from 1 and paragraph starts on next line
            paragraphs[lnum + 2] = []
        else:
            paragraphs[current_paragraph].append(line)
    # strip empty paragraphs at the end (\n at EOF)
    last = next(reversed(paragraphs))
    if not paragraphs[last]:
        del paragraphs[last]
    return paragraphs


def extract_page_numbers(path, ignore_after_lnum=-1):
    """Extract page numbers from given file.
    Internally, extract_page_numbers_from_par is called.
    If ignore_after_lnum is passed, all line numbers after this one are ignored.
    It is set to -1 by default.
    Returned is a list of page numbers. See extract_page_numbers_from_string for
    the actual format."""
    with open(path, "r", encoding="utf-8") as f:
        paragraphs = file2paragraphs(f.read())
        return extract_page_numbers_from_par(
            paragraphs, ignore_after_lnum=ignore_after_lnum
        )


def extract_page_numbers_from_par(
    paragraphs, ignore_after_lnum=-1, regex=config.PAGENUMBERING_PATTERN
):
    """Extract all page numbers from a document.
    Arguments:
    1.  paragraph list, a list of all paragraphs in the document, see `file2paragraphs` for more details.
    2.  `ignore_after_lnum=-1`: if set to a non-negative value, all page numbers
        after the specified line are ignored.
    3.  `regex=...`, specify a different regular expression to identify page
        numbers.
    Returned is  a list of page numbers. Each page number is a
    datastructures.PageNumber."""
    numbers = []
    if not paragraphs:
        return []
    if ignore_after_lnum <= 0:
        ignore_after_lnum = max(paragraphs.keys()) + 1
    # filter for paragraphs with exactly one line and the line starting with||
    # and before ignore_after_lnum
    paragraphs = (
        (l, p)
        for l, p in paragraphs.items()
        if len(p) == 1 and p[0].startswith("||") and l <= ignore_after_lnum
    )

    paragraphs = list(paragraphs)
    for start_line, par in paragraphs:
        result = regex.search(par[0])
        if not result:
            continue
        id, number = result.groups()[:2]
        # figure out whether arabic or roman number
        is_arabic = True
        try:
            number = int(number)
        except ValueError:  # try roman number
            try:
                number = roman.from_roman(number)
                is_arabic = False
            except roman.InvalidRomanNumeralError:
                raise errors.FormattingError(
                    "cannot recognize page number", number, line=start_line
                )

        pnum = datastructures.PageNumber(id, number, is_arabic=is_arabic)
        pnum.line_no = start_line
        numbers.append(pnum)
    return numbers


################################################################################
#   formula parser


def compute_position(text_before, accumulated_stringlength=1):
    """compute_position(text_before, accumulated_stringlength)
    text_before is the token found in front of the formula. This function
    returns the position of the formula in the current line, determined by the
    text_before part and the accumulated_stringlength. The
    accumulated_stringlength is a number necessary for lines with multiple
    formulas to track the position within a line and has to start with one.
    Positions are already normalized for user output, so the count starts at
    1. Example:
    assert compute_position('') == 1
    assert compute_position('a\n', 1) == 1
    assert compute_position('ab', 1) == 3"""
    pos = text_before.rfind("\n")
    if (
        pos == -1
    ):  # no line break in text before formula, count characters and return as position
        return len(text_before) + accumulated_stringlength
    elif pos == len(text_before):
        return 1  # formula was first character on new line
    else:
        return len(text_before[pos + 1 :]) + 1


def parse_environments(
    document, indicator="$$", stripped_document=None, start_line=1
):
    """parse_environments(document, indicator='$$'', stripped_document=None,
    start_line=1)
    This function will parse environments starting with a configurable indicator
    and extract the contents of these environments together with their exact
    positions. The line number and position within the line will start from 1.
    Returned is a unsorted dictionary mapping from a tuple with line number and
    position to the content of the environment.
    If further manipulations should be applied to the document,
    stripped_document can be applied: this reference to a list will be used to
    add the tokens of the same document, with all of the occurences of indicator
    and the content in between replaced by spaces. This way the document can be
    further postprocessed without the environment being considered anymore and
    the line number and position being the same.
    The start_line argument tells this function to start counting the lines from
    the given number.
    This function does not work well with single-dollar (indicator='$') math
    environments, see parse_single_dollar_formulas() for an explanation."""
    formulas = {}
    formula_started = False
    line_number = start_line
    last_plain_text = ""
    pos_in_line = 1
    document = document.replace(r"\$", "  ")  # remove escaped dollars
    for token in document.split(indicator):
        if formula_started:
            pos = compute_position(last_plain_text, pos_in_line)
            formulas[(line_number, pos)] = token
            # the new position depends on the length of formula and line breaks
            pos_in_line = compute_position(token, pos) + 2 * len(indicator)
            if stripped_document is not None:
                stripped_document.append(
                    " " * (len(token) + 2 * len(indicator))
                )
        else:
            last_plain_text = (
                token  # save non-formula text for later position retrieval
            )
            if stripped_document is not None:
                stripped_document.append(token)
        formula_started = not formula_started  # toggles every time
        line_number += token.count("\n")
    return formulas


def parse_single_dollar_formulas(document, start_line=1):
    """This function will parse the given document to extract all single-dollar
    math environments out of it. Returned is a unsorted dictionary mapping from
    (line number, position) (both starting from 1) to the content of the
    formula.
    Straying $'s are ignored, so i.e.

        blubelidupp $formula$ and $ invalid

    will yield {(1, 13): ...}."""
    formulas = {}
    for lnum, line in enumerate(document.split("\n"), start_line):
        tokens = line.split("$")
        if len(tokens) < 3:  # one or less dollars, ignore
            continue
        pos = 0
        is_formula = True  # negated at beginning of iteration; counts whether
        # current token is a formula or not
        last_added = None  # last key added to list of formulas
        for token in tokens:
            is_formula = not is_formula  # flip flop, flip flop....
            if is_formula:
                last_added = (lnum, pos + 1)  # save last added key
                formulas[last_added] = token
                pos += 2  # count the two dollars of the math environment
            pos += len(token)
        # if not is_formula, an environment was untermined or a dollar not escaped,
        # discard last formula, possibly whole line is broken
        if is_formula and last_added in formulas:
            del formulas[last_added]
    return formulas


def parse_formulas(paragraphs):
    """Parse all formulas from a document. Note: this function is rather costly,
    since it involves a lot of string operations.
    Returned is an OrderedDict with formulas in the correct order."""
    formulas = {}
    for start_lnum, paragraph in paragraphs.items():
        paragraph = "\n".join(paragraph)
        parsed_paragraph = []  # paragraph with $$-environments removed
        formulas.update(
            parse_environments(
                paragraph,
                indicator="$$",
                stripped_document=parsed_paragraph,
                start_line=start_lnum,
            )
        )
        formulas.update(
            parse_single_dollar_formulas(
                "".join(parsed_paragraph), start_line=start_lnum
            )
        )
    ordered = collections.OrderedDict()
    for position in sorted(formulas):
        ordered[position] = formulas[position]
    return ordered
