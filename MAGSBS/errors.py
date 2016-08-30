"""
Error classes to be used in the whole MAGSBS module. Ideally 90 % of all
exceptions would be caught and re-raised (if applicable) with sensible
contextual information."""

import collections
import os
import shlex

class MAGSBS_error(Exception):
    """Just a parent."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message
        self.path = None
        self.line = None

    def to_json(self, **kwargs):
        """Convert error object to json with attributes message, line and path
        (if they exist). **kwargs can be used to include more keys in the
        dictionary."""
        data = collections.OrderedDict()
        if self.path:
            data['path'] = self.path
        if self.line:
            data['line'] = self.line
        data['message'] = self.message
        if kwargs:
            data.update(kwargs)
        return data


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
        self.message = 'error while running: %s\n%s' % (self.command, message)
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
        prefix = 'in configuration'
        if self.path and os.path.exists(self.path) and os.path.isdir(self.path):
            prefix += 'from'
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
        msg = 'Erroneous structure in %s: ' % self.path
        return msg + self.message


class FormattingError(MAGSBS_error):
    """FormattingError(msg, excerpt, path=None)
    Report formatting error. It is adviced to provide a path, but it is not
    mandatory. the `excerpt` is used to show an example of where the formatting
    error occurred."""
    def __init__(self, msg, excerpt, path=None):
        self.excerpt = excerpt
        self.message = msg
        super().__init__(msg + ':' )
        if path:
            self.path = path

    def __str__(self):
        prefix = ''
        if self.path:
            prefix += 'error in ' + self.path
        return '%s: %s\nExcerpt: %s' % (prefix, self.message, self.excerpt)


