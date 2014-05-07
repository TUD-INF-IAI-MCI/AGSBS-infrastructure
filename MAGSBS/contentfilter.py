from pandocfilters import *
import pandocfilters
import sys, re
import MAGSBS


def html(x):
    """html(x)
The string x is transformed into an RawBlock for Pandoc's usage."""
    assert type(x) == str
    return RawBlock('html', x)

def join_para(chunks):
    """join_para(chunks)
Pandoc's json is recursively nested. To search for a particular string (like we
        do for page numbers), one has to join all the nested text chunks."""
    str = ''
    for chunk in paras:
        if(type(chunk['c']) == list and chunk['t'] == 'Space'):
            str += ' '
        else:
            str += chunk['c']
    return str

def generate_link(text):
    """GEnerate the HTML paragraph with the HTML anchor and the Text."""
    # strip the first ||
    text = text[2:]
    id = MAGSBS.datastructures.gen_id( text )
    return '<p><a name="%s"/>%s</p>' % (id, text)


def alterparagraphs(key, value, format, meta):
    """Scan all paragraphs for those starting with || to parse it for page
numbering information."""
    if(not (format == 'html' or format == 'html5')):
        return
    elif(key == 'Para'):
        if(len(value)>0):
            text = value[0]['c']
            if(type(text) == str):
                if(text.startswith('||')):
                    text = join_para( value )
                    if(re.search( MAGSBS.config.PAGENUMBERING_REGEX,
                            text.lower())):
                        return html(generate_link(text))

def jsonfilter(text, format='html'):
    """NOTE: this is a copy from pandocfilters, it uses also the infrastructure
    of this module, but doesn't read from stdin (but from an argument) and
    doesn't write to stdout.
    Converts an action into a filter that reads a JSON-formatted
    pandoc document from stdin, transforms it by walking the tree
    with the action, and returns a new JSON-formatted pandoc document
    to stdout.  The argument is a function action(key, value, format, meta),
    where key is the type of the pandoc object (e.g. 'Str', 'Para'),
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
    doc = json.loads( text )
    altered = pandocfilters.walk(doc, alterparagraphs, format, [])#doc[0]['unMeta'])
    return json.dumps( altered )

