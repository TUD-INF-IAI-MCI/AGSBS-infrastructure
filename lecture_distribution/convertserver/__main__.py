import os, sys, socket
from constants import *
import worker, helpers, atexit

"""
Dependencies:

    - GladTeX (for MarkDown /  LaTeX equations)
    - pandoc (>= 1.12.4.4, for conversion of MarkDown files)
    - python3
    - svn
    - zip
"""

SERVER = None

class socketserver():
    def __init__(self):
        self.__server = None
        self.handler = None # function taking rev and repo from server
        self.__conn = None

    def run(self):
        global SERVER
        if( not self.handler ):
            raise ValueError("A handler must be registered first.")

        self.__server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        SERVER = self.__server
        self.__server.bind( ("127.0.0.1", 49867) )
        self.__server.listen( 1 )
        while True:
            self.__conn, addr = self.__server.accept()
            data = self.__conn.recv( 2048 )
            self.__handledata( data )
    def __handledata( self, data ):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            self.__conn.send(b"E: Sorry, but input must be in UTF-8 format.\n")
        data = data.split(" -- ")
        if(len(data) != 2):
            self.__conn.send(b"E: input has two fields: revision and path to SVN repo, separated by \" -- \".\n")
            self.__conn.close()
        self.__conn.send(b"I: Successfully queued your request.\n")
        self.__conn.close()
        self.handler( data[0], data[1])
    def set_handler(self, h):
        self.handler = h


if(len(sys.argv) == 3):
    if(sys.argv[1] == '-g'):
        print(worker.Material.gengrpid('', sys.argv[2]))
        sys.exit(0)

atexit.register( helpers.cleanup )
try:
    s = socketserver()
    s.set_handler( worker.main )
    s.run()
except Exception as e:
    print("closing TCP/IP server port...")
    SERVER.close()
    raise # Todo: delme
    import traceback, locale
    helpers.send_error(  'SocketServer_died', traceback.format_exc()+'\n\n' + \
            '\nLocale: '+str(locale.getlocale()))
