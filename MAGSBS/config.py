"""Handle lecture and conversion configuration. The configuration is XML in the
dublincore format (at least roughly) and has a separate namespace for
MAGSBS-specific extensions.
"""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2017 Sebastian Humenda <shumenda |at| gmx |dot| de>
#pylint: disable=line-too-long,too-few-public-methods

import enum
import datetime
from distutils.version import StrictVersion
import os
import re
import sys
import gettext
import locale
import xml.etree.ElementTree as ET
from xml.dom import minidom
from . import common
from .errors import ConfigurationError
from . import roman
from os.path import dirname

VERSION = StrictVersion('0.7.0')

## default values
CONF_FILE_NAME = ".lecture_meta_data.dcxml"

# all tokens which can mark a start of the page
PAGENUMBERINGTOKENS = ['slide', 'folie', 'seite', 'page']
PAGENUMBERINGTOKENS += [t.title() for t in PAGENUMBERINGTOKENS] # recognize with both case spellings

# regular expression to recognize page numbers, includes both arabic and roman
# numbers
roman_number_regex = roman.roman_numeral_pattern_string.strip().lstrip('^').rstrip('$')
PAGENUMBERING_PATTERN = re.compile(r'''
        # recognize all different languages which are supported for the words
        # "slide" and "page"
        -\s*(%s)\s+
        (\d+|%s)\s*- # arabic or roman numbers
        ''' % ('|'.join(PAGENUMBERINGTOKENS), roman_number_regex),
        re.VERBOSE)


# importing language versions
# TODO: this could be a function that is called during initialization
LANG = locale.getdefaultlocale()[0][:2] # detects the language of the system
CONFIG_DIR = dirname(dirname(os.path.realpath(__file__))) + "/locale" # get the main directory of the system

# generate mo files (somewhere in the user's space)
# TODO: generation of mo files
"""
Code from: https://stackoverflow.com/questions/34070103/how-to-compile-po-gettext-translations-in-setup-py-python-script
PO_FILES = 'translations/locale/*/LC_MESSAGES/app_name.po'

def create_mo_files():
    mo_files = []
    prefix = 'app_name'

    for po_path in glob.glob(str(pathlib.Path(prefix) / PO_FILES)):
        mo = pathlib.Path(po_path.replace('.po', '.mo'))

        subprocess.run(['msgfmt', '-o', str(mo), po_path], check=True)
        mo_files.append(str(mo.relative_to(prefix)))
"""

# load the mo file
# TODO load generated mo files instead of pre-generated one
try:
    trans = gettext.translation("messages", localedir=CONFIG_DIR , languages=[LANG])
    _ = trans.gettext
except IOError:
    # in case language file is not found
    _ = lambda s: s


def get_semester():
    """Guess the current semester from the current time. Semesters are based on
    the German university system."""
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year
    if month < 3 or month >= 9:
        year = (year-1 if month < 3 else year) # WS starts at end of last year
        return 'WS {}/{}'.format(year, year+1)
    else:
        return 'SS {}'.format(year)


def get_lnum_of_tag(path, tag):
    """Find (xml) `tag` in `path` and return its line number. This function
    assumes one tag per line, as it is written by the LectureMetaData.write()
    method."""
    tag = tag.replace('{http://purl.org/dc/elements/1.1}', ''). \
            replace('{http://elvis.inf.tu-dresden.de}', 'MAGSBS:')
    with open(path, 'r', encoding='utf-8') as f:
        for lnum, line in enumerate(f.readlines()):
            if tag in line:
                return lnum + 1

class MetaInfo(enum.Enum):
    AppendixPrefix = 'MAGSBS:appendixPrefix'
    Editor = 'dc:creator'
    Format = 'dc:format'
    GenerateToc = 'MAGSBS:generateToc'
    Institution = 'dc:publisher'
    Language = 'dc:language'
    LectureTitle = 'dc:title'
    PageNumberingGap = 'MAGSBS:pageNumberingGap'
    Rights = 'dc:rights'
    SemesterOfEdit = 'dc:date'
    Source = 'dc:source'
    SourceAuthor = 'MAGSBS:sourceAuthor'
    TocDepth = 'MAGSBS:tocDepth'
    WorkingGroup = 'dc:contributor'

