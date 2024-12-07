# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016-2023 Sebastian Humenda <shumenda |at|gmx |dot| de>
# pylint: disable=unused-argument
"""
To convert lecture material and books taillored to our requirements, content
filters have been written, stored in this module. A content filter is a function
(or program) working on the abstract document representation of a Pandoc
document and extracting, removing or alterint the AST."""

import json
import os
import re
import subprocess
import sys
from xml.dom import minidom
from xml.parsers.expat import ExpatError

import pandocfilters

import gleetex
import gleetex.pandoc

from ..errors import MathError, SubprocessError
from ..mparser import pnum_from_str


html = lambda text: pandocfilters.RawBlock("html", text)

# pylint: disable=inconsistent-return-statements
def page_number_extractor(key, value, fmt, meta):
    """Scan all paragraphs for those starting with || to parse it for page
    numbering information."""
    if not (fmt == "html" or fmt == "html5" or fmt == "epub"):
        return
    if key == "Para" and value:
        # find first obj with content (line breaks don't have this)
        text = None
        for obj in value:
            if "c" in obj:
                text = obj["c"]
                break
        if text is None:
            return  # no content in Paragraph - ignore
        # first chunk of paragraph must be str and contain '||'
        if isinstance(text, str) and text.startswith("||"):
            text = pandocfilters.stringify(value)  # get whole text of page number
            pnum = pnum_from_str(text)
            if pnum:
                # strip the first ||
                text = text[2:].lstrip().rstrip()
                if fmt == "epub":
                    return html(
                        '<p class="pagebreak"><span id="p{0}">{1}</span></p>'.format(
                            pnum, text
                        )
                    )
                return html(
                    '<p><span id="p{0}">{1}</span></p>'.format(pnum, text)
                )


def html_link_converter(key, value, fmt, meta, modify_ast=True):
    """Change file extension of links from .md to .html to make the linking more
    format-independent."""
    if not (fmt == "html" or fmt == "html5"):
        return
    if key == "Link" and value:
        link = value[-1][0]  # last element contains the actual link
        # filter out all absolute links
        if not link or ":" in link:
            return
        if isinstance(link, str):
            link_parts = link.split("#", 1)  # split in # once
            if not link_parts[0]:
                return
            link_parts[0] = os.path.splitext(link_parts[0])[0] + ".html"
            value[-1][0] = "#".join(link_parts)


def epub_link_converter(key, value, fmt, meta, modify_ast=True):
    """Scans all links and changes them according to the current chapter.
    meta stores all link IDs so it's possible to add the back links correctly.
    meta structure: { 'chapter': int, 'ids': dict }
    the 'ids' dict contains the ids of the links as key and
    the chapter as key"""
    if fmt != "epub" or not value:
        return
    if key == "Link":
        link = value[-1][0]  # last element contains the actual link
        # filter out all absolute links
        if not link or ":" in link:
            return
        if isinstance(link, str):
            link_parts = link.split("#", 1)  # split in # once
            if len(link_parts) < 2 or not link_parts[0] or not link_parts[1]:
                return
            # check if link id is within 'ids' dict of meta
            if link_parts[1] in meta["ids"]:
                # set chapter from meta
                link_parts[0] = "ch{:03d}.xhtml".format(meta["ids"][link_parts[1]])
                value[-1][0] = "#".join(link_parts)


def epub_convert_header_ids(key, value, fmt, url_prefix, modify_ast=True):
    """Prepends all header IDs with the chapter number and updates all links
    to images with the image_ prefix.
    Header: e.g. 'header_id' -> 'k02_header_id'
    Image: e.g. 'image_id' -> 'image_k02_image_id'"""
    if fmt != "epub" or not value:
        return
    # prepend all header IDs with the chapter
    if key == "Header":
        value[1][0] = "_".join([url_prefix, value[1][0]])
    elif key == "Link":
        link = value[-1][0]  # last element contains the actual link
        # filter out all absolute links
        if not link or ":" in link:
            return
        if isinstance(link, str):
            link_parts = link.split("#", 1)  # split in # once
            if len(link_parts) < 2 or not link_parts[1]:  # return if there is no anchor
                return
            link_parts[1] = "_".join([url_prefix, link_parts[1]])
            # check if link is attached to an image and update it
            if (
                isinstance(value[1][0], dict)
                and value[1][0]["t"]
                and value[1][0]["t"] == "Image"
            ):
                link_parts[1] = "image_{}".format(link_parts[1])
            value[-1][0] = "#".join(link_parts)


def epub_convert_image_header_ids(key, value, fmt, meta, modify_ast=True):
    """prepends all image header IDs with 'image_'"""
    if key == "Header" and value:
        value[1][0] = "image_{}".format(value[1][0])


