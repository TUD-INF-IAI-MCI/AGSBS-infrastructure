#!/usr/bin/env python3
# Markdown AGSBS (TU) Command line
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2016 Sebastian Humenda <shumenda@gmx.de>
#
# This file contains the command-line frontend for the MAGSBS module, with a
# user-friendly text interface. Most of the functionality is implemented in
# matuc_impl, only the text formatter is defined here.
#pylint: disable=multiple-imports


import os
import shutil
import sys
import textwrap
import MAGSBS
import matuc_impl

def flatten(thing): # flatten a list of lists
    if isinstance(thing, list):
        for item in thing:
            for whatever in flatten(item): yield whatever
    else:
        yield thing



class TextFormatter(matuc_impl.OutputFormatter):
    def __init__(self):
        super().__init__()
        self.spaces = lambda num: ' ' * num

    def __emit_warnings(self):
        """Emit warnings from the warning registry."""
        reindent = lambda x: x.replace('\n', '\n  ')
        warnings = self.get_warnings()
        if warnings:
            sys.stderr.write('Warnings:\n')
            data = []
            for warn in warnings:
                data.append('  ' + reindent(MAGSBS.common.format_warning(warn)))
            sys.stderr.write(''.join(data).rstrip() + '\n')

    def _format_indented_line(self, line, prefix, indent):
        """Format a overlong line so that:
        * the prefix is indented with the given indent
        * all subsequent lines have indentation indent + 2
        * the first line consists of indent + key + ": " + the rest filled with
          words
        """
        if line and not isinstance(line, str):
            line = str(line)
        prefix = ' ' * indent + prefix
        indent = indent + 2 # indent subsequent lines with indent + 2
        t = textwrap.TextWrapper(width=matuc_impl.getTerminalSize()[0] - indent,
                initial_indent=prefix)
        lines = t.wrap(line)
        return [lines[0]] + ['\n{}{}'.format(' ' * indent, l) for l in lines[1:]]

    def format_recursive(self, obj, indent):
        """Format a JSON-alike structure (dicts and lists containing dicts,
        lists, strings or integers) to a nice and structured text
        version."""
        if not obj:
            return []
        elif isinstance(obj, (str, bool, float, int)):
            return self._format_indented_line(obj, '', indent) \
                    + ['\n']
        elif isinstance(obj, (list, tuple)): # format head of list, then tail
            # avoid too deep recursion (is there a nicer solution?)
            data = []
            for item in obj:
                data.append(self.format_recursive(item, indent))
            return data
        elif isinstance(obj, dict):
            if 'verbatim' in obj: # do not format verbatim strings
                return [' ' * indent, # reindent, but keep verbatim otherwise:
                        ('\n' + ' ' * indent).join(obj['verbatim'].split('\n')),
                        '\n']
            data = []
            for key, value in obj.items():
                # no line break, display as key: value
                if isinstance(value, (str, int, bool, float)):
                    data += self._format_indented_line(str(value),
                            key + ': ', indent) + ['\n']
                else: # format key + \n + value (recursive)
                    data += [' ' * (indent), key, ':', '\n']
                    data += self.format_recursive(value, indent + 2)
            return data

    def emit_result(self, result):
        self.__emit_warnings()
        text = ''.join(flatten(self.format_recursive(result, 0)))
        if not text.endswith('\n'):
            text += '\n'
        sys.stdout.write(text)

    def emit_error(self, error):
        if isinstance(error, str):
            error = {'verbatim': error}
        else:
            message = error.pop('message')
            error['message'] = {'verbatim': message}
        error = {'error': error}
        sys.stderr.write(''.join(flatten(self.format_recursive(error, 0))) + '\n')

    def emit_usage(self, usage, error=None):
        if error:
            if not error.lower().startswith('error'):
                error = 'Error: ' + error
            print(error.rstrip(), end='\n\n')
        print(usage)

    def clear(self):
        """Clear the screen. There is no easy cross-platform way, so try to use
        cls/clear."""
        if sys.platform.startswith('win'):
            os.system('cmd /c cls')
        elif shutil.which('clear'):
            os.system('clear')
        else:
            print("\n" + "-" * matuc_impl.getTerminalSize()[0])
            if 'linux' in sys.platform:
                self.register_warning({'message': ("The `clear` command was not"
                    " found, install it, i.e. with `apt-get install ncurses-bin`.")})




if __name__ == '__main__':
    main_inst = matuc_impl.main(TextFormatter())
    main_inst.run(sys.argv)
