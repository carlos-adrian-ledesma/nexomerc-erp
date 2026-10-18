@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo NEXOMERC ERP DEMO - INSTALACION DE DEPENDENCIAS
echo ================================================
if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual local...
  py -3.13 -m venv .venv
  if errorlevel 1 (
    echo Python 3.13 no disponible. Intentando Python 3.12...
    py -3.12 -m venv .venv
    if errorlevel 1 goto :python_error
  )
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :pip_error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :pip_error
".venv\Scripts\python.exe" -c "import PySide6; print('PySide6', PySide6.__version__)"
if errorlevel 1 goto :pip_error
echo.
echo Instalacion completa. Ejecuta INICIAR_DEMO_WINDOWS.bat.
pause
exit /b 0
:python_error
echo ERROR: instala Python 3.13 o 3.12 de 64 bits desde python.org.
pause
exit /b 1
:pip_error
echo ERROR: la instalacion no termino correctamente. Revisa la salida anterior.
pause
exit /b 1
