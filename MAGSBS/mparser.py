# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2017 Sebastian Humenda <shumenda |at| gmx |dot| de>
"""
This file contains a parser parsing certain syntactical structures of MarkDown
to be used for further post-processing. It is not a full MarkDown parser, but a
specialized subset parser.
"""

import collections
import enum
import os
import re

from . import config, datastructures, errors, roman


_hashed_heading = re.compile(r'^#{1,6}(?!\.)\s*\w+')


# this must be in mparser, because otherwise there will be a cyclic dependency
# between mparser and filesystem
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
        try: # try to fetch next line
            line = next(myiter)
        except StopIteration:
            has_next = False
            break
        # join as long as a \ is at the end
        while line.rstrip().endswith('\\'): # rstrip strips \n
            line = line.rstrip()[:-1] + ' ' # strip \
            try:
                nextline = next(myiter)
            except StopIteration:
                break
            lines_to_insert += 1
            if nextline.strip() == '': # empty lines don't get appended at the end of previous line
                insert_blank_lines_now = True
                line = '' # reset it to '' so that following code inserts blank lines
                break
            line += nextline
        # return line
        yield line
        if insert_blank_lines_now:
            insert_blank_lines_now = False
            line = '' # trigger line insertion for missing joined lines
        if lines_to_insert > 0 and line.strip() == '':
            # insert as many lines as were joined to retain line numbering
            for _ in range(0, lines_to_insert):
                yield ''
            lines_to_insert = 0
    raise StopIteration()

def file2paragraphs(lines, line_number, join_lines=False):
    """
file2paragraphs(lines, line_number, join_lines=False)

Return a dictionary mapping from line numbers (where paragraph started) to a
paragraph. The paragraph itself is a list of lines, not ending on\\n. The
parameter must  be iterable, so can be a file object or a list of lines. It can
be a string, in this case it's split on \\n.
If join_lines is set, lines ending on \\ will we joined with the next one.
"""
    #pylint: disable=bad-reversed-sequence
    if isinstance(lines, str):
        lines = lines.split('\n')
    if line_number:
        lines = lines[:line_number]
    paragraphs = collections.OrderedDict()

    paragraphs[1] = []
    iterator_wrappper = (joined_line_iterator if join_lines else iter)
    for lnum, line in enumerate(iterator_wrappper(lines)):
        current_paragraph = next(reversed(paragraphs))
        if line.endswith('\n'):
            line = line[:-1]
        if not line.strip(): # empty line
            # if previous paragraph is empty, this line as well, theere are
            # multiple blank lines; update line number
            if not paragraphs[current_paragraph]:
                del paragraphs[current_paragraph]
            # +1, because count starts from 1 and paragraph starts on _next_
            # line
            paragraphs[lnum+2] = []
        else:
            paragraphs[current_paragraph].append(line)
    # strip empty paragraphs at the end (\n at EOF)
    last = next(reversed(paragraphs))
    if not paragraphs[last]:
        del paragraphs[last]
    return paragraphs



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

def extract_page_numbers(path, line_number):
    """Extract page numbers from given file.
    Internally, extract_page_numbers_from_par is called.
    Returned is a list of page numbers. See extract_page_numbers_from_string for
    the actual format."""
    with open(path, 'r', encoding='utf-8') as f:
        paragraphs = file2paragraphs(f.read(), line_number)
        return extract_page_numbers_from_par(paragraphs)

def is_hashed_heading(line):
    r"""Return whether line is a heading of the form r"#{1,6}\s+\w+"."""
    return bool(_hashed_heading.search(line))


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
    return (level, text)

