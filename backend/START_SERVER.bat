@echo off
cd /d %~dp0
echo ===================================================
echo Starting ApplyEase Backend Server
echo ===================================================
echo.
python simple_server.py
pause
