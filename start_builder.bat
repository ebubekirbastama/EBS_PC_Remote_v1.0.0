@echo off
cd /d "%~dp0"
python -c "import customtkinter" 2>nul || python -m pip install customtkinter
python builder.py
pause
