@echo off

rem assume that python is on the path
rem echo "Executing tests (will only work if Python is on the path)"

python -m unittest discover tests
