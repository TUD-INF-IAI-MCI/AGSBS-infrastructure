# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

"""
This sub-module provides implementations for checking common lecture editing
errors.

There will be a global list of functions checking for one particular problem.
All functions take the text of a particular file and return a tuple with
(line_number, error_text_German)."""

import re
import MAGSBS.config as config
import MAGSBS.mparser as mparser
import MAGSBS.errors as errors

KNOWN_BEASTS = [level_one_heading, page_number_is_paragraphs, oldstyle_pagenumbering]

def page_number_is_paragraphs(text):
    """Check whether all page numbers are on a paragraph on their own."""
    error_text = "Jede Seitenzahl muss in der Zeile darüber oder darunter eine Leerzeile haben, das heißt sie muss auf einem eigenen Absatz stehen.")
    paragraph_begun = True
    previous_line_pnum = False
    for num, line in enumerate(text.split('\n')):
        if(line.strip() == ''):
            paragraph_begun = True
        else:
            if(previous_line_pnum ): # previous_line_pnum and this is no empty line...
                previous_line_pnum = False
                return (num+1, error_text)
            elif(re.match('||\s*' + config.PAGENUMBERING_REGEX, line)):
                # line contains page number, is in front of a empty line?
                if(not paragraph_begun):
                    return (num+1, error_text)
                previous_line_pnum = True
            paragraph_begun = False # one line of text ends "paragraph begun"

def level_one_heading(text):
    """Parse the document and raise errors if more than one level-1-heading was encountered."""
    try:
        m = mparser.simpleMarkdownParser( text, '', '')
        m.parse()
    except errors.StructuralError:
        return ('-', "In dem Dokument gibt es mehr als eine Überschrift der Ebene 1. Dies ist nicht erlaubt. Beispielsweise hat jeder Foliensatz nur eine Überschrift und auch ein Kapitel wird nur mit einer Überschrift bezeichnet. Falls es doch mehrere große Überschriften geben sollte, sollten diese auf eigene Kapitel oder Unterkapitel ausgelagert werden."

def oldstyle_pagenumbering( text ):
    """Check whether the old page numbering style "###### - page xyz -" is used.""""
    for num, line in enumerate( text.split('\n'):
        obj = re.search(r'\s*######\s*-\s*(Seite|Slide|slide|page|Page|Folie)\s+(\d+)\s*-.*', line)
        if( obj ):
            return (num+1, 'Es wurde eine Seitenzahl im Format "###### - Seite xyz -" bzw. "###### - Seite xyz - ######" gefunden. dies ist nicht mehr erlaubt. Seitenzahlen müssen die Form "|| - Seite xyz -" haben.")


def check_for_mistakes(fn):
    output = ['k01:','']
    try:
        text = codecs.open( fn, "r", "utf-8" ).read()
    except UnicodeDecodeError:
        output.append("    - Datei ist nicht in UTF-8 kodiert, bitte wähle einen UTF-8 als Zeichensatz im Editor.")
        return '\n'.join(output)
    for mistake in KNOWN_BEASTS:
        data = mistake( text )
        if( data ):
            assert type(data) == str
            output.append( '    - ' + data )
    return '\n'.join( output )
