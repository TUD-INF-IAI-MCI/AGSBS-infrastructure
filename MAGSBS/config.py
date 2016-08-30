"""Handle lecture and conversion configuration. The configuration is XML in the
dublincore format (at least roughly) and has a separate namespace for
MAGSBS-specific extensions.
"""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda |at| gmx |dot| de>
#pylint: disable=line-too-long,too-few-public-methods

import datetime
from distutils.version import StrictVersion
import os
import re
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
from . import common
from .errors import ConfigurationError

VERSION = StrictVersion('0.5')

## default values
CONF_FILE_NAME = ".lecture_meta_data.dcxml"

# all tokens which can mark a start of the page
PAGENUMBERINGTOKENS = ['slide', 'folie', 'seite', 'page']
PAGENUMBERINGTOKENS += [t.title() for t in PAGENUMBERINGTOKENS] # recognize with both case spellings

# regular expression to recognize page numbers
PAGENUMBERING_PATTERN = re.compile(r'-\s*(' + '|'.join(PAGENUMBERINGTOKENS) + \
                r')\s+(\d+)\s*-')

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
        for lnum, line in enumerate(f.read().split('\n')):
            if tag in line:
                return lnum + 1


class LectureMetaData(dict):
    """The lecture conversion needs meta data which is then embedded into the HTML
document. Those fields are e.g. source, editor, etc.

This class provides a writer and also a reader for those files. A usage scenario
could look like this:

l = LectureMetaData("directory")
l.read()
l['editor'] = 'Sebastian Humenda'
l.write()

In the directory "directory", this class looks for a configuration file with
meta data. It is read. If none is present, this class will silently assume the
default values.

From the above example you can see that  this class can be used as a dictionary.
The following fields are supported:

editor          - who edited it (may be a string of names)
source          - most probably a file name
title           - None by default (can be set for table of contents, etc.)
lecturetitle    - title of lecture
institution     - publisher (default is TU Dresden)
workinggroup    - default is 'AGSBS'
semesterofedit  - either WSYY or SS/WSYY, where YY are the last two digits of
                  the year and the letters in ront are literals

Please note: you should not use this class, except you can make sure that exactly
one instance at a time exists.
"""
    #   save mapping from dict key (used internally) to XML node (with
    #   namespace, Python's name space handling is poor)
    DICTKEY2XML = {'workinggroup' : 'contributor', 'editor' : 'creator',
            'semesterofedit' : 'date', 'lecturetitle' : 'title',
                'source' : 'source', 'language':'language',
                'institution' : 'publisher', 'rights':'rights',
                'format' : 'format', 'tocDepth':'MAGSBS:tocDepth',
                'appendixPrefix' : 'MAGSBS:appendixPrefix',
                'pageNumberingGap' : 'MAGSBS:pageNumberingGap',
                'sourceAuthor':'MAGSBS:sourceAuthor',
                'generateToc':'MAGSBS:generateToc'
        }
    DEFAULTS = { 'workinggroup' : 'AG SBS', 'language':'de',
                'institution' : 'TU Dresden', 'rights': 'Access limited to members',
                'format' : 'html', 'tocDepth' : 5, 'appendixPrefix' : 0,
                'pageNumberingGap' : 5, 'generateToc' : 1}

    def __init__(self, file_path, version=VERSION):
        "Set default values."
        super().__init__()
        self.__path = file_path
        self.__numerical = ['tocDepth', 'appendixPrefix', 'pageNumberingGap',
                'generateToc']
        for key in LectureMetaData.DICTKEY2XML:
            super().__setitem__(key, 'unknown') # initialize all known keys with unknown
        for key, value in LectureMetaData.DEFAULTS.items():
            self[key] = value
        # guess editor
        if 'win32' in sys.platform or 'wind' in sys.platform:
            import getpass
            self['editor'] = getpass.getuser()
        else: # on unixoids, use pwd
            import pwd
            self['editor'] = pwd.getpwuid(os.getuid())[4]
            # on some systems, real name end with commas, strip those
            while self['editor'] and not self['editor'][-1].isalpha():
                self['editor'] = self['editor'][:-1]
        self['semesterofedit'] = get_semester() # guess current semester
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
            xml_tag = LectureMetaData.DICTKEY2XML[key]
            if xml_tag.startswith('MAGSBS:'):
                c = ET.SubElement(root, xml_tag)
            else:
                c = ET.SubElement(root, 'dc:' + xml_tag)
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
        xmlkey2dict = {normalize_keys(key): value
            for value, key in LectureMetaData.DICTKEY2XML.items()}

        with open(self.__path, 'r', encoding='utf-8') as data_source:
            root = ET.fromstring(data_source.read())
            normalize_tag = lambda x: (x[x.find('}')+1:]  if '}' in x else x)
            version_read = False
            for child in root:
                key = normalize_tag(child.tag)
                if key == 'version':
                    version_read = True
                    self.__check_for_version(self.__path, child.text)
                elif not key in xmlkey2dict:
                    common.WarningRegistry().register_warning(
                            "Unknown key %s, skipping." % key,
                            path=self.__path)
                    continue
                else:
                    key = xmlkey2dict[key] # use the internally used key instead
                    try:
                        value = child.text
                        if value in self.__numerical:
                            try:
                                value = int(value)
                            except ValueError:
                                raise ConfigurationError("Option " + key +
                                    "has invalid,  non-numerical value of " +
                                    value, self.__path)
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
        if k in self.__numerical:
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
class confFactory():
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
        If no configuration is found, the default configuation object is
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
            'not edited': 'pas édité'
            }
        self.en_de = {'preface':'vorwort', 'appendix':'anhang',
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
            'not edited': 'nicht Übertragen'
            }
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

