#pylint: disable=redefined-builtin,unused-argument
# Pylint is right about the errors above, but the additional arguments e.g.
# where introduced to be compatible with the pandocfilters package.
"""
This module provides some extensions to the python-pandoc API as well as a few
custom filters for the extended version of MarkDown.
Additionally, a parser is introduced for documents with LaTeX formulas. This one
pre-parses a document and changes all inline equations to displaymath equations.
This way Pandoc preserves the line breaks which ware curcial for alternative
image descriptions.
"""

import pandocfilters
import json
import sys, subprocess, re
from . import config
from . import datastructures
from .errors import StructuralError


def html(x):
    """html(x)
The string x is transformed into an RawBlock for Pandoc's usage."""
    assert type(x) == str
    return pandocfilters.RawBlock('html', x)

def join_para(chunks):
    """join_para(chunks)
Pandoc's json is recursively nested. To search for a particular string (like we
        do for page numbers), one has to join all the nested text chunks."""
    str = ''
    for chunk in chunks:
        if(type(chunk['c']) == list and chunk['t'] == 'Space'):
            str += ' '
        else:
            str += chunk['c']
    return str

def generate_link(ltext, id):
    """GEnerate the HTML paragraph with the HTML anchor and the Text."""
    return '<p><a name="%s"/>%s</p>' % (id, ltext)

def has_math(key, value, format, meta, modify_ast=False):
    """Return True, if a math environment has been found."""
    if( key.lower() == "math" ):
        return True


def page_number_extractor(key, value, format, meta, modify_ast=True):
    """Scan all paragraphs for those starting with || to parse it for page
numbering information."""
    if(modify_ast):
        if(not (format == 'html' or format == 'html5')):
            return
    if key == 'Para':
        if len(value)>0:
            text = value[0]['c']
            if(type(text) == str):
                if(text.startswith('||')):
                    text = pandocfilters.stringify( value )
                    if(re.search(config.PAGENUMBERING_REGEX, text.lower())):
                        # strip the first ||
                        text = text[2:]
                        id = datastructures.gen_id( text )
                        if(modify_ast):
                            return html(generate_link(text, id))
                        else:
                            return (text, id)

def suppress_captions(key, value, format, meta, modify_ast=True):
    """Images on a paragraph of its own get a caption, suppress that."""
    if modify_ast and not format in ['html', 'html5']:
        return
    if key == 'Image':
        # value consists of a list with two items, second contains ('bildpath',
                # x) where x is either 'fig' for a proper figure with caption or
        # '' (which is what is desired)
        value[1][1] = ''

def heading_extractor(key, value, format, meta, modify_ast=False):
    """Extract all headings from the JSon AST."""
    if(key == 'Header'):
        # value[0] is the heading level
        return (value[0], pandocfilters.stringify( value ))


def jsonfilter(doc, action, format='html'):
    """Run a filter on the given json (parameter doc) with the specified action
    (parameter action). Return the altered structure (effectively a copy).
    The action argument is effectively a method:  The argument is a function
    action(key, value, format, meta), where key is the type of the pandoc object
    (e.g. 'Str', 'Para'),
    value is the contents of the object (e.g. a string for 'Str',
    a list of inline elements for 'Para'), format is the target
    output format (which will be taken for the first command line
    argument if present), and meta is the document's metadata.
    If the function returns None, the object to which it applies
    will remain unchanged.  If it returns an object, the object will
    be replaced.  If it returns a list, the list will be spliced in to
    the list to which the target object belongs.  (So, returning an
    empty list deletes the object.)
    """
    altered = pandocfilters.walk(doc, action, format, doc[0]['unMeta'])
    return altered


def run_pandoc(text):
    """Return pandoc and return Pandoc AST."""
    proc = subprocess.Popen(['pandoc', '-f','markdown', '-t','json'], stdin=\
            subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = proc.communicate( text.encode( sys.getdefaultencoding() ) )
    ret = proc.wait()
    if(ret):
        print('\n'.join([e.decode( sys.getdefaultencoding() )
                for e in data]))
        raise OSError("Pandoc gave error status %s." % ret)
    text = data[0].decode( sys.getdefaultencoding() )
    return text


def pandoc_ast_parser(text, action):
    """Walk the specified JSon tree and apply the supplied action."""
    result = []
    doc = json.loads( text )
    def go(key, value, format, meta):
        res = action(key, value, format, meta, modify_ast=False)
        if(res):
            result.append( res )
    pandocfilters.walk(doc, go, "", doc[0]['unMeta'])
    return result


class Text:
    """A text chunk."""
    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return 'T<%s>' % self.text
    def __str__(self):
        return self.text

class Formula:
    """A formula, represented as displaymath by __str__."""
    def __init__(self, formula):
        self.formula = formula
    def __str__(self):
        return '$$%s$$' % self.formula
    def __repr__(self):
        return 'F<%s>' % self.__str__()

class InlineToDisplayMath:
    """Parse math formulas and modify them to be always displaymath so that
    Pandoc will preserve white space."""
    def __init__(self, document):
        self.__document = document
        self.__pieces = []

    def is_followed_by_dollar_sign(self, pos, string):
        """Return true if the character after the one at position ''pos`` is
        also a dollar character."""
        if pos >= (len(string)-1):
            return False # is already at end of string
        # we can now expect that there's a character after string[pos]
        return string[pos+1] == '$'

    def parse(self):
        """Parse the document string into chunks of Text and Formula's.
Algorithm (ignoring $$-enclosed formulas); the position in the text is
implicitely memorized.

1.  Find dollar. If followed by dollar, tread the text before and the two text
    dollars as text and save it. Continue on this vey same step.
    - if no dollar found: 5.
2.  Find the matching dollar sign.
3.  Text between the two dollars is added as Formula() to self.__pieces.
4.  Position is updated, start from one.
5.  Save current position until end as Text() and exit.
"""
        current_pos = 0
        while current_pos < len(self.__document):
            dollar = self.__document[current_pos:].find('$')
            if dollar == -1: # no dollar found, end
                self.__pieces.append(Text(self.__document[current_pos:]))
                break
            if self.is_followed_by_dollar_sign(current_pos+dollar, self.__document):
                # ignore $$ environments, they are already like desired; save
                # everything til the $$ and those as well and "continue" to
                # search on
                self.__pieces.append(Text(self.__document[current_pos:current_pos
                    + dollar + 2]))
                current_pos += (dollar + 2)
                continue

            begin = dollar + current_pos + 1
            # save text before formula
            self.__pieces.append(Text(self.__document[current_pos:begin-1]))


            # find closing dollar(s)
            dollar = self.__document[begin+1:].find('$') # +1 to ignore current char
            if dollar == -1: # opening dollar, but no closing
                raise StructuralError("At position %d an opening " % begin +
                        "math environment was found that was never closed!")
            end = dollar + begin + 1
            # add math formula to chunks
            self.__pieces.append(Formula(self.__document[begin:end]))
            if self.is_followed_by_dollar_sign(end, self.__document):
                raise StructuralError("Parser encountered a closing $$ " +
                        "environment, although that should never happen. " +
                        "Possibly a bug.")
            current_pos = end + 1 # ignore dollar sign

    def get_document(self):
        """Return the document as a string."""
        return ''.join(map(str, self.__pieces))


