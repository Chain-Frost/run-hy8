@echo off
setlocal
pushd "%~dp0"

if "%~1"=="" (
    set "PYTEST_ARGS=tests -v"
) else (
    set "PYTEST_ARGS=%*"
)

py -3.13 -m pytest %PYTEST_ARGS%
set "EXIT_CODE=%ERRORLEVEL%"

popd
endlocal
exit /b %EXIT_CODE%
