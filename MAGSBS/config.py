"""
Read in user configuration.
"""

import getpass, os
import datetime, codecs
import xml.etree.ElementTree as ET
from xml.dom import minidom
import filesystem

## default values
CONF_FILE_NAME = ".lecture_meta_data.dcxml"
GLADTEX_OPTS = '-a -d bilder'


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
    if(os.path.exists( os.path.join(path, CONF_FILE_NAME) )):
        return True
    else:
        return False

def get_applicable_conf():
    """get_applicable_conf() -> file name (or path to file)

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
                os.path.split( os.path.abspath(path) )[-1]) ):
        if(os.path.exists( os.path.join(path, CONF_FILE_NAME) )):
            break # return this path + CONF_FILE_NAME
        path = os.path.join(path, '..')
    ## if we reached this, we are in the lecture root
    return os.path.join(path, CONF_FILE_NAME)


class LectureMetaData(dict):
    """
The lecture conversion needs meta data which is then embedded into the HTML
document. Those fields are e.g. souce, editor, etc.

This class provides a writer and also a reader for those files. The usage is as
follows:

# the path is optional, it'll try to autodetect the correct path
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
    def __init__(self, directory=get_applicable_conf()):
        """Set default values."""
        self.dir = directory
        self['workinggroup'] = 'AGSBS'
        self['editor'] = getpass.getuser()
        self['semesterofedit'] = get_semester()
        self['lecturetitle'] = 'Unknown'
        self['source'] = 'Unknown'
        self['institution'] = 'TU Dresden'
        self['type'] = 'html'
        self['language'] = 'de'
        self['rights'] = 'Access limited to members'
        self.dictkey2xml = {
                'workinggroup' : 'contributor', 'editor' : 'creator',
                'semesterofedit' : 'date', 'lecturetitle' : 'title',
                'source' : 'source', 'language':'language',
                'institution' : 'publisher', 'rights':'rights',
                'type' : 'type'
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
        codecs.open(CONF_FILE_NAME,'w',encoding='utf-8').write(  out )

    def read(self):
        if(has_meta_data(self.dir)):
            xmlkey2dict = {}
            for value,key in self.dictkey2xml.items():
                xmlkey2dict[ key ] = value

            root = ET.fromstring( codecs.open(CONF_FILE_NAME, 'r', 'utf-8').read() )
            for child in root:
                try:
                    self[ xmlkey2dict[ child.tag ] ] = child.text
                except IndexError:
                    print(ET.dump( child ))

