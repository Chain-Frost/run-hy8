@echo off
setlocal EnableDelayedExpansion
set "PROJECT_ROOT=%~dp0"
set "DIST_DIR=%PROJECT_ROOT%dist"
set "PYTHON_CMD=py -3"

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo Python 3 was not found by the Windows Python Launcher.
    echo Run "py -0p" to list the installed Python versions.
    exit /b 1
)

if not exist "%DIST_DIR%" (
    echo No "dist" directory found. Run build_package.bat first.
    exit /b 1
)

set "PACKAGE_FILE="
for /f "delims=" %%F in ('dir /b /o:-d "%DIST_DIR%\run_hy8-*.whl" 2^>nul') do (
    set "PACKAGE_FILE=%%F"
    goto :install
)

echo No run-hy8 wheel found in "%DIST_DIR%".
exit /b 1

:install
echo Using Python:
%PYTHON_CMD% -c "import sys; print(sys.executable)"
echo Force reinstalling "%PACKAGE_FILE%" without reinstalling dependencies...
%PYTHON_CMD% -m pip install --upgrade --force-reinstall --no-deps "%DIST_DIR%\!PACKAGE_FILE!" || goto :error

%PYTHON_CMD% -c "import importlib.metadata, run_hy8, sys; print(f'Verified run-hy8 {importlib.metadata.version(""run-hy8"")} with Python {sys.version_info.major}.{sys.version_info.minor}')" || goto :error

echo.
echo run-hy8 force reinstalled from "%PACKAGE_FILE%".
endlocal
exit /b 0

:error
echo Force reinstall failed.
endlocal
exit /b 1
