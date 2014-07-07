import socket, os, sys, datetime

REV = sys.argv[1]
REPO = sys.argv[2]

def TMP( repo, suffix ):
    now = datetime.datetime.now()
    PREFIX = "/tmp/.svn_" + str(now.minute) + str(now.second) + \
        str(now.microsecond)
    if( suffix ):
        return os.path.join( PREFIX, suffix )
    else:
        return PREFIX
client = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
client.connect( ("127.0.0.1", 49867) )

client.send( (REV + " -- " + REPO).encode("utf-8") )
resp = client.recv(1024).decode("utf-8")
if(not resp.startswith("I:")):
    print('Fehler: ',resp)
    sys.exit( 1 )
client.close()
