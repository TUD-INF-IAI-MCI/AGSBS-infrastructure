NOTE: This file was writtenusing Pandoc's MarkDown. If you are viewing this file
on GitHub or with a non-Pandoc-compliant version of Markdown, it is likely that
some formatting is lost.


Matuc JSON API
==============

The MAGSBS JSON API allows programs to interact with the MAGSBS module, even if they are knot Python programs themselves. The next section will define how the format should look like and is followed by an example.

Specification
-------------

In the following specification, an array is a list of elements, i.e. `[element1, ...]` and a mapping refers to JSON objects with keys and values like `{key : value, ...}`.

One special exception are mappings / dictionaries with the key "verbatim". This
indicates that verbatim text is supplied. This means that the string may not be
re-formatted for the user. So while it might be desirable to re-format some
message produced by Mistkerl, verbatim (e.g. table of contents) may not be
reformatted. Example: `[{'verbatim: '\n123\n'}, ...]`.

JSON output is obtained by using the command `matuc_js`. It works exactly like
`matuc`.

There are four top-level keys which can occur within the JSON output. They are
discussed in the subsequent sections.

### `usage`

The usage is printed whenever it was requested (i.e. `-h`) or when the program
was used incorrectly. The value is a simple string with the usage information.

### `warnings`  

Warnings may occur at any time during the execution. However they do not halt the program. It is possible to omit this key, but if present, it MUST be presented to the user.

The value of this key is a list and contains mappings as its elements. An element mapping specifies a warning in more detail. Possible keys are `message`, `line` and `path`, where `message` is mandatory.

### `error`

Errors always preempt the execution premature and MUST be displayed to the user with a dedicated dialog (or similar UI element).

An error is a mapping of the following keys:

#### `message`  

The error message, mandatory.

#### `line`

The line of a document where the error occurred, optional.

#### `path`

The path to the document where the error occurred.

#### traceback

This will contain the internal traceback. It should not be directly displayed to
the user, but available using an appripriate method, i.e. a button "details"
opening the traceback so that the user can copy the traceback to report the bug.

### `result`

This is a mapping providing execution results. It is not used by all subcommands. The keys and the value formats differ from subcommand to subcommand.

For subcommands not outputting anything, the return code of the program shall be used as an indicator of success.

#### Subcommand Specification

All subcommands listed here output a `result` mapping. The others will not
output anything upon success and use the fields above to report problems.

`conf`
:   This subcommand allows the alteration of the configuration file (used to
    populate the meta information in the HTML files).  
    The result contains a key "New settings" mapping to another mapping with
    the configuration values.  
    Each key in the configuration value omapping represents an option which can
    be set using `matuc(_js) conf`.

    Example: `{'result': {'new settings': {'creator': 'me, ...}}}`
    
`fixpnums`
:   This command will check whether the page numbering increases by one per page
    and will offer reformatted page number strings, if a problem has been detected.
    Output is as follows:

    1.  If no problems have been detected, result is an empty list.
    2.  If a problem has been found:
        The result will contain a list of objects (python dictionaries),
        which represent the page number to update. The key is the line number
        (counting from one) which to update and the value is the literal string
        to insert. The replacement rules are as follows:

        -   Roman and arabic numbers are kept, a change between those two
            formats is detected.
        -   Only page numbers which changed are listed.
        -   Example: `[…, {538, "|| - Slide 98 -"}, …]`
        -   As can be seen from the example, the old line can be completely
            replaced through the new one.
`imgdsc`
:   The imgdsc command will output a mapping containing either one or two keys:

    -   One key, if the image description is not outsourced and the key will be
        'internal' and the value the string to be inserted in the document being
        edited.
    -   Two keys, when the image description is outsourced. The key 'internal'
        will then map to the image and a link referencing the xternal image
        description which is found with the key 'external'. The value of
        'external' must be appended to the file with the outsourced image
        descriptions, at the time of writing that's "bilder.md".

`iswithinlecture` (check, whether certain path is part of a lecture)
:   The `result` key will contain a JSON object with exactly one key, which is
    "is within a lecture" and the corresponding value true or false.
`mk` (the Mistkerl)
:   The Mistkerl command provides a mapping of paths to a list of mistakes. A
    Mistake can be:
    
    1.  a Message containing the string to be outputted to the user.
    2.  a mapping with the position in the file as key and the mistake message
        as a value.

    Example: 
    
    ~~~~
    {"k01/k01.md": [
      {"1": "something's wrong"},
      {"2, 18": "invalid formula"}
      "something applying in general"]
    }
    ~~~~



Complete Example
----------------

This is an example of a full output as it might occur after a run of `matuc mk .`.

    {
      "warnings": [
        {
          "line": 5,
          "path": ".lecture_metadata.dcxml",
          "message": "source author not set"
        }
      ],
      'result': {'k01/k01.md': [
          {"97": "some descriptive Mistkerl error message"},
          {"97, 1": "some other error on the same line."},
          ...
        ]
      }
    }