def epub_remove_images_from_toc(key, value, fmt, meta):
    """Converts all headers to be just paragraphs so that images are not
    added to toc."""
    if fmt != "epub":
        return
    # convert all headres to raw blocks
    # paragrapf contains 3 attributes:
    # id: image id
    # class: "header" or "header pagebrak" for correct display
    # data-level: header level from original header
    # <p id="image_id" class="header" data-level="2">Image</p>
    if key == "Header" and value:
        # find first obj with content (line breaks don't have this)
        text = None
        header_level = 0
        _id = ""
        # extract all relevant values
        for obj in value:
            if isinstance(obj, int):
                header_level = obj
            elif isinstance(obj, list):
                for inner_obj in obj:
                    if isinstance(inner_obj, str):
                        _id = inner_obj
                    elif isinstance(inner_obj, dict):
                        if "c" in inner_obj:
                            text = inner_obj["c"]
        # check if everything is there
        if text is None or header_level == 0 or _id == "":
            return  # no valid content
        # create raw block
        if isinstance(text, str):
            text = pandocfilters.stringify(value)
            return html(
                '<p id="{0}" class="{1}" data-level="{2}">{3}</p>'.format(
                    _id,
                    "header pagebreak" if header_level == 1 else "header",
                    header_level,
                    text,
                )
            )


def epub_update_image_location(key, value, fmt, url_prefix, modify_ast=True):
    """Updates all image references (referenced relative to the lecture root) so
    that pandoc can find and add them correctly for epub.
    E.g:
    before: bilder/image.png
    after: k02/bilder/image.png"""
    if fmt != "epub":
        return
    if key == "Image" and value:
        image_url = value[-1][0]
        if not image_url or image_url[0] == "/" or ":" in image_url:
            return
        value[-1][0] = "/".join([url_prefix, image_url])  # dont use os.path


def epub_create_back_link_ids(key, value, fmt, meta, modify_ast=True):
    """Adds an id with the suffix _back to each link to be used as anchor for
    possible back links."""
    if fmt != "epub" or not value:
        return
    # add an id to all relative links to jump back to
    elif key == "Link":
        link = value[-1][0]  # last element contains the actual link
        # filter out all absolute links
        if not link or ":" in link:
            return
        if isinstance(link, str):
            # get target and use it as id for the link
            # the virst element of value contains the link id which is empty
            # by default. It is just needed to add the id there.
            # e.g.: <a id="target_id_back" href="target_id">Target</a>
            link_parts = link.split("#", 1)  # split in # once
            if len(link_parts) < 2 or not link_parts[1]:
                return
            value[0][0] = "{}_back".format(link_parts[1])


def epub_create_back_links(key, value, fmt, meta):
    """creates back links for previously collected links.
    meta stores all link IDs so it's possible to add the back links correctly.
    meta structure: { 'chapter': int, 'ids': dict }
    the 'ids' dict contains the ids of the links as key and
    the chapter as key"""
    if fmt != "epub":
        return
    # header from image descriptions are within a RawBlock
    # due to a previous filter
    # before: <p id="image_id", class="header" data-level="2">Image Id</p>
    # after:
    # <p id="image_id", class="header" data-level="2">
    #   <a href="image_id_back">Image Id</a>
    # </p>
    if key == "RawBlock" and value[0] == "html":
        # get the html code from the raw block and parse it
        try:
            xml = minidom.parseString(value[1])
        except ExpatError:
            return  # no valid xml!
        # get the element to be updated
        content = xml.getElementsByTagName("p")
        if not content:
            return
        content = content[0]
        # check if the html code meets the requirements to be an image header
        if not all(x in content.attributes for x in ["id", "class"]):
            return
        anchor_id = content.attributes["id"].value + "_back"
        if not anchor_id in meta["ids"]:
            return
        # get the id to put it later in the link to go back
        # the original link will have a matching id
        # id: 'image_id' -> back link: '#image_id_back'
        link = xml.createElement("a")
        link.setAttribute(
            "href", "ch{:03d}.xhtml#{}".format(meta["ids"][anchor_id], anchor_id),
        )
        text = xml.createTextNode(content.firstChild.toxml())
        link.appendChild(text)
        content.replaceChild(link, content.firstChild)
        return html(content.toxml())


