# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016-2017 Sebastian Humenda <shumenda |at|gmx |dot| de>
#pylint: disable=unused-argument
"""
This module provides some extensions to the python-pandoc API as well as a few
custom filters for the extended version of MarkDown.
Additionally, a parser is introduced for documents with LaTeX formulas. This one
pre-parses a document and changes all inline equations to displaymath equations.
This way Pandoc preserves the line breaks which ware curcial for alternative
image descriptions.
"""

import json
import subprocess
import sys
import pandocfilters
from .. import config
from ..errors import SubprocessError


html = lambda text: pandocfilters.RawBlock('html', text)


def join_para(chunks):
    """join_para(chunks)
Pandoc's json is recursively nested. To search for a particular string (like we
        do for page numbers), one has to join all the nested text chunks."""
    str = ''
    for chunk in chunks:
        if isinstance(chunk['c'], list) and chunk['t'] == 'Space':
            str += ' '
        else:
            str += chunk['c']
    return str

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

def heading_extractor(key, value, format, meta, modify_ast=False):
    """Extract all headings from the JSon AST."""
    if(key == 'Header'):
        # value[0] is the heading level
        return (value[0], pandocfilters.stringify( value ))


def file2json_ast(file_name):
    """Read in specified file and return a JSON AST."""
    with open(file_name, encoding='utf-8') as f:
        return text2json_ast(f.read())

def text2json_ast(text):
    """Run pandoc and return parsed JSON AST."""
    command = ['pandoc', '-f','markdown', '-t','json']
    proc = subprocess.Popen(command, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = proc.communicate(text.encode(sys.getdefaultencoding()))
    ret = proc.wait()
    if ret:
        error = '\n'.join([e.decode( sys.getdefaultencoding() )
                for e in data])
        raise SubprocessError(' '.join(command),
        "Pandoc gave error status %s: %s" % (ret, error))
    text = data[0].decode( sys.getdefaultencoding() )
    return json.loads(text)


def json_ast_filter(doc, action):
    """Walk the specified JSon tree and apply the supplied action. Return all
    values for which "action" returned something (so effictively filter for
    None)"""
    if not isinstance(doc, (dict, list)):
        raise TypeError("A JSON AST is required, got %s" % type(doc))
    result = []
    def go(key, value, format, meta):
        res = action(key, value, format, meta, modify_ast=False)
        if(res):
            result.append( res )
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
    nodes_to_visit = json_ast['blocks'] # content of document without meta information
    for node in nodes_to_visit:
        if isinstance(node, list):
            nodes_to_visit.extend(node)
        elif isinstance(node, dict):
            # node dictionaries have keys t (type) and c (content)
            if 't' in node and node.get('t') == 'Header' and 'c' in node:
                if node['c'][0] == 1: # level 1 heading
                    return pandocfilters.stringify(node['c'])

