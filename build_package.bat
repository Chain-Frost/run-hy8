@echo off
python "%~dp0scripts\build_library.py" %*
exit /b %errorlevel%
