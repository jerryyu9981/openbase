@echo off
setlocal
cd /d "%~dp0"
set "WINDIR_ROOT=%SystemRoot%"
if "%WINDIR_ROOT%"=="" set "WINDIR_ROOT=C:\Windows"
if exist "%WINDIR_ROOT%\System32\chcp.com" "%WINDIR_ROOT%\System32\chcp.com" 65001 >nul 2>&1
set "PS=%WINDIR_ROOT%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=%WINDIR_ROOT%\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"
echo ============================================================
echo  OpenBase S7 K07 gate closure - one-shot commit and push
echo  (add - commit - push origin/backup - verify)
echo  scope: gate evidence 2 + docs 4 + s7 tests 2 + script 2
echo ============================================================
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\s7_k07_shoukou_commit_push.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo [WARN] script exit code = %RC%
pause
exit /b %RC%
