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
    of instances of class Reference that contain following information:
    reference_type, line_number, id, link, is_image, is_footnote, file_name,
    file_path. Note, that some pieces of information should not be filled by
    this function.
    Note: This function assumes that markdown references are correctly
    structured according to the rules specified in pandoc manual, available at
    https://pandoc.org/MANUAL.html#links """
    output = []
    lineno = init_lineno  # number of lines that were examined
    index = 0  # specify the number of chars that were already processed
    escape_next = False  # specify if next char should be escaped
    is_in_formula = False  # specify, if the character is within formula

    while index < len(text):
        if text[index] == "\n":  # count lines
            lineno += 1
        if text[index] == "$" and not escape_next:
            is_in_formula = not is_in_formula
            # handle block formulas
            if index + 1 < len(text) and text[index + 1] == "$":
                index += 1

        # find the potential beginning of link (ignore the masked bracket and
        # cases when [ is within formula)
        if text[index] == "[" and not escape_next and not is_in_formula:
            beginning = index - max(0, index - 2)
            chars, reference = extract_link(text[index - beginning:])
            # chars recalculation - beginning should not be counted twice
            chars = chars - beginning
            # result processing, but not when it is a to-do list
            if reference and not is_todo_or_empty(reference):
                reference.line_number = lineno
                output.append(reference)
                # there should be some inner references within line text
                if reference.id:
                    for inner_reference in find_links_in_markdown(
                            reference.id, lineno):
                        output.append(inner_reference)
                # there should be some inner references in link itself
                if reference.link:
                    for inner_reference in find_links_in_markdown(
                            reference.link, lineno):
                        output.append(inner_reference)
                # need to recalculate the index char and number of lines
                for _ in range(index, index + chars):
                    index += 1
                    if index < len(text) and text[index] == "\n":
                        lineno += 1

        escape_next = True if index < len(text) and \
            text[index] == "\\" and not escape_next else False
        index += 1
    return output


def extract_link(text):
    """This function extracts the reference itself from the input text.
    Parameter text should contain opening square bracket.
    Then it is resolved and new instance of Reference class is returned. """
    if "[" not in text:
        raise ValueError("Text for extracting link must contain \"[\".")
    index = text.find("[")
    image_char, is_footnote = detect_image_footnote(text[:index + 2], index)

    # [ ... whatever ... ] part
    first_part = get_text_inside_brackets(text[index:])
    index += first_part[0]

    # solve labeled
    if index < len(text) - 1 and text[index] == "[" and text[index + 1] != "]":
        second_part = get_text_inside_brackets(text[index:])
        return index + second_part[0], Reference(
            Reference.Type.IMPLICIT, image_char, identifier=second_part[1],
            is_footnote=is_footnote)
    elif index < len(text) and text[index] == "(":  # inline links
        second_part = get_text_inside_brackets(text[index:])
        second_part_str = second_part[1]
        if second_part_str.find(r"\u0020") != -1:
            second_part_str = second_part_str[:second_part_str.find(r"\u0020")]
        return index + second_part[0], Reference(
            Reference.Type.INLINE, image_char, identifier=first_part[1],
            link=second_part_str)
    elif index < len(text) and text[index] == ":":  # explicit reference links
        if is_footnote:  # explicit reference to footnote
            end_index = text[index:].find("\n\n")
            # no two newlines there till end of string
            end_index = len(text) if end_index < 0 else end_index + index

            return end_index, Reference(
                Reference.Type.EXPLICIT, image_char, identifier=first_part[1],
                link=text[index + 2:end_index], is_footnote=True)
        # explicit reference link, is ended by first whitespace after ": "
        link = text[index + 1:].split(None, 1)[0]
        return index + len(link), Reference(Reference.Type.EXPLICIT,
                                            image_char, first_part[1], link)
    # nothing from previous = implicit reference link
    return index, Reference(Reference.Type.IMPLICIT, image_char,
                            identifier=first_part[1], is_footnote=is_footnote)


def detect_image_footnote(text, index):
    """Function detects whether the text in brackets represents an image or
    footnote. Images have the not escaped exclamation mark before opening
    square bracket. Footnote has the "^" sign right after opening square
    bracket. Function returns a tuple of two boolean values, first is True
    if text in brackets represents an image (False otherwise), second is True
    if it represents a footnote (False otherwise). """
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
    brackets should be same. Escaped brackets are ignored. Only opening square
    brackets or parentheses are allowed as a opening character. Function
    returns double - first part contains number of processed characters,
    the second one contains extracted text. """
    if not text or text[0] not in {"(", "["}:
        return None

    brackets_dict = {"[": "]", "(": ")"}
    bracket_char = text[0]
    closing_bracket_char = brackets_dict[bracket_char]

    index = 1  # processed characters (bracket is already processed)
    count_brackets = 1  # counting brackets
    output = ""
    escape_next = False

    while count_brackets > 0 and index < len(text):
        if text[index] == bracket_char and not escape_next:
            count_brackets += 1
        if text[index] == closing_bracket_char and not escape_next:
            count_brackets -= 1
        escape_next = True if text[index] == "\\" and not escape_next \
            else False
        # simulate the pandoc behaviour for \\n
        if escape_next and index < len(text) - 1 and text[index + 1] == "\n":
            output += " "  # \\n is changed to space char
            index += 1  # compensate the removed \n
            escape_next = False
        elif text[index] == "\n":
            output += " "  # replace \n with space char
        else:
            output += text[index]
        index += 1

    return index, output[:-1]


def is_todo_or_empty(reference):
    """This methods returns True if the implicit reference represents
    todo list in markdown format (i.e. in format [ ] or [x]) or identifier
    is empty, False otherwise."""
    return reference.type == Reference.Type.IMPLICIT and \
        not reference.link and reference.id.lower() in (" ", "x", "")


def get_html_elements_identifiers(document):
    """Returns a set of ids (of html elements) in a markdown document. Only
    elements allowed in matuc are processed (currently div and span elements).
    Note: When other type of element(s) are allowed, the IDS_REGEX constant
    has to be updated. """
    return set(IDS_REGEX.findall(document))
