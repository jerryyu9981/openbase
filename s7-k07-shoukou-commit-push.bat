@echo off
setlocal
set "SYS=%SystemRoot%\System32"
if not exist "%SYS%\cmd.exe" set "SYS=C:\Windows\System32"
if exist "%SYS%\chcp.com" "%SYS%\chcp.com" 65001 >nul 2>&1
cd /d "%~dp0"
set "PS=%SYS%\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"
echo ============================================================
echo  OpenBase S7 K07 gate closure - one-shot commit ^& push
echo  (add -^> commit -^> push origin/backup -^> verify)
echo  scope: gate evidence 2 + docs 4 + s7 assertion tests 2 + script 2
echo ============================================================
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\s7_k07_shoukou_commit_push.ps1" %*
echo.
pause
