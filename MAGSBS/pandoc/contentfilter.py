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
import subprocess
import sys

import gleetex
import gleetex.pandoc
import pandocfilters

from .. import config
from ..errors import SubprocessError


html = lambda text: pandocfilters.RawBlock('html', text)

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


def json_ast_filter(doc, action):
    """Walk the specified JSon tree and apply the supplied action. Return all
    values for which "action" returned something (so effictively filter for
    None)"""
    if not isinstance(doc, (dict, list)):
        raise TypeError("A JSON AST is required, got %s" % type(doc))
    result = []
    def go(key, value, fmt, meta):
        res = action(key, value, fmt, meta, modify_ast=False)
        if res:
            result.append(res)
    pandocfilters.walk(doc, go, "", doc['blocks'])
    return result


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
    conv.convert_all(base_path, formulas)
    # an converted image has information like image depth and height and hence
    # the data structure is different
    formulas = [conv.get_data_for(eqn, style) for _p, style, eqn in formulas]
    with gleetex.htmlhandling.HtmlImageFormatter(base_path)  as img_fmt:
        img_fmt.set_exclude_long_formulas(True)
        img_fmt.set_replace_nonascii(True)
        # this alters the AST reference, so no return value required
        gleetex.pandoc.replace_formulas_in_ast(img_fmt, ast['blocks'],
                formulas)

