@echo off
setlocal EnableDelayedExpansion
set "PROJECT_ROOT=%~dp0"
set "DIST_DIR=%PROJECT_ROOT%dist"

if not exist "%DIST_DIR%" (
    echo No "dist" directory found. Run build_package.bat first.
    exit /b 1
)

set "PACKAGE_FILE="
for /f "delims=" %%F in ('dir /b /o:-d "%DIST_DIR%\run_hy8-*.whl" 2^>nul') do (
    set "PACKAGE_FILE=%%F"
    goto :install
)

for /f "delims=" %%F in ('dir /b /o:-d "%DIST_DIR%\run-hy8-*.tar.gz" 2^>nul') do (
    set "PACKAGE_FILE=%%F"
    goto :install
)

echo No build artifact found in "%DIST_DIR%".
exit /b 1

:install
echo Installing "%PACKAGE_FILE%"...
py -3.13 -m pip install --force-reinstall "%DIST_DIR%\!PACKAGE_FILE!" || goto :error

echo.
echo run-hy8 installed from "%PACKAGE_FILE%".
endlocal
exit /b 0

:error
endlocal
exit /b 1
