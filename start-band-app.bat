@echo off
rem Start the band screening app (Windows). Double-click this file.
rem It runs, from this folder:  python -m physicroll.band_app --runs-dir band-app-runs
rem and keeps the window open if something goes wrong.
setlocal
cd /d "%~dp0"

set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo Python 3.10 or newer was not found.
    echo Install Python 3.10 or newer from python.org ^(tick "Add python.exe to PATH"^),
    echo then double-click this file again.
    echo.
    pause
    exit /b 1
)

echo Starting the band screening app with %PY%. Close this window or press Ctrl-C to stop it.
%PY% -m physicroll.band_app --runs-dir band-app-runs
if errorlevel 1 (
    echo.
    echo The band app stopped with an error. The message above says why.
    echo.
    pause
    exit /b 1
)
endlocal
