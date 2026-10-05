@echo off
call "%~dp0build_package.bat" %*
if errorlevel 1 exit /b %errorlevel%
call "%~dp0force_reinstall_package.bat"
exit /b %errorlevel%
