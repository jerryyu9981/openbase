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
echo  OpenLLM K07 openapi snapshot drop-in - one-shot commit and push
echo  (validate 351 ops - copy to backend/data - commit - push x3 - verify)
echo  note: OpenLLM is read-only inside sandbox; run this in a writable env
echo ============================================================
"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\openllm_k07_snapshot_commit_push.ps1" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo [WARN] script exit code = %RC%
pause
exit /b %RC%
