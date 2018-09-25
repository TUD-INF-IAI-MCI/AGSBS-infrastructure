"""Error classes to be used in the whole MAGSBS module. Ideally 90 % of all
exceptions would be caught and re-raised (if applicable) with sensible
contextual information."""
# vim: set expandtab sts=4 ts=4 sw=4:
# This is free software, licensed under the LGPL v3. See the file "COPYING" for
# details.
#
# (c) 2014-2018 Sebastian Humenda <shumenda |at| gmx |dot| de>

import collections
import os
import shlex

class MAGSBS_error(Exception):
    """Just a parent."""
    def __init__(self, message, path=None, line=None, pos=None):
        self.message = message
        self.path = path
        self.line = line
        self.pos = pos
        super().__init__(str(self))

    def to_json(self, **kwargs):
        """Convert error object to json with attributes message, line and path
        (if they exist). **kwargs can be used to include more keys in the
        dictionary."""
        data = collections.OrderedDict()
        if self.path:
            data['path'] = self.path
        if self.line:
            data['line'] = self.line
        if self.pos: # position on line
            data['position'] = self.pos
        data['message'] = self.message
        if kwargs:
            data.update(kwargs)
        return data

    def __str__(self):
        fmt = lambda b, pre: ('' if not b else '%s%s' % (pre, b))
        pathlinepos = '%s%s%s' % (fmt(self.path, ''), fmt(self.line, ', '),
                fmt(self.pos, ':'))
        return '%s: %s' % (fmt(pathlinepos, ''), self.message)


class SubprocessError(MAGSBS_error):
    """SubprocessError(command, message, path)
    command     May be a string or a list like it is passed to subprocess.Popen;
                it'll be displayed in the error message.
    message     Can be either command output or a descriptive message.
    path        Directory in which the subprocess was run in. os.path.abspath is
                executed on this path.

    The error object will have attributes called command, message, path and line
    number (where the last may be None).
    """
    def __init__(self, command, message, path=os.getcwd(), line=None):
        self.command = (' '.join(map(shlex.quote, command))
                if isinstance(command, list) else command)
        self.message = _('error while running: %s\n%s') % (self.command, message)
        super().__init__(message)
        self.path = os.path.abspath(path)
        self.line = line

    def __str__(self):
        return self.message.rstrip() + '\n  Path: ' + self.path

class ConfigurationError(MAGSBS_error):
    def __init__(self, message, path, line=None):
        self.message = message
        super().__init__(message)
        self.path = path
        self.line = line

    def __str__(self):
        prefix = ''
        if self.path and os.path.exists(self.path):
            prefix = (_('in configuration from') if os.path.isdir(self.path)
                    else _('in configuration')) + ' '
        return '{} {}: {}'.format(prefix, self.path, self.message)


class StructuralError(MAGSBS_error):
    """StructuralError(msg, path)
    Structural errors like wrong file name endings, wrong directory structures,
    etc."""
    def __init__(self, msg, path):
        self.message = msg
        super().__init__(msg)
        self.path = path

    def __str__(self):
        msg = _('erroneous structure in %s: ') % self.path
        return msg + self.message


class FormattingError(MAGSBS_error):
    """FormattingError(msg, excerpt, path=None)
    Report formatting error. It is adviced to provide a path, but it is not
    mandatory. The `excerpt` is used to show an example of where the formatting
    error occurred."""
    def __init__(self, msg, excerpt, path=None, line=None):
        self.excerpt = excerpt
        self.message = msg
        super().__init__(msg + ':' + excerpt)
        self.path = path
        self.line_no = line

    def __str__(self):
        prefix = ''
        if self.path:
            prefix += _('error in {path}').format(self.path)
        if self.line_no:
            prefix += (' ' if prefix else '') + str(self.line_no)
        return '%s%s%s\nExcerpt: %s' % (prefix, (': ' if prefix else ''),
                self.message, self.excerpt)

class MathError(MAGSBS_error):
    #pylint: disable=too-many-arguments
    def __init__(self, msg, formula, path=None, line=None, pos=None,
            formula_count=None):
        self.formula = formula
        msg = '%s\n  %s' % (msg, formula)
        super().__init__(msg, path=path, line=line, pos=pos)
        self.formula_count = formula_count
