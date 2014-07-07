import smtplib, os
from email.mime.text import MIMEText
from constants import *
import sys, datetime, random

sys.path.append("..")

# set that up
try:
    os.environ['PATH'] += ':/home/s7369555/bin'
except KeyError:
    os.environ['PATH'] = '/bin:/usr/bin:/home/s7369555/bin'

import MAGSBS, MAGSBS.master


def send_error( repo, error, to = None):
    SVNNAME = os.path.split( repo )[-1]
    if( not to ):
        to = ', '.join( PANICEMAIL )
    else:
        if(type(to) == str):
            to = [to]
    msg = MIMEText(error.encode('utf-8'), 'plain', _charset='utf-8')
    msg['Subject'] = 'Fehler in '+SVNNAME
    msg['From'] = SVNNAME+'_error@iai8292.inf.tu-dresden.de'
    msg['To'] = to
    s = smtplib.SMTP()
    s.connect( SSMTP_DOMAIN )
    s.send_message( msg, SVNNAME + '_error@iai8292.inf.tu-dresden.de', to)
    s.quit()

def set_group(path):
    """Set group ownership of given path."""
    os.system('chgrp -R agsbs_informatik-svn "%s"' % path)


TMP_BASE = '/tmp/.svn'

def NEWTMP( repo ):
    PREFIX = TMP_BASE + '_' + os.path.split( repo )[-1] + '-'
    now = datetime.datetime.now()
    PREFIX += str(now.hour) + '.' + str(now.minute) + '_' + str(now.second) + \
            '.' + str(now.microsecond * random.randint(2,9))
    return PREFIX


def cleanup():
    os.chdir( os.path.split( TMP_BASE)[0] )
    for dir in [e for e in os.listdir(".") if os.path.isdir( e) and\
            e.startswith(  os.path.split( TMP_BASE )[-1] )]:
        os.system("rm -rf \"%s\"" %  dir)
