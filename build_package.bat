@echo off
setlocal
pushd "%~dp0"

echo Ensuring the build backend is installed...
py -3.13 -m pip install --upgrade build || goto :error

echo.
echo Building run-hy8 distributions...
py -3.13 -m build || goto :error

echo.
echo Build artifacts available under "%~dp0dist".
popd
endlocal
exit /b 0

:error
popd
endlocal
exit /b 1
