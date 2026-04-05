@echo off
setlocal

cd /d "%~dp0"

if not exist "dev.py" (
  echo [dev][error] dev.py not found in repo root.
  echo Press any key to close this window...
  pause >nul
  exit /b 1
)

set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if not defined PYCMD where python >nul 2>nul && set "PYCMD=python"
if not defined PYCMD where python3 >nul 2>nul && set "PYCMD=python3"

if not defined PYCMD (
  echo [dev][error] Python not found. Install Python 3.10+ first.
  echo Press any key to close this window...
  pause >nul
  exit /b 1
)

echo [dev] Using %PYCMD%
echo [dev] Starting project...

%PYCMD% dev.py up
set "EXIT_CODE=%ERRORLEVEL%"

if "%EXIT_CODE%"=="0" (
  echo [dev] Project stopped normally.
) else (
  echo [dev][error] dev.py exited with code %EXIT_CODE%.
)

echo.
echo Press any key to close this window...
pause >nul
exit /b %EXIT_CODE%

