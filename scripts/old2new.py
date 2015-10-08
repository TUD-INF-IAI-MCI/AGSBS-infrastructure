#!/usr/bin/env python3
# This is free software licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014 Sebastian Humenda <shumenda@gmx.de>
__doc__ = """
This script converts files which uses the old page numbering style to the new
format. The old format used h5 headings, the new one uses ||<pagenumber>.
"""

import sys, re, codecs, os

def renew_a_file( fn ):
    data = codecs.open( fn, 'r', 'utf-8').readlines()

    for num, line in enumerate( data ):
        i=len(line)-1
        if(line.strip() == ''): continue
        while(line[i] == '\n' or line[i] == '\r'): i -= 1
        line = line[:i+1]
        obj = re.search(r'######\s*-\s*(Seite|Slide|slide|page|Page|Folie)\s+(\d+)\s*-', line)
        if( obj ):
            obj = obj.groups()
            data[ num ] = '|| - ' + obj[0] + ' ' + obj[1] + ' -\n'
    codecs.open( fn, 'w', 'utf-8' ).write( ''.join( data ) )

if(len(sys.argv) < 2):
    print(sys.argv[0] + " <FILENAME>\n" + __doc__)
    sys.exit(127)
elif(not os.path.exists( sys.argv[1] )):
    print(sys.argv[0]+": The file %s doesn't exist." % sys.argv[1] )
    sys.exit(127)
else:
    if(os.path.isfile( sys.argv[1] )):
        print('Editing ',sys.argv[1])
        renew_a_file( sys.argv[1] )
    else:
        for directoryname, directory_list, file_list in os.walk( sys.argv[1] ):
            for file in file_list:
                if(file.endswith('.md')):
                    print('Editing ',os.path.join( directoryname,file))
                    renew_a_file( os.path.join( directoryname, file) )
