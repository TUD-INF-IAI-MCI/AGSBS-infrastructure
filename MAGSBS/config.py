"""
Read in user configuration.
"""
#pylint: disable=invalid-encoded-data,line-too-long,too-few-public-methods

import getpass, os, sys
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
from . import common
from .errors import ConfigurationError, ConfigurationNotFoundError

if not (sys.platform.lower().startswith("win")):
    import pwd

VERSION = '0.3'
## default values
CONF_FILE_NAME = ".lecture_meta_data.dcxml"
# as a regular expression all kinds of token which can mark a page
PAGENUMBERINGTOKENS = ['slide','folie','seite','page']
PAGENUMBERING_REGEX = r'-\s*(' + '|'.join(PAGENUMBERINGTOKENS) + \
                r')\s+(\d+)\s*-'

VALID_PREFACE_BGN = ['v']
VALID_MAIN_BGN = ['k', 'blatt', 'Blatt', 'paper']
VALID_APPENDIX_BGN = ['anh']
VALID_FILE_BGN = VALID_PREFACE_BGN + VALID_MAIN_BGN + VALID_APPENDIX_BGN

class Singleton:
    """
A non-thread-safe helper class to ease implementing singletons.
This should be used as a decorator -- not a metaclass -- to the class that
should be a singleton.

The decorated class can define one `__init__` function that takes only the
`self` argument. Other than that, there are no restrictions that apply to the
decorated class.

Limitations: The decorated class cannot be inherited from.
"""
    def __init__(self, decorated):
        self._decorated = decorated
        self._instance = None

    def __call__(self):
        """Returns the singleton instance. Upon its first call, it creates a
new instance of the decorated class and calls its `__init__` method.  On all
subsequent calls, the already created instance is returned.  """
        if not self._instance:
            self._instance = self._decorated()
        return self._instance

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

def get_semester():
    """Guess from the time in the year the semester (summer or winter, looking
    at German semesters, though."""
    semester = ''
    month = datetime.datetime.now().month
    if month < 4 or month > 10:
        semester = 'WS'
        year = datetime.datetime.now().year
        if month < 4: # if before April, that's still previous winter semester
            year -= 1
    else:
        semester = 'SS'
        year = datetime.datetime.now().year
    yearstring = str(year)
    if semester == 'WS': # winter semester stretches across the years boundary:
        yearstring += '/' + str(year + 1)
    return '%s %s' % (semester, yearstring)

def has_configuration(path):
    """Return whether lecture meta data can be found in the specified path."""
    if(not path.endswith(CONF_FILE_NAME)):
        path = os.path.join(path, CONF_FILE_NAME)
    if(os.path.exists( path )):
        return True
    else:
        return False

class LectureMetaData(dict):
    """
The lecture conversion needs meta data which is then embedded into the HTML
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
    def __init__(self, path):
        "Set default values."
        self.__path = path
        self.__numerical = ['tocDepth', 'appendixPrefix', 'pageNumberingGap']
        self['workinggroup'] = 'AGSBS'
        if 'win32' in sys.platform or 'wind' in sys.platform:
            self['editor'] = getpass.getuser()
        else: # full name with the unix way
            self['editor'] = pwd.getpwuid(os.getuid())[4]
            # on some systems, real name end with commas, strip those
            while self['editor'].endswith(','):
                self['editor'] = self['editor'][:-1]
        self['semesterofedit'] = get_semester()
        self['lecturetitle'] = 'Unknown'
        self['source'] = 'Unknown'
        self['institution'] = 'TU Dresden'
        self['format'] = 'html'
        self['language'] = 'de'
        self['rights'] = 'Access limited to members'
        self['format'] = 'html'
        self['tocDepth'] = 5
        self['appendixPrefix'] = 0
        self['pageNumberingGap'] = 5
        self['sourceAuthor'] = 'unknown'
        self.dictkey2xml = {
                'workinggroup' : 'contributor', 'editor' : 'creator',
                'semesterofedit' : 'date', 'lecturetitle' : 'title',
                'source' : 'source', 'language':'language',
                'institution' : 'publisher', 'rights':'rights',
                'format' : 'format',
                'tocDepth':'MAGSBS:tocDepth',
                'appendixPrefix' : 'MAGSBS:appendixPrefix',
                'pageNumberingGap' : 'MAGSBS:pageNumberingGap',
                'sourceAuthor':'MAGSBS:sourceAuthor',
        }
        dict.__init__(self)

    def write(self):
        root = ET.Element('metadata')
        root.attrib['xmlns:dc'] = 'http://purl.org/dc/elements/1.1'
        root.attrib['xmlns:MAGSBS'] = 'http://elvis.inf.tu-dresden.de'
        for key, value in self.items():
            if not self.dictkey2xml[key].startswith('MAGSBS:'):
                c = ET.SubElement(root, 'dc:'+self.dictkey2xml[ key ] )
            else:
                c = ET.SubElement(root, self.dictkey2xml[key])
            c.text = str(value)
        out = minidom.parseString('<?xml version="1.0" encoding="UTF-8"?>' + \
                ET.tostring(root, encoding="unicode")
                ).toprettyxml(indent="  ", encoding="utf-8")
        open(self.__path, 'wb').write(out)

    def normalize_tag(self, tag):
        if(tag.find('}')>0):
            return tag[ tag.find('}')+1:]
        else:
            return tag

    def read(self):
        if not has_configuration(self.__path):
            return
        xmlkey2dict = {}
        for value,key in self.dictkey2xml.items():
            if key.startswith('MAGSBS'):
                key = key.split(':')[1]
            xmlkey2dict[key] = value

        with open(self.__path, 'r', encoding='utf-8') as data_source:
            root = ET.fromstring(data_source.read())
            for child in root:
                try:
                    key = xmlkey2dict[self.normalize_tag(child.tag)]
                except KeyError as e:
                    common.warn("Unknown key %s, skipping." % e.args[0])
                    continue
                try:
                    value = child.text
                    if value in self.__numerical:
                        try:
                            value = int( value )
                        except ValueError:
                            raise ConfigurationError("Option " + key +
                                    "has invalid,  non-numerical value of " +
                                    value)
                    self[key] = value
                except IndexError:
                    print(ET.dump( child ))

    def __setitem__(self, k, v):
        if(k in self.__numerical):
            try:
                v = int(v)
            except ValueError:
                raise TypeError("Option " + k + ": not a number (%s)" % v)
        dict.__setitem__(self, k, v)

@Singleton
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

    def get_conf_instance(self):
        """Return either an old object if already created or create a new one
