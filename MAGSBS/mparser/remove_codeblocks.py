"""This file contains functions required to detect and remove code blocks from a
Markdown document."""

import enum
from itertools import chain
import re


def all_lines_indented(lines):
    """An indented code block must indent all lines (except for empty ones) with
    four spaces or a tab."""
    return all(not l or l.startswith('    ') or l.startswith('\t') for l in
            lines)

def is_even(num):
    return (num % 2) == 0

def rm_codeblocks(paragraphs):
    """This functions takes an ordered dict with line numbers mapping to a list
    of lines, where each of this key:value pairs represents a paragraph. All
    paragraphs with code blocks will become empty, the others are returned as
    they are.
    Keeping the paragraph with empty lines helps to preserve the document
    structure and the line numbers."""
    # this ought to be implemented in a more efficient way, but it's a shallow
    # copy, so possibly not too bad
    modified_paragraphs = paragraphs.copy()

    for start_line, par in paragraphs.items():
        changed = handle_fenced_blocks(modified_paragraphs, start_line, '~~~')
        if not changed:
            changed = handle_fenced_blocks(modified_paragraphs, start_line, '```')
        par = modified_paragraphs[start_line] # update, just to be sure
        if not changed:
            # if all lines start with indentation
            if all_lines_indented(par) and not is_indented_itemize(modified_paragraphs, start_line):
                modified_paragraphs[start_line] = [''] * (len(par) + 1)
            else: # try to replace `inline`-environments
                for index, line in enumerate(par):
                    if '`' in line and is_even(line.count('`')):
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

def skip_until(iterable, requested_key):
    """Return an iterator which fast-forwards beyond the specified key."""
    iterable = iter(iterable)
    for key in iterable:
        if key == requested_key:
            return iterable
    raise StopIteration


def handle_fenced_blocks(paragraphs, start_line, indicator):
    """Fenced code blocks are those surrounded by an indicator such as ``` or
    ~~~ (see input parameters). This function replaces all code block lines
    through empty lines. If a code block spans multiple lines, it'll peek
    forward to find the end. This function will itself update the paragraphs
    from the paragraphs input parameter, so works directly on the reference."""
    indicator_count = sum(1 for line in paragraphs[start_line]
            if line.lstrip().startswith(indicator))
    if indicator_count == 0:
        return False

    within_code_block = False
    speculative_replacement = {}
    keys = chain([start_line], skip_until(paragraphs.keys(), start_line))
    for number, key in enumerate(keys):
        if number > 6:
            break # dangling code block delimiter and already 7 paragraphs
                  # parsed, give up
        paragraph = paragraphs[key][:] # copy
        for index, line in enumerate(paragraphs[key]):
            if line.lstrip().startswith(indicator):
                within_code_block = not within_code_block
                paragraph[index] = ''
            else:
                if within_code_block:
                    paragraph[index] = ''
        if key == start_line:
            paragraphs[key] = paragraph # replace content
            if (indicator_count % 2) == 0:
                break
        elif not is_even(indicator_count):
            speculative_replacement[key] = paragraph
            if not within_code_block: # found end
                paragraphs.update(speculative_replacement)
                break
    return True


