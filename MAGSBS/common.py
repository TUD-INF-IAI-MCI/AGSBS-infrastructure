"""Common methods and functions to ease some not MAGSBS-specific recurring
tasks."""

import sys

def warn(*args):
    """Print-compatible function; write a warning to sys.stderr. The word
    "Warning:" is prefixed."""
    if sys.stderr:
        print("Warning:", *args, file=sys.stderr)
    else:
        print("Warning:", *args)