def epub_collect_ids(key, value, fmt, meta):
    """Collects IDs of all headers and links and stores them into meta['ids']
    meta structure: { 'chapter': int, 'ids': dict }
    the 'ids' dict contains the ids of the links as key and
    the chapter as key"""
    if fmt != "epub" or not value:
        return
    # if header level is 1 a new chapter is created for epub. It is needed
    # to count the chapters to create correct links.
    if key == "Header":
        if value[0] == 1:  # first element contains header level (1 == <h1>)
            meta["chapter"] += 1
        # value[1][0] is id in AST for Header
        meta["ids"][value[1][0]] = meta["chapter"]
    elif key == "Link":
        # value[0][0] is id in AST for Link
        meta["ids"][value[0][0]] = meta["chapter"]
    elif key == "RawBlock" and value[0] == "html":
        # get the html code from the raw block and parse it
        try:
            xml = minidom.parseString(value[1])
        except ExpatError:
            return  # no valid xml!
        # get the element to be updated
        content = xml.getElementsByTagName("p")
        if not content:
            return
        content = content[0]
        # check if there is an id
        if not "id" in content.attributes:
            return
        meta["ids"][content.attributes["id"].value] = meta["chapter"]


def epub_unnumbered_toc(key, value, fmt, meta, modify_ast=True):
    """marks all headlines of appendix to be unnumbered in toc."""
    if fmt != "epub" or not value:
        return
    if key == "Header":
        value[1][1].append("unnumbered")  # append unnumbered class to header


def suppress_captions(key, value, fmt, meta, modify_ast=True):
    """Images on a paragraph of its own get a caption, suppress that."""
    if modify_ast and not fmt in ["html", "html5"]:
        return
    if key == "Image":
        # value consists of a list with the last item being a list again; this
        # list contains (path, 'fig:'), if the latter is removed, caption
        # vanishes:
        value[-1][1] = ""


def heading_extractor(key, value, fmt, meta, modify_ast=False):
    """Extract all headings from the JSon AST."""
    if key == "Header":
        # value[0] is the heading level
        return (value[0], pandocfilters.stringify(value))


def file2json_ast(file_name):
    """Read in specified file and return a JSON AST."""
    with open(file_name, encoding="utf-8") as file:
        return load_pandoc_ast(file.read())


def load_pandoc_ast(text):
    """Run pandoc on given document and return parsed JSON AST."""
    command = ["pandoc", "-f", "markdown", "-t", "json"]
    proc = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    data = proc.communicate(text.encode(sys.getdefaultencoding()))
    ret = proc.wait()
    if ret:
        error = "\n".join([e.decode(sys.getdefaultencoding()) for e in data])
        raise SubprocessError(
            " ".join(command), "Pandoc gave error status %s: %s" % (ret, error)
        )
    text = data[0].decode(sys.getdefaultencoding())
    return json.loads(text)


# pylint: disable=too-few-public-methods
class Text:
    """A text chunk."""

    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return "T<%s>" % self.text

    def __str__(self):
        return self.text


# pylint: disable=too-few-public-methods
class Formula:
    """A formula, represented as displaymath by __str__."""

    def __init__(self, formula):
        self.formula = formula

    def __str__(self):
        return "$$%s$$" % self.formula

    def __repr__(self):
        return "F<%s>" % self.__str__()


def get_title(json_ast):
    """Get title from AST"""
    nodes_to_visit = json_ast["blocks"]  # content of document without meta info
    for node in nodes_to_visit:
        if isinstance(node, list):
            nodes_to_visit.extend(node)
        elif isinstance(node, dict):
            # node dictionaries have keys t (type) and c (content)
            if "t" in node and node.get("t") == "Header" and "c" in node:
                if node["c"][0] == 1:  # level 1 heading
                    return pandocfilters.stringify(node["c"])


def convert_formulas(conversion_file, img_dir, ast):
    """This filter extracts all formulas from the given Pandoc AST, converts
    them and replaces their original occurrences with RAW inline HTML.
    For the linking to work, the first argument needs to be the path to the file
    being converted (relative to the current working directory) and the second a
    path to the image directory name and will be in the same directory as the
    file under conversion.
    Example, cwd="some project root":
    >>> convert_formulas('k01/k01.md', 'bilder', my_ast)"""
    formulas = gleetex.pandoc.extract_formulas(ast)
    base_path = os.path.dirname(conversion_file)
    conv = gleetex.cachedconverter.CachedConverter(
        base_path, True, encoding="UTF-8", img_dir=img_dir
    )
    conv.set_replace_nonascii(True)
    try:
        conv.convert_all(formulas)
    except gleetex.cachedconverter.ConversionException as gle:
        raise MathError(
            _("Incorrect formula: {reason}").format(reason=gle.cause),
            gle.formula,
            formula_count=gle.formula_count,
        ) from None

    # an converted image has information like image depth and height and hence
    # the data structure is different
    formulas = [conv.get_data_for(eqn, style) for _p, style, eqn in formulas]
    img_fmt = gleetex.htmlhandling.HtmlImageFormatter(base_path)
    img_fmt.set_replace_nonascii(True)
    # this alters the AST reference, so no return value required
    gleetex.pandoc.replace_formulas_in_ast(img_fmt, ast["blocks"], formulas)
