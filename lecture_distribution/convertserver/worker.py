#!/usr/bin/python3
# -*- coding: utf-8 -*-
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>

"""
No nice source code, (partly) C-like imperative style. Was intended as a short script,
but grew.
"""

import subprocess, os, zipfile, codecs, io
import sys, smtplib, datetime, atexit
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import email, email.header
import helpers
from constants import *
import MAGSBS

#TXN_NAME=sys.argv[3] # mhh?
"""
The directory structure must look like:

    SEMESTER/FIELD/SUBJECT

e.g.:
SS15/INF/Mikrokernel construction

Alternatively, Buecher might reside under:


Buecher/Title
"""



def remove_surrogate_escaping(s, method='replace'):
    assert method in ('ignore', 'replace'), 'invalid removal method'
    return s.encode('utf-8', method).decode('utf-8')

def subprocess_call(args, stdin=None, stdout=None):
    if( not stdout): stdout = sys.stdout
    if(not stdin): stdin = sys.stdin
    myenv = os.environ.copy()
    myenv['LANG'] = "de_DE.UTF-8"
    assert type(args) == list
    for num, arg in enumerate(args):
        args[num] = arg.encode( sys.getdefaultencoding() )
    proc = subprocess.Popen(args, env=myenv, stdin=stdin, stdout=stdout)
    return proc.wait()

def pretty_filesize( path ):
    """Pretty-format file size of given path to German format and into kb or mb."""
    statinfo = os.stat( path )
    filesize = statinfo.st_size
    divided = 0
    units = ['B', 'KB', 'MB', 'GB']
    while(filesize> 1024):
        filesize /= 1024
        divided += 1
    filesize = str(filesize)
    dot = filesize.find('.')
    if((dot >=0) and (len(filesize[dot:]) > 2)):
        filesize = filesize[:dot+3]
    filesize = filesize.replace(".", ",")
    return filesize + " " + units[ divided ]


def call_MAGSBS_master( rev, repo, path ):
    """Everything what MAGSBS.masterMaster does + removing MarkDown files."""
    m = MAGSBS.master.Master( path )
    try:
        m.run()
    except MAGSBS.errors.SubprocessError as E:
        proc = subprocess.Popen(["svnlook","author","-r", str(rev), repo],
                stdout=subprocess.PIPE)
        username = proc.communicate()[0].decode( sys.getdefaultencoding() )
        msg = "Hallo,\n\nes trat beim Konvertieren von " + path + \
                " ein Fehler auf:\n" + E.args[0]
        helpers.send_error( repo, msg, to = username+'@mail.zih.tu-dresden.de')
        sys.exit( 9 )
    for dir, dir_list, f_list in MAGSBS.filesystem.get_markdown_files( path ):
        for f in f_list:
            if( not f.endswith(".md") ): continue
            f = os.path.join( dir, f )
            # for each MarkDown file, there must be a HTML file, else raise an
            # Error
            if(os.path.exists( f[:-2] + 'html' )):
                os.remove( f )
            else:
                raise OSError("For the file \"%s\", no HTML file exists, even though all files should have been converted. It looks like a bug in MAGSBS.master.Master" \
                        % f)

