"""Errors which are neither specific to MarkDown nor to LaTeX."""

import os
from xml.etree import ElementTree as ET
from .. import errors
from .meta import MistakeType, Mistake, OnelinerMistake, MistakePriority

class ConfigurationValuesAreAllSet(Mistake):
    """Check whether all configuration options have been set."""
    def __init__(self):
        super().__init__()
        self.set_type(MistakeType.need_configuration)
        self.set_file_types(['dcxml'])

    def worker(self, *args):
        try:
            tree = ET.parse(args[0])
        except ET.ParseError as e:
            # it is garanteed that mistkerl is in the cwd, so get full path
            full_path = os.path.join(os.getcwd(), args[0])
            raise errors.ConfigurationError("Error while parsing %s: %s" \
                    % (full_path, e.args[0]))
        root = tree.getroot()
        def getTag(node):
            return node.tag[node.tag.find('}') + 1 :]
        for node in root:
            if 'unknown' in node.text.lower():
                return self.error('Fehler in der Konfiguration: Der Wert ' + \
                        getTag(node) + ' ist nicht gesetzt, wodurch die ' + \
                        'Kopfdaten in den HTML-Dateien ' +
                        'nicht erzeugt werden können. Dies ist allerdings eine' +
                        ' Vorgabe.')

class BrokenUmlautsFromPDFFiles(OnelinerMistake):
    """When copying texts over from PDF's, the umlauts often are unreadable.
    This is because they are at times not saved as an actual umlaut, but rahter
    as their respective Latin vowel with a special formatting directive to lift
    an accent or whatever above it. Flag those umlauts, if the editor didn't
    convert them yet to proper umlauts."""
    def __init__(self):
        super().__init__()
        self.set_file_types(["md"])
        self.set_priority(MistakePriority.critical)
        # save the malicious sequences as UTF-8 byte arrays
        self.garbled = [b'\xc2\xb4\xc4\xb1', b'\xc2\xa8\xc4\xb1', b'\xc2\xb8c'] + \
                [b'\xc2\xa8' + l  for l in [b'a', b'o', b'u', b's']] + \
                [b'\xc2\xa8 ' + l  for l in [b'a', b'o', b'u', b's']]
        self.garbled = [x.decode('utf-8') for x in self.garbled]

    def check(self, num, line):
        for seq in self.garbled:
            if seq in line:
                super().error("Es wurden inkorrekt dargestellte Umlaute "
                        "gefunden. Dies geschieht oft, wenn Text aus "
                        "PDF-Dateien kopiert wird. Diese kaputten Umlaute "
                        "machen den Text allerdings schwer leserlich.", num)