(kind of singleton). Automatically read the configuration upon creation."""
        path = self.__getpath()
        if path in self._instances.keys():
            return self._instances[path]
        else:
            try:
                self._instances[ path ] = LectureMetaData( path )
                self._instances[path].read()
            except UnicodeDecodeError:
                raise ValueError(path + ": File must be encoded in UTF-8")
        return self._instances[ path ]

    def __getpath(self):
        """__getpath() -> path to configuration file

If the current directory contains a configuration file, just return the file
name. If this directory is not the lecture root, look in the lecture root for a
configuration file. If the lecture root has also no configuration, return the
lecture root path nevertheless.

Please note: if you are in a subdirectory, this will be a path like ../$CONF_FILE_NAME."""
        if(os.path.exists(CONF_FILE_NAME)):
            return CONF_FILE_NAME
        # cwd != lecture root?
        path = ''
        def valid_dir_bgn(s): # cannot be used from file_system, circular dependency
            for k in VALID_FILE_BGN:
                if(s.startswith(k) and (len(s) > (len(k))+1)):
                    if(s[len(k)].isdigit()):
                        return True
            return False
        while(valid_dir_bgn( \
                    os.path.split( os.path.abspath(path) )[-1])):
            if(os.path.abspath(os.sep) == os.path.abspath( path )):
                raise ConfigurationNotFoundError("While searching for a"+\
                        " configuration file, the root directory was"+\
                        " reached.\nThis means that this program fails to"+\
                        " determine the lecture root.\nPlease report this bug.")
            if(os.path.exists( os.path.join(path, CONF_FILE_NAME) )):
                break # return this path
            path = os.path.join(path, '..')
        # if we reached this, we are in the lecture root
        return os.path.abspath( os.path.join(path, CONF_FILE_NAME) )

class Translate:
    """Replace me through gettext, as soon as its clear how easy it is to ship
l10n with Windows."""
    def __init__(self):
        self._factory = confFactory()
        self.supported_languages = [ 'de', 'fr' ]
        self.en_fr = {
            'preface':'introduction',   'appendix':'appendice',
            'table of contents':'table des matières',
            'chapters':'chapitres',
            'image description of image':"description à l'image",
            'pages':'pages',
            'index':'index',
            'external image description' : "description de l'image externe",
            'images':'images',
            'next':'suivant',  'previous':'précédent',
            'chapter':'chapitre', 'paper':'document',
            'Remarks about the accessible version':'Remarques concernant la version accessible',
            }
        self.en_de = {'preface':'vorwort', 'appendix':'anhang',
            'table of contents' : 'inhaltsverzeichnis',
            'chapters':'kapitel',
            'image description of image':'bildbeschreibung von Bild',
            'pages':'Seiten',
            'external image description':'Bildbeschreibung ausgelagert',
            'images':'bilder',
            'index':'Inhalt',
            'next':'weiter',   'previous':'zurück',
            'chapter':'kapitel', 'paper':'blatt',
            'Remarks about the accessible version':'Hinweise zur der barrierefreien Version'
            }

    def get_translation(self, origin):
        inst = self._factory.get_conf_instance()
        lang = inst[ 'language' ]

        try:
            trans = getattr(self, 'en_'+lang)
        except AttributeError:
            return origin
        try:
            return trans[ origin ]
        except KeyError:
            return origin

L10N = Translate()
_ = L10N.get_translation
