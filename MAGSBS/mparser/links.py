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

# Regexp for finding ids within div and span html elements
IDS_REGEX = re.compile(r"<(?:div|span).*?id=[\"'](\S+?)[\"']")


def find_links_in_markdown(text, init_lineno=1):
    """This function parses the text written in markdown and creates the list
    of triples about the links. Each triple has following structure:
      (line number of link, type of link, (link triple), where link triple is:
      (! if ! is before [, empty string otherwise, link or link text, link or
      empty string). Last two parts are based on link structure. """
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
            res = extract_link(text[max(0, processed - 2):])
            if res:  # result processing
                link = clear_link(res[4])  # remove redundant chars like < or >
                output.append((lineno, res[1], (res[2], res[3], link)))
                # there should be some inner links within line text
                for inner_link in find_links_in_markdown(res[3], lineno):
                    output.append(inner_link)
                # there should be some inner links in link itself
                for inner_link in find_links_in_markdown(link, lineno):
                    output.append(inner_link)
                # need to recalculate the processed char and number of lines
                for _ in range(processed, processed + res[0] - 1):
                    processed += 1
                    if processed < len(text) and text[processed] == "\n":
                        lineno += 1

        escape_next = True if processed < len(text) and \
            text[processed] == "\\" and not escape_next else False
        processed += 1
    return output


def extract_link(text):
    """This function extract the link itself from the input text. Parameter
    text should contain opening square bracket. Then it is resolved and
    the link triple is returned.
    """
    procs = text.find("[")
    image_char, is_footnote = detect_image_footnote(text[:procs + 2], procs)

    # [ ... whatever ... ] part
    first_part = get_text_inside_brackets(text[procs:])
    procs += first_part[0]

    if procs < len(text) and text[procs] == "[":  # solve labeled
        second_part = get_text_inside_brackets(text[procs:])
        return procs + second_part[0], "labeled", image_char, first_part[1], \
            second_part[1]
    elif procs < len(text) and text[procs] == "(":  # solve inline
        second_part = get_text_inside_brackets(text[procs:])
        second_part_str = second_part[1]
        if second_part_str.find(" ") != -1:
            second_part_str = second_part_str[:second_part_str.find(" ")]
        return procs, "inline", image_char, first_part[1], second_part_str
    elif procs < len(text) and text[procs] == ":":  # solve reference
        if is_footnote:
            end_index = text[procs:].find("\n\n")
            # no two newlines there till end of string
            end_index = len(text) if end_index < 0 else end_index + procs

            return procs + end_index, "reference_footnote", image_char, \
                first_part[1], text[procs + 2:end_index]
        # normal reference, search for space after ": "
        end_index = text[procs:].find(" ", 2)
        end_index = len(text) if end_index < 0 else end_index + procs
        return end_index, "reference", image_char, first_part[1], \
            text[procs + 2:end_index]
    # nothing from previous
    return procs, "labeled", image_char, first_part[1], ""


def detect_image_footnote(text, index):
    """Function for detecting if links is image or footnote. Image has the
    exclamation mark before opening square brackets (that is not escaped).
    Footnote has the "^" sign right after opening square brackets. """
    if index > 1:
        image_char = "!" if text[0] != "\\" and text[1] == "!" else ""
    elif index > 0:
        image_char = "!" if text[0] == "!" else ""
    else:
        image_char = ""

    is_footnote = True if len(text) > index + 1 and text[index + 1] == "^" \
        else False

    return image_char, is_footnote


def get_text_inside_brackets(text):
    """Function gets the text inside brackets. Note that same brackets can be
    content of the text, however the number of opening and closing brackets
    should be same. Escaped brackets are ignored. """
    if not text or text[0] not in {"(", "["}:
        return ""

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


def clear_link(string):
    if not isinstance(string, str) or len(string) < 2:
        return string

    output = string
    if output[0] == "<":
        output = output[1:]
    if output[len(output) - 1] == ">":
        output = output[:len(output) - 1]
    return output


def get_html_elements_ids_from_document(document):
    """Returns a set of ids (of html elements) in a markdown document. Only
    elements allowed in matuc are processed (currently div and span elements).
    Note: When other type of element(s) are allowed, the IDS_REGEX constant
    has to be updated. """
    return set(IDS_REGEX.findall(document))
