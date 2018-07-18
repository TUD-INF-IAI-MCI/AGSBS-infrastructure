# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016-2018 Sebastian Humenda <shumenda |at|gmx |dot| de>
#pylint: disable=unused-argument
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

import pandocfilters

import gleetex
import gleetex.pandoc

from .. import config
from ..errors import MathError, SubprocessError


html = lambda text: pandocfilters.RawBlock('html', text)

LINK_REGEX = re.compile(r'.*:.*')  # if link contains ":" it is no relative link

#pylint: disable=inconsistent-return-statements
def page_number_extractor(key, value, fmt, meta):
    """Scan all paragraphs for those starting with || to parse it for page
    numbering information."""
    if not (fmt == 'html' or fmt == 'html5'):
        return
    if key == 'Para' and value:
        # find first obj with content (line breaks don't have this)
        text = None
        for obj in value:
            if 'c' in obj:
                text = obj['c']
                break
        if text is None:
            return # no content in Paragraph - ignore
        # first chunk of paragraph must be str and contain '||'
        if isinstance(text, str) and text.startswith('||'):
            text = pandocfilters.stringify(value) # get whole text of page number
            pnum = config.PAGENUMBERING_PATTERN.search(text)
            if pnum:
                # strip the first ||
                text = text[2:].lstrip().rstrip()
                return html('<p><span id="p{0}">{1}</span></p>'.format(
                        pnum.groups()[1], text))


#pylint: disable=inconsistent-return-statements
def epub_page_number_extractor(key, value, fmt, meta):
    """Scan all paragraphs for those starting with || to parse it for page
    numbering information."""
    if not (fmt == 'epub'):
        return
    if key == 'Para' and value:
        # find first obj with content (line breaks don't have this)
        text = None
        for obj in value:
            if 'c' in obj:
                text = obj['c']
                break
        if text is None:
            return # no content in Paragraph - ignore
        # first chunk of paragraph must be str and contain '||'
        if isinstance(text, str) and text.startswith('||'):
            text = pandocfilters.stringify(value) # get whole text of page number
            pnum = config.PAGENUMBERING_PATTERN.search(text)
            if pnum:
                # strip the first ||
                text = text[2:].lstrip().rstrip()
                return html('<p class="pagebreak"><span id="p{0}">{1}</span></p>'.format(
                        pnum.groups()[1], text))


def html_link_converter(key, value, fmt, meta, modify_ast=True):
    """Scan all links and append change to .html for all relative links."""
    if not (fmt == 'html' or fmt == 'html5'):
        return
    if key == 'Link' and value:
        link = value[-1][0]
        if not link or LINK_REGEX.match(link):
            return
        if isinstance(link, str):
            link_parts = link.split('#', 1)  # split in # once
            if not link_parts[0]:
                return
            link_parts[0] = os.path.splitext(link_parts[0])[0] + '.html'
            value[-1][0] = '#'.join(link_parts)


def epub_link_converter(key, value, fmt, meta, modify_ast=True):
    """Scan all links and append change to .html for all relative links."""
    if not 'epub':
        return
    if key == 'Header' and value:
        if value[0] == 1:
            meta['chapter'] +=1
            return
    if key == 'Link' and value:
        link = value[-1][0]
        if not link or LINK_REGEX.match(link):
            return
        if isinstance(link, str):
            link_parts = link.split('#', 1)  # split in # once
            if not link_parts[0]:
                return
            link_parts[0] = 'ch{:03d}.xhtml'.format(meta['chapter'])
            value[-1][0] = '#'.join(link_parts)


def epub_convert_header_ids(key, value, fmt, url_prefix, modify_ast=True):
    """Prepends all header IDs with the chapter and updates all links to images
    with the image_ prefix."""
    if key == 'Header' and value:
        value[1][0] = '_'.join([url_prefix, value[1][0]])
    if key == 'Link' and value:
        link = value[-1][0]
        if not link or LINK_REGEX.match(link):
            return
        if isinstance(link, str):
            link_parts = link.split('#', 1)  # split in # once
            if not link_parts[1]:
                return
            link_parts[1] = '_'.join([url_prefix, link_parts[1]])
            if (isinstance(value[1][0], dict) and value[1][0]['t']
                    and value[1][0]['t'] == 'Image'):
                link_parts[1] = 'image_{}'.format(link_parts[1])
            value[-1][0] = '#'.join(link_parts)


def epub_convert_image_header_ids(key, value, fmt, meta, modify_ast=True):
    """prepends all image header IDs with 'image_'"""
    if key == 'Header' and value:
        value[1][0] = 'image_{}'.format(value[1][0])


def epub_remove_images_from_toc(key, value, fmt, meta):
    """Scan all paragraphs for those starting with || to parse it for page
    numbering information."""
    if fmt != 'epub':
        return
    if key == 'Header' and value:
        # find first obj with content (line breaks don't have this)
        text = None
        header_level = 0
        _id = ''
        for obj in value:
            if isinstance(obj, int):
                header_level = obj
            elif isinstance(obj, list):
                for inner_obj in obj:
                    if isinstance(inner_obj, str):
                        _id = inner_obj
                    elif isinstance(inner_obj, dict):
                        if 'c' in inner_obj:
                            text = inner_obj['c']
        if text is None or header_level == 0 or _id == '':
            return # no valid content
        if isinstance(text, str):
            text = pandocfilters.stringify(value)
            return html(
                '<p id="{0}" class="{1}" data-level="{2}">{3}</p>'.format(
                    _id,
                    'header pagebreak' if header_level == 1 else 'header',
                    header_level,
                    text
                )
            )
 