def send_mail(zihlogin, to, subject, filename, commit_msg):
    if(type(to) != list):
        to = [to]
    # preformat some data
    if(commit_msg.strip() == ""):
        commit_msg = "Leider hat der Bearbeiter keinen Hinweistext verfasst."
    else:
        commit_msg = "Änderungshinweis:\n" + commit_msg
    SVNNAME, filename = os.path.split( filename )
    file_size = pretty_filesize( os.path.join( SSHFS_MOUNTPOINT, SVNNAME, filename ) )

    msg = MIMEMultipart('plain text')
    msg.set_charset('utf-8')
    msg['Subject'] = email.header.Header('Neue Materialien fuer %s' % subject,
            'utf-8')
    msg['From'] = 'Neue Lehrmaterialien <'+EMAIL_ADDRESS+'>'
    msg['To'] = ', '.join( to )
    msg.preamble = "This is a multi-part message in MIME format."
    msgAlternative = MIMEMultipart('alternative')
    msg.attach(msgAlternative)
    text = """
Guten Tag,

in "%s" wurden Änderungen vorgenommen.

Größe: %s
%s

Sie finden das Material zum Download unter:

https://%s@elvis.inf.tu-dresden.de/material/%s

--
Bei Fragen und Fehlern wenden Sie sich bitte an die Mailingliste; Senden Sie
dazu eine E-Mail an <ag-sbs@groups.tu-dresden.de> und falls notwendig,
schildern
Sie die Fehlermeldung und Ihr Vorgehen.
""" % (subject, file_size, commit_msg, zihlogin, filename)
    HTML = """
<html>
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <title>Neues Material in "%s"</title>
</head>
<body>
<p>Guten Tag,</p>
<p>in "%s" wurden Änderungen vorgenommen.</p>
<p>Größe: %s</p>
<p>%s </p>

<p>Sie finden das Material zum Download unter:<br/>
<a
href="https://%s@elvis.inf.tu-dresden.de/material/%s">https://%s@elvis.inf.tu-dresden.de/material/%s</a>
</p>
<hr/>
<p>
Bei Fragen und Fehlern wenden Sie sich bitte an die Mailingliste; Senden Sie
dazu eine E-Mail an <a
href="mailto:ag-sbs@groups.tu-dresden.de">ag-sbs@groups.tu-dresden.de</a>
und falls notwendig, schildern
Sie die Fehlermeldung und Ihr Vorgehen.
</p></body></html>
""" % (subject, subject, file_size, commit_msg, zihlogin, filename, zihlogin, filename)

    msgHTML = MIMEText( HTML.encode('utf-8'), 'html', _charset='utf-8')
    msgAlternative.attach( msgHTML )

    msgText = MIMEText(text.encode('utf-8'), 'plain', _charset='utf-8')
    msgAlternative.attach( msgText )


    s = smtplib.SMTP()
    s.connect( SSMTP_DOMAIN )
    s.send_message( msg, EMAIL_ADDRESS, ', '.join(to))
    s.quit()

def copy_file_to_server( SVNNAME, path ):
    target = os.path.join( SSHFS_MOUNTPOINT, SVNNAME, os.path.split( path )[-1])
    if(os.path.exists( target )):
        subprocess_call(['rm', target ], stdout=open('/dev/null','w'))
    subprocess_call(['cp', '-dpr', path,
        os.path.join( SSHFS_MOUNTPOINT, SVNNAME)],
        stdout=open('/dev/null','w'))
    cwd = os.getcwd()
    os.chdir( os.path.join( SSHFS_MOUNTPOINT, SVNNAME) )
    for item in os.listdir("."):
        subprocess_call( ['chmod', 'a+r', item])
    os.chdir( cwd )


def zipmaterial( base, directory, zip):
    """Zip a directory."""
    cwd = os.getcwd()
    # change to directory above the directory to compres
    os.chdir( base )
    subprocess_call(['zip', '-r', zip, directory], stdout=open('/dev/null'))
    os.chdir( cwd )
    #zipf = zipfile.ZipFile(zip, 'w')
    #for root, dirs, files in os.walk(directory):
    #    for file in files:
    #        root = remove_surrogate_escaping( root )
    #        file = remove_surrogate_escaping( file )  # os.walk creates surrogates...
    #        zfile = os.path.join( root, file )
    #        zipf.writestr( zfile,#.encode('iso-8859-15'),
    #                io.open(zfile,'rb').read())
    #zipf.close()



class Material():
    """Datatype to save name, id and path of subject."""
    def __init__(self, path, name):
        self.path = self.determine_path( path )
        self.id = self.gengrpid( name )
        self.name = name
    def determine_path(self, path):
        if(path.find('bearbeitet')>=0):
            path = path[ : path.find('bearbeitet') + len('bearbeitet')+1]
        if(path.endswith('/')):
            path = path[:-1]
        return path
    def gengrpid(self, path):
        """Generate group id from path."""
        newstr = ''
        path = path.strip().lower()
        for c in path:
            if((c.isalpha() or c.isdigit())and ord(c) < 128):
                newstr += c
        return newstr


class EmailUser():
    def __init__(self, zih_login, email):
        self.zihlogin = zih_login
        self.email = email

def read_user_subscriptions( repo ):
    subs = {}
    data = codecs.open( os.path.join(repo, 'hooks', 'subscriptions_email'),
            'r', 'utf-8').read()
    for num, line in enumerate( data.split('\n') ):
        if(line.strip() == '' or line.startswith('#')): continue

        fields = line.split(',')
        if(len(fields)<2):
            helpers.send_error(repo, "In the repository "+repo+", the subscriptions are damaged on line "+str(num+1)+".")
        subject = fields[0]
        subs[ subject ] = []
        for person in fields[1:]:
            zihlogin, address = person.split(' ')
            subs[ subject ].append( EmailUser( zihlogin, address ) )
    return subs


