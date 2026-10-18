@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No se encuentra el entorno virtual de NexoMerc.
  echo Ejecuta primero INSTALAR_DEMO_WINDOWS.bat.
  pause
  exit /b 1
)
set "NEXOMERC_DATA_DIR=%~dp0data\demo_local"
if not exist "%NEXOMERC_DATA_DIR%" mkdir "%NEXOMERC_DATA_DIR%"
echo Abriendo NexoMerc ERP DEMO con datos aislados...
".venv\Scripts\python.exe" run.py
if errorlevel 1 (
  echo.
  echo ERROR: NexoMerc no pudo finalizar normalmente. Revisa el mensaje anterior.
  pause
  exit /b 1
)
exit /b 0
