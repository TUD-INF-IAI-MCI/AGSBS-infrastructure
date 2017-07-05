"""This file contains functions required to detect and remove code blocks from a
Markdown document."""

import collections
import enum
import re


class BlockKind(enum.Enum): # which kind of code block detected
    NoCodeBlock = 0
    HasCodeBlock = 1
    HasUnclosedCodeBlock = 2

def all_lines_indented(lines):
    """An indented code block must indent all lines (except for empty ones) with
    four spaces or a tab."""
    return all(not l or l.startswith('    ') or l.startswith('\t') for l in
            lines)

def rm_codeblocks(paragraphs):
    """This functions takes an ordered dict with line numbers mapping to a list
    of lines, where each of this key:value pairs represents a paragraph. All
    paragraphs with code blocks will become empty, the others are returned as
    they are.
    Keeping the paragraph with empty lines helps to preserve the document
    structure and the line numbers."""
    modified_paragraphs = collections.OrderedDict()
    is_even = lambda num: (num % 2) == 0


    for start_line, par in paragraphs.items():
        (par, had_code_blocks) = handle_fenced_blocks(par, '~~~')
        if had_code_blocks is BlockKind.NoCodeBlock:
            (par, had_code_blocks) = handle_fenced_blocks(par, '```')
        if had_code_blocks is not BlockKind.NoCodeBlock:
            modified_paragraphs[start_line] = par # get updated reference

        # if all lines start with indentation
        if all_lines_indented(par) and not is_indented_itemize(paragraphs, start_line):
            modified_paragraphs[start_line] = [''] * (len(par) + 1)
        else: # try to replace `inline`-environments
            for index, line in enumerate(par):
                if line.find('`') and is_even(line.count('`')):
                    par[index] = re.sub('`.*?`', '  ', line)
            modified_paragraphs[start_line] = par
    return modified_paragraphs


def is_indented_itemize(paragraphs, current_startline):
    """Check whether the current indentation is due to an itemize environment.
    This can be achieved by skipping any indented text to the point that an item
    sign was found. If non-indented normal text is found, False is returned."""
    keys = list(paragraphs.keys())
    idx = keys.index(current_startline)
    for lineno in reversed(keys[:idx]):
        par = paragraphs[lineno]
        # any itemize environment in this paragraph?
        if any(len(l) > 1 and l.lstrip()[:2] in ['- ', '+ ', '* ']
                        for l in par):
            return True # I'm aware that indented code blocks with an example markdown list won't work
        elif all_lines_indented(par):
            continue # not clear whether it's a list
        else: # no itemize, no indentation — not an indented itemize
            return False

def handle_fenced_blocks(paragraph, indicator):
    """Parse code blocks surrounded by ~~~ or ``` characters. Return whether
    complete, incomplete or no code blocks were found."""
    indicator_lines = tuple(i for i, line in enumerate(paragraph)
            if line.lstrip().startswith(indicator))

    if not indicator_lines:
        return (paragraph, BlockKind.NoCodeBlock)

    paragraph = paragraph[:]
    # get ranges of code blocks; note: code blocks which don't end in this
    # paragraph are not a problem, they are ignored; +1 for end position
    # because ranges are exclusive in python
    ranges = map(lambda x: range(x[0], x[1]+1),
                zip(*[iter(indicator_lines)]*2))
    lines_to_replace = (ln for r in ranges for ln in r)
    for line_number in lines_to_replace:
        paragraph[line_number] = ''
    return (paragraph, BlockKind.HasCodeBlock)


