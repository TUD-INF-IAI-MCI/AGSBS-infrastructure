#!/usr/bin/env python3
"""This file provides a matuc interface with solely JSON output. It imports
matuc and alters the OutputFormatter to print JSON."""
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda@gmx.de>

import json
import os
import sys
import imp

binary_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
# check for the matuc "program" to use as library."""
if not any('matuc' in e   for e in os.listdir(binary_directory)):
    raise OSError('Could not find matuc in "%s" % binary_directory'
if 'matuc.py' in os.listdir(binary_directory):
    matuc = imp.load_source('matuc', os.path.join(binary_directory,
        'matuc.py'))
elif 'matuc' in os.listdir(binary_directory):
    matuc = imp.load_source('matuc', os.path.join(binary_directory, 'matuc'))

# enable debugging for matuc_js, since it is a programatic internface and it is
# useful to report errors when they occur
os.environ['DEBUG'] = str(1)

class JsonFormatter(matuc.OutputFormatter):
    def __emit_json(self, object):
        sys.stdout.write(json.dumps(object, indent=2, sort_keys=True) + '\n')

    def emit_result(self, result):
        warnings = self.get_warnings()
        output = {}
        if warnings:
            output['warnings'] = warnings
        output['result'] = result
        self.__emit_json(output)

    def emit_error(self, error):
        warnings = self.get_warnings()
        output = {'error': error}
        if warnings:
            output['warnings'] = warnings 
        self.__emit_json(output)

    def emit_usage(self, usage, error=None):
        output = {'usage': usage}
        if error:
            output['error'] = error.rstrip()
        self.__emit_json(output)

    def clear(self):
        """Screen will _not_ be cleared in JSON output  mode."""
        pass

if __name__ == '__main__':
    main_inst = matuc.main(JsonFormatter())
    main_inst.run(sys.argv)