class LectureMetaData(dict):
    """The lecture conversion needs meta data which is then embedded into the HTML
document. Those fields are e.g. source, editor, etc.

This class provides a writer and also a reader for those files. A usage scenario
could look like this:

l = LectureMetaData("directory")
l.read()
l[MetaInfo.Editor] = 'Max Mustermann'
l.write()

In the directory "directory", this class looks for a configuration file with
meta data. It is read. If none is present, this class will silently assume the
default values.

The class behaves like a dictionary, but only accepts keys of type MetaInfo.

Please note: you should not use this class, except if you can make sure that
exactly one instance at a time exists for a given path. Use the ConfFactory
instead.
"""
    DEFAULTS = { MetaInfo.WorkingGroup: 'AG SBS', MetaInfo.Language: 'de',
            MetaInfo.Institution: 'TU Dresden',
            MetaInfo.Rights: 'Access limited to members',
            MetaInfo.Format: 'html', MetaInfo.TocDepth: 5,
            MetaInfo.AppendixPrefix: 0, MetaInfo.PageNumberingGap: 5,
            MetaInfo.GenerateToc: 1}
    NUMERICAL = (MetaInfo.TocDepth, MetaInfo.AppendixPrefix,
                MetaInfo.PageNumberingGap, MetaInfo.GenerateToc)

    def __init__(self, file_path, version=VERSION):
        """Set default values."""
        super().__init__()
        self.__path = file_path
        for key in MetaInfo:
            if key in self.NUMERICAL:
                super().__setitem__(key, 0)
            else:
                super().__setitem__(key, 'Unknown')
        for key, value in LectureMetaData.DEFAULTS.items():
            self[key] = value
        if self[MetaInfo.Editor] == 'Unknown':
            # guess editor
            if 'win32' in sys.platform or 'wind' in sys.platform:
                import getpass
                self[MetaInfo.Editor] = getpass.getuser()
            else: # on unixoids, use pwd
                import pwd
                editor = pwd.getpwuid(os.getuid())[4]
                # on some systems, real name end with commas, strip those
                while editor and not editor[-1].isalpha():
                    editor = editor[:-1]
                self[MetaInfo.Editor] = editor
        self[MetaInfo.SemesterOfEdit] = get_semester() # guess current semester
        self.__changed = False
        self.__version = version

    def write(self):
        """Write back configuration, if it was changed."""
        if not self.__changed:
            return
        root = ET.Element('metadata')
        root.attrib['xmlns:dc'] = 'http://purl.org/dc/elements/1.1'
        root.attrib['xmlns:MAGSBS'] = 'http://elvis.inf.tu-dresden.de'
        for key, value in self.items():
            if key.value.startswith('MAGSBS:'):
                c = ET.SubElement(root, key.value)
            else:
                c = ET.SubElement(root, key.value)
            c.text = str(value)
        # add version number
        c = ET.SubElement(root, 'MAGSBS:version')
        c.text = str(self.__version)
        # re-format XML
        out = minidom.parseString('<?xml version="1.0" encoding="UTF-8"?>' + \
                ET.tostring(root, encoding="unicode")
                ).toprettyxml(indent="  ", encoding="utf-8")
        with open(self.__path, 'wb') as f:
            f.write(out)

    def get_path(self):
        return self.__path

    def read(self):
        normalize_keys = lambda k: k.split(':')[-1] # strip namespace
        xmlkey2dict = {normalize_keys(key.value): key for key in MetaInfo}

        with open(self.__path, 'r', encoding='utf-8') as data_source:
            root = ET.fromstring(data_source.read())
            normalize_tag = lambda x: (x[x.find('}')+1:]  if '}' in x else x)
            version_read = False
            for child in root:
                tag = normalize_tag(child.tag)
                if tag == 'version':
                    version_read = True
                    self.__check_for_version(self.__path, child.text)
                elif not tag in xmlkey2dict:
                    raise ConfigurationError(("Unknown key %s, skipping. Please"
                        " update the configuration and rerun the operation.") % tag,
                            path=self.__path)
                else:

                    key = xmlkey2dict[tag] # get enum
                    value = child.text
                    if key in self.NUMERICAL:
                        try:
                            value = int(value)
                        except ValueError:
                            raise ConfigurationError("Option " + tag +
                                "has invalid,  non-numerical value of " +
                                value, self.__path)
                    try:
                        self[key] = value
                    except IndexError:
                        msg = 'Malformed XML in configuration: ' + ET.dump(child)
                        raise ConfigurationError(msg, self.__path)
            if not version_read:
                self.__check_for_version(self.__path, '0.1')
        self.__changed = False

    def __check_for_version(self, path, value):
        """Check whether version exists and fail otherwise."""
        try:
            version = StrictVersion(value)
        except ValueError:
            raise ConfigurationError("invalid version number: " + repr(value),
                    path, line=get_lnum_of_tag(path, 'MAGSBS:version'))
        # check whether the first two digits of the version numbers match;
        # that'll tread bug fix releases the same
        if self.__version.version[:2] == version.version[:2]:
            if self.__version.version[-1] < version.version[-1]: # a newer bug fix release is available
                common.WarningRegistry().register_warning(("A newer version of "
                    "Matuc is available: ") + str(version))
            # do nothing
        elif version < self.__version:
            self.__changed = True
            self.write() # overwrite version number in configuration which is too old
        else:
            raise ConfigurationError(("matuc is too old, the configuration "
                "requires version {}, but version {} is running.").format(version, VERSION),
                path, get_lnum_of_tag(path, 'MAGSBS:version'))

    def __setitem__(self, k, v):
        if not isinstance(k, MetaInfo):
            raise ConfigurationError("Keys can only be of type MetaInfo, got " + \
                    str(type(k)), path=self.get_path())
        if k in self.NUMERICAL:
            try:
                v = int(v)
            except ValueError:
                raise ConfigurationError(("Option {} couldn't be converted to "
                    "a number: {}").format(k, v), self.__path)
        if k not in self.keys():
            raise ConfigurationError("the key %s is unknown" % k, self.__path)
        super().__setitem__(k, v)
        self.__changed = True

    def __eq__(self, other):
        if not isinstance(other, LectureMetaData):
            return False
        # xor will filter the symetric diff. of both dictionaries; they are
        # equals if there are not elements
        has_elements = set(self.items()) ^ set(other.items())
        return not has_elements


