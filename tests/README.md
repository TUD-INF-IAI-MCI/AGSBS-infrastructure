Tests
=====

Clunky code gets even worse if it's not tested, so here we go. To help avoid
confusion, the naming scheme for test files and classes is as follows:

1.  files are named like the files in the MAGSBS-directory
2.  sub modules are ignored
3.  test cases have the same name as in the original file (except for the test
    prefix)
4.  tests should be readable, but they don't need docs
5.  `sys.path.prepend('.')` should be before any imports to import the MAGSBS
    package from the current directory, not the system wide one
