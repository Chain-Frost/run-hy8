@echo off
goto :Main

:StageProject
REM Clean and recreate the local staging area
echo Staging project under %LOCAL_STAGE_DIR%...
rmdir /s /q "%LOCAL_BUILD_ROOT%" >nul 2>&1
mkdir "%LOCAL_STAGE_DIR%" >nul 2>&1
if not exist "%LOCAL_STAGE_DIR%" (
    echo Failed to prepare local staging directory at %LOCAL_STAGE_DIR%.
    exit /b 1
)
mkdir "%LOCAL_DIST_DIR%" >nul 2>&1
if not exist "%LOCAL_DIST_DIR%" (
    echo Failed to prepare local dist directory at %LOCAL_DIST_DIR%.
    exit /b 1
)
python -c "import os, shutil; src=os.environ['PROJECT_ROOT']; dst=os.environ['LOCAL_STAGE_DIR']; ignore=shutil.ignore_patterns('.git','dist','build','disttest','__pycache__'); shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)"
if errorlevel 1 (
    echo Failed to copy project into the local staging area.
    exit /b 1
)
echo Local staging copy complete.
exit /b 0

:Main
REM packager.bat
setlocal EnableDelayedExpansion

REM Define important directories
set "PROJECT_ROOT=%~dp0"
set "PACKAGE_DIR=%PROJECT_ROOT%dist"
set "BUILD_STAGE_DIR=%PROJECT_ROOT%"
set "BUILD_OUTPUT_DIR=%PROJECT_ROOT%build"
set "USING_LOCAL_STAGE=0"

if defined RUN_HY8_STAGE_ROOT (
    set "LOCAL_BUILD_PARENT=%RUN_HY8_STAGE_ROOT%"
) else (
    if defined TEMP (
        set "LOCAL_BUILD_PARENT=%TEMP%"
    ) else (
        set "LOCAL_BUILD_PARENT=C:\temp"
    )
)
set "LOCAL_BUILD_ROOT=%LOCAL_BUILD_PARENT%\run-hy8-build"
set "LOCAL_STAGE_DIR=%LOCAL_BUILD_ROOT%\project"
set "LOCAL_DIST_DIR=%LOCAL_BUILD_ROOT%\dist"

REM Try to reserve a local workspace on C:\temp
2>nul mkdir "%LOCAL_BUILD_PARENT%"
2>nul mkdir "%LOCAL_BUILD_ROOT%"
if exist "%LOCAL_BUILD_ROOT%" (
    set "USING_LOCAL_STAGE=1"
    set "BUILD_STAGE_DIR=%LOCAL_STAGE_DIR%"
    set "BUILD_OUTPUT_DIR=%LOCAL_DIST_DIR%"
)

REM Always remove any previous packages in the repo
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"

if "%USING_LOCAL_STAGE%"=="1" (
    call :StageProject
    if errorlevel 1 (
        endlocal
        goto :EOF
    )
) else (
    echo Local staging unavailable. Building directly from %PROJECT_ROOT%.
    set "BUILD_STAGE_DIR=%PROJECT_ROOT%"
    set "BUILD_OUTPUT_DIR=%PROJECT_ROOT%build"
)

REM Ensure the build output directory is clean
echo Preparing build output at %BUILD_OUTPUT_DIR%...
if exist "%BUILD_OUTPUT_DIR%" rmdir /s /q "%BUILD_OUTPUT_DIR%"
mkdir "%BUILD_OUTPUT_DIR%" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Failed to create build output directory at %BUILD_OUTPUT_DIR%.
    endlocal
    goto :EOF
)

REM Build the wheel inside the staging directory
echo Building wheel from %BUILD_STAGE_DIR%...
pushd "%BUILD_STAGE_DIR%"
python -m pip install --upgrade build >nul 2>&1

REM Create the wheel distribution in the specified build directory
python -m build --wheel --outdir "%BUILD_OUTPUT_DIR%"
set "BUILD_EXIT=%ERRORLEVEL%"
popd

REM Check if the build was successful
if %BUILD_EXIT% neq 0 (
    echo Build failed. Please check the setup.py for errors.
    endlocal
    goto :EOF
)

REM Copy the artifacts back to the repo
echo Copying artifacts back to %PACKAGE_DIR%...
mkdir "%PACKAGE_DIR%" >nul 2>&1

REM Check if the move was successful
if %ERRORLEVEL% neq 0 (
    echo Failed to create package directory at %PACKAGE_DIR%.
    endlocal
    goto :EOF
)
set "COPIED_FILE="
for %%F in ("%BUILD_OUTPUT_DIR%\*.whl") do (
    copy "%%~fF" "%PACKAGE_DIR%\\" >nul
    if !ERRORLEVEL! neq 0 (
        echo Failed to copy %%~nxF back to the project.
        endlocal
        goto :EOF
    )
    set "COPIED_FILE=%%~nxF"
)
if not defined COPIED_FILE (
    echo No wheel was produced in %BUILD_OUTPUT_DIR%.
    endlocal
    goto :EOF
)

REM Clean up the local workspace after a successful build
if "%USING_LOCAL_STAGE%"=="1" (
    rmdir /s /q "%LOCAL_BUILD_ROOT%" >nul 2>&1
)

echo Package created and moved to %PACKAGE_DIR% successfully.
endlocal
goto :EOF