def extract_headings_from_par(paragraphs, max_headings=-1):
    """extract_headings_from_par(list_of_paragraphs, max_headings=-1)
    Return list of heading objects; if max_headings is set to a value > -1, only
    this number of headings will be parsed.
    These headings contain only the text, the level and the line number.
    Please note: certain properties of the Heading objects like chapter_number
    won't be set. Please use extract_headings instead.
    """
    headings = []
    def add_heading(start_line, level, text):
        h = datastructures.Heading(text, level)
        h.set_line_number(start_line)
        headings.append(h)

    for start_line, paragraph in paragraphs.items():
        if max_headings > -1 and len(headings) >= max_headings:
            break
        if not paragraphs:
            continue
        if len(paragraph) >= 2:
            if is_hashed_heading(paragraph[0]):
                for lnum, line in enumerate(paragraph):
                    if is_hashed_heading(line):
                        add_heading(start_line + lnum,
                                *parse_hashed_headings(line))
                    else:
                        break
            elif paragraph[1].startswith('==='):
                add_heading(start_line, 1, paragraph[0])
            elif paragraph[1].startswith('---') and not ' ' in paragraph[1]:
                add_heading(start_line, 2, paragraph[0])
        else: # 1 line
            if is_hashed_heading(paragraph[0]):
                add_heading(start_line, *parse_hashed_headings(paragraph[0]))
    return headings


def extract_page_numbers_from_par(paragraphs, regex=config.PAGENUMBERING_PATTERN):
    """Extract all page numbers from given paragraph list. Paragraph must be in
    the format as returned by file2paragraphs, see documentation of this
    function for details.
    Return a list of page numbers. Each page number is a
    datastructures.PageNumber. A custom regular expression for recognizing page
    numbers can be given, to e.g. detect page numbers with incorrect
    identifiers."""
    numbers = []
    # filter for paragraphs with exactly one line and the line starting with||
    pars = [(l,p) for l,p in paragraphs.items() \
            if len(p) == 1 and p[0].startswith('||')]
    for start_line, par in pars:
        result = regex.search(par[0])
        if not result:
            continue
        id, number = result.groups()[:2]
        # figure out whether arabic or roman number
        is_arabic = True
        try:
            number = int(number)
        except ValueError: # try roman number
            try:
                number = roman.from_roman(number)
                is_arabic = False
            except roman.InvalidRomanNumeralError:
                raise errors.FormattingError("cannot recognize page number",
                        number, line=start_line)


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
    pos = text_before.rfind('\n')
    if pos == -1: # no line break in text before formula, count characters and return as position
        return len(text_before) + accumulated_stringlength
    elif pos == len(text_before):
        return 1 # formula was first character on new line
    else:
        return len(text_before[pos + 1 :]) + 1



