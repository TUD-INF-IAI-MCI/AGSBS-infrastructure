"""
Read in user configuration.
"""

import getpass
import datetime

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

def read_user_configuration():
    """Todo: implement me. Use standard values up to now."""
    defaults = {'workinggroup':'AGSBS', 'editor' : getpass.getuser(),
            'semesterofedit' : get_semester(), 'lecturetitle':'Unknown',
            'source':'Unknown', 'institution':'TU Dresden',
            'gladtex_opts':'-a -d bilder'}
    return defaults
