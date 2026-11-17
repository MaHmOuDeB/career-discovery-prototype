@echo off
setlocal EnableExtensions
rem Career Discovery starter for Windows. Needs no admin rights.
rem Set CD_DRY_RUN=1 to print the command that would run and exit.
cd /d "%~dp0"
if errorlevel 1 (
  set "MSG=The starter could not open its own folder."
  set "NEXT=Unzip the download again and double-click the starter inside the unzipped folder."
  goto :fail
)

set "PYCMD="
if defined CD_TEST_NO_PYTHON goto :findUv
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 set "PYCMD=py -3"
if defined PYCMD goto :runPython
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 set "PYCMD=python"
if defined PYCMD goto :runPython

:findUv
set "UV="
if defined CD_TEST_NO_UV goto :askInstall
where uv >nul 2>&1
if not errorlevel 1 set "UV=uv"
if defined UV goto :runUv
if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if defined UV goto :runUv

:askInstall
echo Career Discovery needs Python, and it is not installed on this computer.
echo This starter can install the free uv tool from astral.sh, which then downloads Python into your own folder. No admin rights are needed.
if defined CD_DRY_RUN (
  echo DRY RUN: would ask, then run: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
  exit /b 0
)
echo.
echo Press Enter to continue or close this window to cancel
pause >nul
set "UV_NO_MODIFY_PATH=1"
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
if errorlevel 1 (
  set "MSG=The uv installer did not finish."
  set "NEXT=Check your internet connection and try again, or install Python 3.12 or newer from python.org."
  goto :fail
)
if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV (
  set "MSG=uv was installed but could not be found."
  set "NEXT=Close this window and double-click the starter again."
  goto :fail
)

:runUv
if defined CD_DRY_RUN (
  echo DRY RUN in %CD%: "%UV%" run --no-project --python 3.12 -- python -B -m career_discovery app
  exit /b 0
)
"%UV%" run --no-project --python 3.12 -- python -B -m career_discovery app
goto :done

:runPython
if defined CD_DRY_RUN (
  echo DRY RUN in %CD%: %PYCMD% -B -m career_discovery app
  exit /b 0
)
%PYCMD% -B -m career_discovery app
goto :done

:done
if errorlevel 1 (
  set "MSG=The app stopped with an error."
  set "NEXT=Read the message above. If a port or file is in use, close other copies of the app and try again."
  goto :fail
)
exit /b 0

:fail
echo.
echo Something went wrong: %MSG%
echo Next step: %NEXT%
if not defined CD_DRY_RUN pause
exit /b 1