def epub_update_image_location(key, value, fmt, url_prefix, modify_ast=True):
    """Updates all image locations so that pandoc can find and add them
    correctly for epub."""
    if fmt != 'epub':
        return
    if key == 'Image' and value:
        image_url = value[-1][0]
        if not image_url or image_url[0] == '/' or LINK_REGEX.match(image_url):
            return
        value[-1][0] = '/'.join([url_prefix, image_url])  # dont use os.path


def epub_collect_link_targets(key, value, fmt, meta, modify_ast=True):
    """Collects all links via meta and appends an id to be used as anchor for
    back buttons."""
    if not 'epub':
        return
    if key == 'Header' and value:
        if value[0] == 1:
            meta['chapter'] +=1
            return
    if key == 'Link' and value:
        link = value[-1][0]
        if not link or LINK_REGEX.match(link):
            return
        if isinstance(link, str):
            link_parts = link.split('#', 1)  # split in # once
            if not link_parts[1]:
                return
            meta['ids'][link_parts[1]] = meta['chapter']
            value[0][0] = '{}_back'.format(link_parts[1])


def epub_create_back_links(key, value, fmt, meta):
    """creates back links for previously collected links."""
    if not 'epub':
        return
    if key == 'RawBlock' and value[0] == 'html':
        xml = minidom.parseString(value[1])
        content = xml.getElementsByTagName("p")
        if not content:
            return
        content = content[0]
        if not all(x in content.attributes for x in ['id', 'class']):
            return
        if not content.attributes['id'].value in meta['ids']:
            return
        anchor_id = content.attributes['id'].value
        link = xml.createElement('a')
        link.setAttribute('href', 'ch{:03d}.xhtml#{}_back'.format(
            meta['ids'][anchor_id], anchor_id))
        text = xml.createTextNode(content.firstChild.toxml())
        link.appendChild(text)
        content.replaceChild(link, content.firstChild)
        return html(content.toxml())


def suppress_captions(key, value, fmt, meta, modify_ast=True):
    """Images on a paragraph of its own get a caption, suppress that."""
    if modify_ast and not fmt in ['html', 'html5']:
        return
    if key == 'Image':
        # value consists of a list with the last item being a list again; this
        # list contains (path, 'fig:'), if the latter is removed, caption
        # vanishes:
        value[-1][1] = ''

def heading_extractor(key, value, fmt, meta, modify_ast=False):
    """Extract all headings from the JSon AST."""
    if key == 'Header':
        # value[0] is the heading level
        return (value[0], pandocfilters.stringify(value))


def file2json_ast(file_name):
    """Read in specified file and return a JSON AST."""
    with open(file_name, encoding='utf-8') as file:
        return load_pandoc_ast(file.read())

def load_pandoc_ast(text):
    """Run pandoc on given document and return parsed JSON AST."""
    command = ['pandoc', '-f', 'markdown', '-t', 'json']
    proc = subprocess.Popen(command, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = proc.communicate(text.encode(sys.getdefaultencoding()))
    ret = proc.wait()
    if ret:
        error = '\n'.join([e.decode(sys.getdefaultencoding())
                for e in data])
        raise SubprocessError(' '.join(command),
        "Pandoc gave error status %s: %s" % (ret, error))
    text = data[0].decode(sys.getdefaultencoding())
    return json.loads(text)


#pylint: disable=too-few-public-methods
class Text:
    """A text chunk."""
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'T<%s>' % self.text
    def __str__(self):
        return self.text

#pylint: disable=too-few-public-methods
class Formula:
    """A formula, represented as displaymath by __str__."""
    def __init__(self, formula):
        self.formula = formula
    def __str__(self):
        return '$$%s$$' % self.formula
    def __repr__(self):
        return 'F<%s>' % self.__str__()


def get_title(json_ast):
    nodes_to_visit = json_ast['blocks'] # content of document without meta info
    for node in nodes_to_visit:
        if isinstance(node, list):
            nodes_to_visit.extend(node)
        elif isinstance(node, dict):
            # node dictionaries have keys t (type) and c (content)
            if 't' in node and node.get('t') == 'Header' and 'c' in node:
                if node['c'][0] == 1: # level 1 heading
                    return pandocfilters.stringify(node['c'])

def convert_formulas(base_path, ast):
    """This filter extracts all formulas from the given Pandoc AST, converts
    them and replaces their original occurrences with RAW inline HTML."""
    formulas = gleetex.pandoc.extract_formulas(ast)
    conv = gleetex.cachedconverter.CachedConverter(base_path, True,
            encoding="UTF-8")
    conv.set_replace_nonascii(True)
    try:
        conv.convert_all(base_path, formulas)
    except gleetex.cachedconverter.ConversionException as gle:
        raise MathError(_('Incorrect formula: {reason}').format(
                reason=gle.cause), gle.formula,
                formula_count=gle.formula_count) from None

    # an converted image has information like image depth and height and hence
    # the data structure is different
    formulas = [conv.get_data_for(eqn, style) for _p, style, eqn in formulas]
    with gleetex.htmlhandling.HtmlImageFormatter(base_path)  as img_fmt:
        img_fmt.set_exclude_long_formulas(True)
        img_fmt.set_replace_nonascii(True)
        # this alters the AST reference, so no return value required
        gleetex.pandoc.replace_formulas_in_ast(img_fmt, ast['blocks'],
                formulas)
