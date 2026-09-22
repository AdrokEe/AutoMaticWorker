@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing. Follow docs\QUICKSTART.md first.
  pause
  exit /b 1
)
if not exist "vue_frontend\dist\index.html" (
  echo Frontend missing. Run npm ci --prefix vue_frontend and npm run build --prefix vue_frontend.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