class SVNParser():
    """Parse the output of svn look."""
    def __init__(self, rev, repo):
        self.rev = rev
        self.repo = repo
        self.__subjects = []
        self.__data = self.read_input()

    def get_subjects(self): return self.__subjects

    def read_input(self):
        """Read data from SVN using subprocess."""
        # get list of changed files
        proc = subprocess.Popen(['svnlook', 'changed', self.repo, '-r', self.rev],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = proc.communicate()
        if(proc.wait()):
            raise Exception(data[1].decode('utf-8'))
        data = data[0]
        data = data.decode(sys.getdefaultencoding(), 'surrogateescape')
        return data

    def parse(self):
        """Parse SVN data."""
        for line in self.__data.split('\n'):
            while(len(line)>0): # strip white spaces / \r / blah at the end
                if(line[-1].isspace()):
                    line = line[:-1]
                else:
                    break
            # search for the path; strip status letter first, afterwards spaces
            status = ''
            idx = 0
            while(idx < len(line)): # search for status letter or _ at beginning
                if(line[idx].isspace()):
                    break
                status += line[idx]
                idx += 1
            while(idx < (len(line)-1)):
                if(not line[idx].isspace()): break
                idx += 1
            if(line[idx:].strip() != ''):
                path = line[idx:]
                new_material = None
                if(path.lower().find('quelldateien')>=0 or \
                        path.lower().find('quellen')>=0):
                    continue
                # skip if it ends on os.sep, because only when files are in
                # there, it should be considered
                if( path.endswith( os.sep ) ):
                    continue
                if(path.lower().startswith('buecher')):
                    new_material = self.__parseBuecher( path )
                else:
                    new_material = self.__parse_lectures( path )
                if( new_material ):
                    # check whether it is already indexed
                    ids = [e.id for e in self.__subjects ]
                    if(not (new_material.id in ids)):
                        self.__subjects.append( new_material )

    def __parseBuecher(self, path):
        if(len(path.split( os.sep )) < 2):
            return None
        name = path.split( os.sep )[1]
        return Material( path, name )

    def __parse_lectures(self, path):
        if(len(path.split(os.sep)) < 3):
            return None
        else:
            k = path.split(os.sep)[2]
            return Material( path, k)

#def clean_up_at_exit(tmp):
#    os.system('rm -rf "%s"' % tmp )


def main( rev, repo ):
    os.environ[ "LANG" ] = "de_DE.UTF-8" # guessed work-around
    mytmp = helpers.NEWTMP( repo )
    SVNNAME = os.path.split( repo )[-1]

    SVN = SVNParser(rev, repo)
    SVN.parse()
    subjects = SVN.get_subjects()
    # fetch commit message
    proc = subprocess.Popen(['svnlook', 'log', '-r', rev, repo],
                stdout=subprocess.PIPE)
    commit_msg = proc.communicate()[0].decode(sys.getdefaultencoding(),
                'surrogateescape')


    emails = read_user_subscriptions( repo )

    os.mkdir( mytmp )
    helpers.set_group( mytmp )

    # generate / zip data
    os.chdir( mytmp )
    if(not os.path.exists( os.path.join( SSHFS_MOUNTPOINT, SVNNAME))):
        os.mkdir( os.path.join( SSHFS_MOUNTPOINT, SVNNAME))
        subprocess_call(['chmod', 'a+r',
                os.path.join(SSHFS_MOUNTPOINT, SVNNAME)])
    for subject in subjects:
        subprocess_call(['svn', 'export', '-q',
            'file://'+repo + '/' + subject.path,
            os.path.join( mytmp, subject.id)])
        # all tasks defined in MAGST.master (conversion and automagic stuff):
        call_MAGSBS_master( rev, repo, os.path.join( mytmp, subject.id ) )
        zipmaterial( mytmp, subject.id, subject.id + '.zip' )
    helpers.set_group( mytmp )
    # send emails
    for subject in subjects:
        copy_file_to_server( SVNNAME, os.path.join( mytmp, subject.id) + '.zip')
        # send email
        if(subject.id in emails.keys()):
            for person in emails[ subject.id ]:
                send_mail(person.zihlogin, person.email, subject.name,
                        os.path.join( SVNNAME, subject.id+'.zip'), commit_msg )
        else:
            helpers.send_error( repo, "No subscriber for: "+\
                    subject.name+': '+subject.path+ "\nUsed ID: "+\
                    subject.id +'\nKnown keys: '+', '.join(list(emails.keys()))+\
                    '\nRevision: '+str(rev))
            subprocess_call( ['rm', '-rf', mytmp])