@common.Singleton
class ConfFactory:
    """
Factory which returns the corresponding instance of a user configuration. They
are however not thread-safe.
The "corresponding" configuration (object) is selected using first the root
configuration and then, if present, the corresponding subdirectory configuration
(if in a subdirectory).
"""
    def __init__(self):
        self._instances = {}

    def get_conf_instance(self, path):
        """get_conf_instance(path)
        Get a configuration object representing a configuration for a given
        path.
        If no configuration is found the method searches in the directories
        above, as long as it can determine whether it's still in the lecture.
        If no configuration is found, the default configuration object is
        returned."""
        if path is None:
            raise ValueError("Path expected")
        elif path == '':
            path = os.getcwd()
        if not os.path.exists(path):
            raise ConfigurationError("specified path doesn't exist", path)
        elif os.path.isfile(path):
            path = os.path.dirname(path)
        conf_path = os.path.abspath(os.path.join(path, CONF_FILE_NAME))
        if conf_path in self._instances.keys():
            return self._instances[conf_path]
        else:
            # check directory above if in a subdirectory of a lecture
            if not os.path.exists(conf_path) and not common.is_lecture_root(path):
                dir_above = os.path.split(os.path.abspath(path))[0]
                if common.is_lecture_root(dir_above):
                    conf_path = os.path.join(dir_above, CONF_FILE_NAME)
            try:
                self._instances[conf_path] = LectureMetaData(conf_path)
                if os.path.exists(conf_path):
                    self._instances[conf_path].read()
            except UnicodeDecodeError:
                raise ValueError(conf_path + ": File must be encoded in UTF-8")
            except ET.ParseError as e:
                raise ConfigurationError("Configuration errorneous: " + str(e),
                        conf_path, e.position[0])
        return self._instances[conf_path]

    def get_conf_instance_safe(self, path):
        """Same as get_conf_instance, but returns a default configuration object
        if configuration could not be read due to an underlying error. This
        method should be used with care, it might swallow errors. It is intended
        to be used with the Mistkerl checkers."""
        try:
            return self.get_conf_instance(path)
        except (ET.ParseError, ConfigurationError, OSError, UnicodeDecodeError):
            return LectureMetaData(path)


