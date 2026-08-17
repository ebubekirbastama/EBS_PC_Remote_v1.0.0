@echo off
cd /d "%~dp0"
python -c "import customtkinter,mss,PIL,pyautogui,cryptography,qrcode,cv2,sounddevice,numpy,pyperclip" 2>nul || python -m pip install -r requirements.txt
powershell -NoProfile -Command "Start-Process -FilePath python -ArgumentList 'main.py' -Verb RunAs"
