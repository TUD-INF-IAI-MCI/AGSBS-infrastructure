# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2018 Sebastian Humenda <shumenda |at| gmx |dot| de>
#   Jaromir Plhak <xplhak |at| gmail |dot| com>

"""
Functions in this file allows linkchecker to extract the links from .md files
and to get the ids from allowed html elements.

Note: This parser expects the file with correct markdown links (e.g. no spaces
    between brackets used for link are allowed).
"""

import re

# Searches for the patterns in the form [link_text](link) (it also includes
# images with exclamation mark).
INLINE = r"(!?)\[([^\]\[\(\)]+)\]\(([^)\s]+).*?\)"

# Searches for the same patterns as INLINE, but this contains nested image
# inside link text. The example can be:
# [![Bildbeschreibung](bilder/test.jpg)](bilder.html#title-of-the-graphic)
INLINE_NESTED = \
    r"(!?)\[([^\[\]\(\)]*(?:!?)?\[(?:.*?)\]\((?:.*)\)?)\]\(([^)\s]+).*?\)"

# Searches for the patterns in the forms [link_text][link_ref], [link_ref]
# and [link_ref][] (it also includes images with exclamation mark).
# Labeled links should be coupled with the REFERENCE or REFERENCE_FOOTNOTE.
LABELED = r"(!)?\[([^\[\]]+)(?:\]\[)?([^\[\]]*)\](?!/?:|/?\()+"

# Searches for references in form [link_ref]: link (link_ref should not start
# with ^ character - in this case it is a REFERENCE_FOOTNOTE.
# This reference should be coupled with LABELED links through link_ref
# (link insensitively).
# Note: Detection for exclamation mark is used due to compatibility with the
# structure of previous regexps (and could be used for link structure checks).
REFERENCE = r"(!?)\[([^\^\]]+[^\]]+)\]:\s*<?([^>\s]+)>?"

# Searches for references to footnotes in form [^link_ref]: text (where text
# end with \n\n or end of file). In the text, there can be e.g. inline links.
REFERENCE_FOOTNOTE = r"(!?)\[(\^[^\]]+)\]:(.*?)(?:\n\n|\Z)"

# This constant represents the dictionary of used regular expressions for
# parsing .md files. The structure is "description_of_regexp_type": regexp.
REG_EXPS = {"inline": INLINE, "inline_nested": INLINE_NESTED,
            "labeled": LABELED, "reference": REFERENCE,
            "reference_footnote": REFERENCE_FOOTNOTE}

# Regexp for finding ids within div and span html elements
IDS_REGEX = r"<(?:div|span).*?id=[\"'](\S+?)[\"']"


def get_starting_line_numbers(reg_expr, text):
    """ This function searches for the line number of the regular expression
    matches.
    Note: This is not the most efficient way to do this. In case, the
        examined data will have non-trivial length and number of links,
        this function should be reimplemented. """
    line_numbers = []
    matches = re.compile(reg_expr, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    for match in matches.finditer(text):
        # One is added, because there is no line ending in front first line
        line_numbers.append(1 + text[0:match.start()].count('\n'))
    return line_numbers


def find_links_in_markdown(text):
    """ Return the the list of triples that contains the links retrieved
    from the markdown string. Triples are structured as follows:
    - line number of the link;
    - type of regular expression that matched the link;
    - link itself. It could be a raw text or tuple (based on the regexp used).
    """
    output = []
    for description, reg_expr in REG_EXPS.items():
        # detects the line numbers
        line_nums = get_starting_line_numbers(reg_expr, text)
        links = re.compile(
            reg_expr, re.MULTILINE | re.DOTALL | re.IGNORECASE).findall(text)
        if len(line_nums) != len(links):
            raise ValueError("Line numbers count should be the same"
                             " as the number of regular expressions.")

        for i, link in enumerate(links):
            output.append((line_nums[i], description, link))
    return output


def get_ids_of_html_elements(text):
    """ Returns a set of ids for valid html elements that are allowed
    in matuc (currently div and span elements).
    Note: When new element(s) will be allowed, the IDS constant has to
        be updated. """
    output = set()
    result = re.compile(IDS_REGEX).findall(text)
    for elem in result:
        output.add(elem)
    return output