class Translate:
    """t = Translate()
    t.set_language(lang)
    _ = t.get_translation
    print(_("translate me"))

    Custom translation class which can alter the language according to the set
    language. set_language raises ValueError if the language is unknown."""
    supported_languages = ['de', 'fr', 'en']
    def __init__(self):
        self.en_fr = {
            "page": "page", "slide": "diapositive",
            'preface':'introduction',   'appendix':'appendice',
            'table of contents':'table des matières',
            'chapters':'chapitres',
            'image description of image':"description à l'image",
            'pages':'pages',
            'external image description' : "description de l'image externe",
            'next':'suivant',  'previous':'précédent',
            'chapter':'chapitre', 'paper':'document',
            'remarks about the accessible version':'remarques concernant la version accessible',
            'note of editor': "Note de l'éditeur",
            "title page": "couverture",
            'glossary': 'glossaire',
            'index': 'index',
            'list of abbreviations': 'abréviations',
            'list of tactile graphics': 'list de la graphiques tactiles',
            'copyright notice': "avis de droit d'auteur",
            'not edited': 'pas édité',
            'end of frame': 'Fin cadre autour du texte',
            'end of box': 'Fin de la bulle de texte'
        }
        for colour, trans in {'black': ('noir', 'noire'),
                'blue': ('bleu', 'bleue'), 'brown':('marron',)*2,
                'grey': ('gris','grise'), 'green':('vert','verte'),
                'orange':('orange',)*2, 'red':('rouge',)*2,
                'violet':('violett', 'violette'), 'yellow':('jaune',)*2}.items():
            masc, fem = trans
            self.en_fr['%s frame' % colour] = 'Cadre {} autour du texte'\
                    .format(masc)
            self.en_fr['%s box' % colour] = 'Bulle {} de texte'.format(fem)

        self.en_de = {'preface':'vorwort', 'appendix':'anhang',
                "page": "Seite", "slide": "Folie",
            'table of contents' : 'inhaltsverzeichnis',
            'chapters':'kapitel',
            'image description of image':'bildbeschreibung von Bild',
            'pages':'Seiten',
            'external image description':'Bildbeschreibung ausgelagert',
            'next':'weiter',   'previous':'zurück',
            'chapter':'kapitel', 'paper':'blatt',
            'remarks about the accessible version':'Hinweise zur barrierefreien Version',
            'note of editor': 'Anmerkung des Bearbeiters',
            "title page": "Titelseite",
            'glossary': 'Glossar', 'index': 'index',
            'list of abbreviations': 'Abkürzungsverzeichnis',
            'list of tactile graphics': 'Verzeichnis taktiler Grafiken',
            'copyright notice': 'Hinweise zum Urheberrecht',
            'not edited': 'nicht Übertragen',
            'end of frame': 'Rahmenende',
            'end of box': 'Ende des Kastens', 'title': 'Titel',
        } # insert colours
        for colour, trans in {'black': 'schwarzer', 'blue': 'blauer',
                'brown':'brauner', 'grey': 'grauer', 'green':'grüner',
                'orange':'oranger', 'red':'roter', 'violet':'violetter',
                'yellow':'gelber'}.items():
            self.en_de['%s frame' % colour] = '{} Rahmen'.format(trans)
            self.en_de['%s box' % colour] = '{} Kasten'.format(trans)

        self.lang = 'de'

    def set_language(self, lang):
        if not lang in self.supported_languages:
            raise ValueError("unsupported language %s; known languages: %s" \
                    % (lang, ', '.join(self.supported_languages)))
        self.lang = lang

    def get_translation(self, origin):
        if self.lang == 'en':
            return origin
        try:
            trans = getattr(self, 'en_' + self.lang)
        except AttributeError:
            return origin
        try:
            return trans[origin]
        except KeyError:
            return origin

    def get_translation_and_upper_first(self, origin):
        s = self.get_translation(origin)
        return s[:1].upper() + s[1:] if s else ''
