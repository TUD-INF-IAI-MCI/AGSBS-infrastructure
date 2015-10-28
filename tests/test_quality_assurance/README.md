quality assurance &mdash; Mistkerl
==================================

Normally it is advised for this project to have one test*.py per real *.py file.
For the checkers there should be one test*.py for each checker, named 
`test_<name of checker>`.

The `__init__.py` file is necessary so that the unit test discovery find all the
tests in this subdirectory.
