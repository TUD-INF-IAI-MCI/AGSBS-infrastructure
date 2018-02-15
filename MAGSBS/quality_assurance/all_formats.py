"""Errors which are neither specific to MarkDown nor to LaTeX."""

import os
import gettext
from xml.etree import ElementTree as ET
from .. import config, common
from .meta import MistakeType, Mistake, OnelinerMistake

# importing language versions
try:
    trans = gettext.translation("all_formats", localedir=config.CONFIG_DIR + "/quality_assurance/locale", languages=[config.LANG])
    _ = trans.gettext
except IOError:
    # in case language file is not found
    _ = lambda s: s

class ConfigurationValuesAreAllSet(Mistake):
    """Check whether all configuration options have been set."""
    mistake_type = MistakeType.configuration
    def __init__(self):
        super().__init__()
        self.set_file_types(['dcxml'])

    def worker(self, *args):
        tree = ET.parse(args[0])
        root = tree.getroot()
        def get_tag(node):
            return node.tag[node.tag.find('}') + 1 :]
        for node in root.getchildren():
            if not node.text or 'unknown' in node.text.lower():
                return self.error(_("Fehler in der Konfiguration: Der Wert {} ist "
                    "nicht gesetzt, wodurch die Kopfdaten in den HTML-Dateien "
                    "nicht erzeugt werden können.").format(get_tag(node)),
                    config.get_lnum_of_tag(args[0], node.tag), args[0])

class BrokenUmlautsFromPDFFiles(OnelinerMistake):
    """When copying texts over from PDF's, the umlauts often are unreadable.
    This is because they are at times not saved as an actual umlaut, but rather
    as their respective Latin vowel with a special formatting directive to lift
    an accent or whatever above it. Flag those umlauts, if the editor didn't
    convert them yet to proper umlauts."""
    def __init__(self):
        super().__init__()
        self.set_file_types(["md"])
        # save the malicious sequences as UTF-8 byte arrays
        self.garbled = [b'\xc2\xb4\xc4\xb1', b'\xc2\xa8\xc4\xb1', b'\xc2\xb8c'] + \
                [b'\xc2\xa8' + l  for l in [b'a', b'o', b'u', b's']] + \
                [b'\xc2\xa8 ' + l  for l in [b'a', b'o', b'u', b's']]
        self.garbled = [x.decode('utf-8') for x in self.garbled]

    def check(self, num, line):
        for seq in self.garbled:
            if seq in line:
                return super().error(_("Es wurden inkorrekt dargestellte Umlaute "
                        "gefunden. Dies geschieht oft, wenn Text aus "
                        "PDF-Dateien kopiert wird. Das macht den Text "
                        "allerdings schwer leserlich."), num)

class OnlyCorrectDirectoriesFound(Mistake):
    mistake_type = MistakeType.lecture_root
    def worker(self, *args):
        root = args[0]
        for file in os.listdir(root):
            if any(file.startswith(x) for x in ('bilder', 'inhalt', 'titel',
                    'glossar', 'index', 'kurz' 'taktil', 'copyright',
                    '.lecture_meta')):
                continue
            if not common.is_valid_file(file):
                return self.error(_("Die Datei \"{}\" ist falsch benannt und folgt "
                    "nicht den Namenskonventionen. Dies führt zu einer falschen "
                    "Verwendung der Datei.").format(file), path=root)
