@echo off
rem MES Web UI nightly regression entry (Phase 7)
rem Called by Windows Task Scheduler at 17:00 daily, or run manually.
rem Flow: probe login -> full regression -> timestamped HTML report -> WeCom notify
rem Exit codes: 0=pass, 2=regression failed, 3=login state invalid
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
.venv\Scripts\python.exe utils\nightly_run.py %*
exit /b %errorlevel%
