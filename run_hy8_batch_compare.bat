@echo off
setlocal EnableDelayedExpansion

rem Root of the repository (trailing slash preserved by %~dp0)
set "REPO_ROOT=%~dp0"
rem Ensure we are operating from the repo root
pushd "%REPO_ROOT%" >nul

rem Configuration (adjust as needed)
set "RUN_HY8_DIR=%REPO_ROOT%"
set "INPUT_FILE=%RUN_HY8_DIR%\results-to-check.xlsx"
set "HY8_EXE=C:\Program Files\HY-8 8.00\HY864.exe"
set "OUTPUT_FILE=%RUN_HY8_DIR%\hy8_velocity_comparison.csv"
set "WORK_DIR=%RUN_HY8_DIR%\hy8_batches"
set "BATCH_SIZE=500"
set "WORKERS=12"
set "PYTHON_CMD=py -3"

if not exist "%RUN_HY8_DIR%\src\run_hy8" (
    echo [ERROR] Could not find run_hy8 sources under "%RUN_HY8_DIR%\src".
    popd >nul
    exit /b 1
)

if not exist "%INPUT_FILE%" (
    echo [ERROR] Input spreadsheet not found: "%INPUT_FILE%".
    popd >nul
    exit /b 1
)

if not exist "%HY8_EXE%" (
    echo [ERROR] HY-8 executable not found at "%HY8_EXE%".
    echo         Update HY8_EXE in run_hy8_batch_compare.bat before running again.
    popd >nul
    exit /b 1
)

rem Prepend src/ to PYTHONPATH so imports succeed without installation
if defined PYTHONPATH (
    set "PYTHONPATH=%RUN_HY8_DIR%\src;!PYTHONPATH!"
) else (
    set "PYTHONPATH=%RUN_HY8_DIR%\src"
)

echo.
echo Running HY-8 batch comparison...
echo   Input   : %INPUT_FILE%
echo   Output  : %OUTPUT_FILE%
echo   Workdir : %WORK_DIR%
echo   Batch   : %BATCH_SIZE% crossings / process
echo   Workers : %WORKERS%
echo.

%PYTHON_CMD% "%RUN_HY8_DIR%\scripts\batch_hy8_compare.py" ^
    --input "%INPUT_FILE%" ^
    --exe "%HY8_EXE%" ^
    --output "%OUTPUT_FILE%" ^
    --workdir "%WORK_DIR%" ^
    --batch-size %BATCH_SIZE% ^
    --workers %WORKERS% ^
    %*

set "EXIT_CODE=%errorlevel%"
popd >nul

if not "%EXIT_CODE%"=="0" (
    echo [ERROR] HY-8 batch comparison failed with exit code %EXIT_CODE%.
    exit /b %EXIT_CODE%
)

echo HY-8 batch comparison completed successfully.
echo Results written to "%OUTPUT_FILE%".
exit /b 0
