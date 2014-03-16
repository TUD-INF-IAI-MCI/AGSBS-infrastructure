"""
Read in user configuration.
"""

import getpass, os, sys, pwd
import datetime, codecs
import xml.etree.ElementTree as ET
from xml.dom import minidom
import filesystem

## default values
CONF_FILE_NAME = ".lecture_meta_data.dcxml"
GLADTEX_OPTS = '-a -d bilder'
PYVERSION = int(sys.version[0])

class Singleton:
    """
A non-thread-safe helper class to ease implementing singletons.
This should be used as a decorator -- not a metaclass -- to the class that
should be a singleton.

The decorated class can define one `__init__` function that takes only the
`self` argument. Other than that, there are no restrictions that apply to the
decorated class.

To get the singleton instance, use the `Instance` method. Trying to use
`__call__` will result in a `TypeError` being raised.

Limitations: The decorated class cannot be inherited from.
"""
    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self, path):
        """Returns the singleton instance. Upon its first call, it creates a
new instance of the decorated class and calls its `__init__` method.  On all
subsequent calls, the already created instance is returned.  """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated(path)
        return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)


def get_semester():
    semester = ''
    month = datetime.datetime.now().month
    if(month < 4 or month > 10):
        semester = 'WS'
        year = datetime.datetime.now().year
        if(month < 4):
            year -= 1
    else:
        semester = 'SS'
        year = datetime.datetime.now().year
    if(semester == 'WS'):
        semester += str( year )[-2:] + '/' + str( year + 1 )[-2:]
    else:
        semester += str( year )[-2:]
    return semester

def has_meta_data(path):
    """Return whether lecture meta data can be found in the specified path."""
    if(not path.endswith(CONF_FILE_NAME)):
        path = os.path.join(path, CONF_FILE_NAME)
    if(os.path.exists( path )):
        return True
    else:
        return False

@Singleton
class _LectureMetaData(dict):
    """
The lecture conversion needs meta data which is then embedded into the HTML
document. Those fields are e.g. souce, editor, etc.

This class provides a writer and also a reader for those files. The usage is as
follows:

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

All parameters are strings.
"""
    def __init__(self, path):
        "Set default values."
        self.__path = path
        self['workinggroup'] = 'AGSBS'
        if(sys.platform.lower().find('win')>=0):
            self['editor'] = getpass.getuser()
        else: # full name with the unix way
            self['editor'] = pwd.getpwuid(os.getuid())[4]
            # on some systems, real name ends with commas, strip those
            while(self['editor'].endswith(',')):
                self['editor'] = self['editor'][:-1]
        self['semesterofedit'] = get_semester()
        self['lecturetitle'] = 'Unknown'
        self['source'] = 'Unknown'
        self['institution'] = 'TU Dresden'
        self['format'] = 'html'
        self['language'] = 'de'
        self['rights'] = 'Access limited to members'
        self['format'] = 'html'
        self.dictkey2xml = {
                'workinggroup' : 'contributor', 'editor' : 'creator',
                'semesterofedit' : 'date', 'lecturetitle' : 'title',
                'source' : 'source', 'language':'language',
                'institution' : 'publisher', 'rights':'rights',
                'format' : 'type'
        }
        dict.__init__(self)

    def write(self):
        root = ET.Element('metadata')
        root.attrib['xmlns:dc'] = 'http://purl.org/dc/elements/1.1'
        root.attrib['xmlns:xsi'] = 'http://www.w3.org/2001/XMLSchema-instance'
        for key, value in self.items():
            c = ET.SubElement(root, 'dc:'+self.dictkey2xml[ key ] )
            c.text = value
        out = dom = minidom.parseString(
                '<?xml version="1.0" encoding="UTF-8"?>' + \
                ET.tostring( root )).toprettyxml()
        codecs.open(self.__path,'w',encoding='utf-8').write(  out )

    def normalize_tag(self, tag):
        if(tag.find('}')>0):
            return tag[ tag.find('}')+1:]
        else:
            return tag

    def read(self):
        if(has_meta_data(self.__path)):
            xmlkey2dict = {}
            for value,key in self.dictkey2xml.items():
                xmlkey2dict[ key ] = value

            # py 2 / 3:
            data = codecs.open( self.__path, 'r', 'utf-8').read()
            if(PYVERSION == 2):
                data = data.encode('utf-8')
            root = ET.fromstring( data )
            for child in root:
                try:
                    self[ xmlkey2dict[ self.normalize_tag( child.tag ) ] ] = child.text
                except IndexError:
                    print(ET.dump( child ))

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
    def get_conf_instance(self, force_current_directory=False):
        """Return either an old object if already created or create a new one
(kind of singleton). Automatically read the configuration upon creation."""
        if(force_current_directory):
            path = CONF_FILE_NAME
        else:
            path = self.__getpath()
        if(path in self._instances.keys()):
            return self._instances[ path ]
        else:
            self._instances[ path ] = _LectureMetaData.Instance( path )
            self._instances[ path ].read()
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
        while(filesystem.valid_file_bgn(
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