class RemoveCodeblocks:
    """This could be technically a function, but it's easier to maintain from a
    class.

    The methods of this class iterate over a list of paragraphs and remove those
    which are code blocks.
    Since identifying a code block is really tricky, this function removes only
    those for which it can assure that it is a code block. Code blocks
    are replaced with empty lines to preserve the document structure."""
    class CodeBlock(enum.Enum): # which kind of code block detected
        no_codeblock = 0
        has_codeblock = 1
        has_unclosed_codeblock = 2

    def __init__(self, paragraphs): # dummy
        self.paragraphs = paragraphs
        self.keys = list(paragraphs.keys())
        self.modified_paragraphs = collections.OrderedDict()

    def __call__(self):
        return self.run()

    def is_even(self, number):
        return (number % 2) == 0

    def run(self):
        """Parse the given paragraphs and return the modified document."""
        keys = list(self.paragraphs.keys())
        prev_par_had_codeblock = RemoveCodeblocks.CodeBlock.no_codeblock

        for start_line, par in self.paragraphs.items():
            had_code_blocks = self.handle_fenced_blocks(start_line, par, '~~~',
                    prev_par_had_codeblock)
            if had_code_blocks is RemoveCodeblocks.CodeBlock.no_codeblock:
                had_code_blocks = self.handle_fenced_blocks(start_line, par,
                    '```', prev_par_had_codeblock)
            prev_par_had_codeblock = had_code_blocks
            if had_code_blocks is not RemoveCodeblocks.CodeBlock.no_codeblock:
                par = self.modified_paragraphs[start_line] # get updated reference

            # if all lines start with indentation
            if all(not e or e[0].isspace() for e in par) and not \
                    self.prev_par_is_itemize(start_line):
                self.modified_paragraphs[start_line] = [''] * (len(par) +1)
            else: # try to replace `inline`-environments
                for index, line in enumerate(par):
                    if line.find('`') and self.is_even(line.count('`')):
                        par[index] = re.sub('`.*?`', '  ', line)
                self.modified_paragraphs[start_line] = par
        return self.modified_paragraphs


    def prev_par_is_itemize(self, current_startline):
        """Return true if previous paragraph is an itemize of first level."""
        prev = self.keys[self.keys.index(current_startline) - 1]
        if prev > 0:
            for line in reversed(self.paragraphs[prev]):
                if len(line) > 1 and line.lstrip()[:2] in ['- ', '+ ', '* ']:
                    return True

    def handle_fenced_blocks(self, start_line, paragraph, indicator,
            prev_par_codeblocks): # no/unclosed/proper code blocks found in prev paragraph?
        """Parse code blocks surrounded by ~~~ or ``` characters. Return whether
        complete, incomplete or no code blocks were found."""
        indicator_lines = tuple(i for i, line in enumerate(paragraph)
                if line.lstrip().startswith(indicator))

        if not indicator_lines:
            return RemoveCodeblocks.CodeBlock.no_codeblock

        paragraph = paragraph[:]
        # get ranges of code blocks; note: code blocks which don't end in this
        # paragraph are not a problem, they are ignored; +1 for end position
        # because ranges are exclusive in python
        ranges = map(lambda x: range(x[0], x[1]+1),
                zip(*[iter(indicator_lines)]*2))
        lines_to_replace = (ln for r in ranges for ln in r)
        for line_number in lines_to_replace:
            paragraph[line_number] = ''
        self.modified_paragraphs[start_line] = paragraph
        return RemoveCodeblocks.CodeBlock.has_codeblock


def parse_environments(document, indicator='$$', stripped_document=None,
        start_line=1):
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
    last_plain_text = ''
    pos_in_line = 1
    document = document.replace(r'\$', '  ') # remove escaped dollars
    for token in document.split(indicator):
        if formula_started:
            pos = compute_position(last_plain_text, pos_in_line)
            formulas[(line_number, pos)] = token
            # the new position depends on the length of formula and line breaks
            pos_in_line = compute_position(token, pos) + 2 * len(indicator)
            if stripped_document is not None:
                stripped_document.append(' ' * (len(token) + 2 * len(indicator)))
        else:
            last_plain_text = token # save non-formula text for later position retrieval
            if stripped_document is not None:
                stripped_document.append(token)
        formula_started = not formula_started # toggles every time
        line_number += token.count('\n')
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
    for lnum, line in enumerate(document.split('\n'), start_line):
        tokens = line.split('$')
        if len(tokens) < 3: # one or less dollars, ignore
            continue
        pos = 0
        is_formula = True # negated at beginning of iteration; counts whether
                # current token is a formula or not
        last_added = None # last key added to list of formulas
        for token in tokens:
            is_formula = not is_formula # flip flop, flip flop....
            if is_formula:
                last_added = (lnum, pos+1) # save last added key
                formulas[last_added] = token
                pos += 2 # count the two dollars of the math environment
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
        paragraph = '\n'.join(paragraph)
        parsed_paragraph = [] # paragraph with $$-environments removed
        formulas.update(parse_environments(paragraph, indicator='$$',
                stripped_document=parsed_paragraph, start_line=start_lnum))
        formulas.update(parse_single_dollar_formulas(''.join(parsed_paragraph),
            start_line=start_lnum))
    ordered = collections.OrderedDict()
    for key in sorted(formulas):
        ordered[key] = formulas[key]
    return ordered
