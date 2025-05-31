@echo off
REM Activate the virtual environment and run the app

cd /d %~dp0
call .venv\Scripts\activate.bat

echo Running image cropper app...
python main.py

pause
