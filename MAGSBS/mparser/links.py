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

from ..datastructures import Reference

# Regexp for finding ids within div and span html elements
IDS_REGEX = re.compile(r"<(?:div|span).*?id=[\"'](\S+?)[\"']")


def find_links_in_markdown(text, init_lineno=1):
    """This function parses the text written in markdown and creates the list
    of instances of Reference class. It contains all information about the
    reference: reference_type, line_number, id, link, is_image, is_footnote."""
    output = []
    lineno = init_lineno  # number of lines that were examined
    processed = 0  # specify the number of chars that were already processed
    escape_next = False  # specify if next char should be escaped
    is_in_formula = False  # specify, if the character is within formula

    while processed < len(text):
        if text[processed] == "\n":  # count lines
            lineno += 1
        if text[processed] == "$" and not escape_next:
            is_in_formula = not is_in_formula
            # handle block formulas
            if processed + 1 < len(text) and text[processed + 1] == "$":
                processed += 1

        # find the potential beginning of link (ignore the masked bracket and
        # cases when [ is within formula)
        if text[processed] == "[" and not escape_next and not is_in_formula:
            lines, reference = extract_link(text[max(0, processed - 2):])
            if reference:  # result processing
                reference.set_line_number(lineno)
                output.append(reference)
                # there should be some inner references within line text
                if reference.get_id():
                    for inner_reference in find_links_in_markdown(
                            reference.get_id(), lineno):
                        output.append(inner_reference)
                # there should be some inner references in link itself
                if reference.get_link():
                    for inner_reference in find_links_in_markdown(
                            reference.get_link(), lineno):
                        output.append(inner_reference)
                # need to recalculate the processed char and number of lines
                for _ in range(processed, processed + lines - 1):
                    processed += 1
                    if processed < len(text) and text[processed] == "\n":
                        lineno += 1

        escape_next = True if processed < len(text) and \
            text[processed] == "\\" and not escape_next else False
        processed += 1
    return output


def extract_link(text):
    """This function extract the reference itself from the input
    text. Parameter text should contain opening square bracket.
    Then it is resolved and the instance of Reference class is returned.
    """
    procs = text.find("[")
    image_char, is_footnote = detect_image_footnote(text[:procs + 2], procs)

    # [ ... whatever ... ] part
    first_part = get_text_inside_brackets(text[procs:])
    procs += first_part[0]

    # solve labeled
    if procs < len(text) - 1 and text[procs] == "[" and text[procs + 1] != "]":
        second_part = get_text_inside_brackets(text[procs:])
        return procs + second_part[0], Reference("labeled", image_char,
                                            identifier=second_part[1])
    elif procs < len(text) and text[procs] == "(":  # solve inline links
        second_part = get_text_inside_brackets(text[procs:])
        second_part_str = second_part[1]
        if second_part_str.find(" ") != -1:
            second_part_str = second_part_str[:second_part_str.find(" ")]
        return procs, Reference("inline", image_char, identifier=first_part[1],
                           link=second_part_str)
    elif procs < len(text) and text[procs] == ":":  # solve reference links
        if is_footnote:  # footnote reference link
            end_index = text[procs:].find("\n\n")
            # no two newlines there till end of string
            end_index = len(text) if end_index < 0 else end_index + procs

            return procs + end_index, Reference("reference", image_char,
                                                identifier=first_part[1],
                                                link=text[procs + 2:end_index],
                                                is_footnote=True)
        # normal reference link, search for space after ": "
        end_index = text[procs:].find(" ", 2)
        end_index = len(text) if end_index < 0 else end_index + procs
        return end_index, Reference("reference", image_char, first_part[1],
                               text[procs + 2:end_index])
    # nothing from previous
    return procs, Reference("labeled", image_char, identifier=first_part[1])


def detect_image_footnote(text, index):
    """Function detects whether the text in brackets represents an image or
    footnote. Images have the not escaped exclamation mark before opening
    square brackets. Footnote has the "^" sign right after opening square
    brackets. Function returns a tuple of two boolean values, first is True
    if text in brackets represent image (False otherwise), second is True
    if it represents footnote (False otherwise). """
    if index > 1:
        is_image = text[0] != "\\" and text[1] == "!"
    elif index > 0:
        is_image = text[0] == "!"
    else:
        is_image = False

    is_footnote = True if len(text) > index + 1 and text[index + 1] == "^" \
        else False

    return is_image, is_footnote


def get_text_inside_brackets(text):
    """Function extracts the text inside brackets. Note that same brackets
    can be content of the text, however the number of opening and closing
    brackets should be same. Escaped brackets are ignored. """
    if not text or text[0] not in {"(", "["}:
        return None

    brackets_dict = {"[": "]", "(": ")"}
    bracket_char = text[0]
    closing_bracket_char = brackets_dict[bracket_char]

    procs = 1  # processed characters (bracket is already processed)
    count_brackets = 1  # counting brackets
    output = ""
    escape_next = False

    while count_brackets > 0 and procs < len(text):
        if text[procs] == bracket_char and not escape_next:
            count_brackets += 1
        if text[procs] == closing_bracket_char and not escape_next:
            count_brackets -= 1
        escape_next = True if text[procs] == "\\" and not escape_next \
            else False
        output += text[procs]

        procs += 1

    return procs, output[:-1]


def get_html_elements_ids_from_document(document):
    """Returns a set of ids (of html elements) in a markdown document. Only
    elements allowed in matuc are processed (currently div and span elements).
    Note: When other type of element(s) are allowed, the IDS_REGEX constant
    has to be updated. """
    return set(IDS_REGEX.findall(document))
