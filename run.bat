@echo on

rem Ruta al directorio que contiene el entorno virtual
set VENV_DIR=C:\Users\SaidJ\OneDrive\Documentos\projects\forex_ml_bot\forex_ml_bot

rem Nombre del entorno virtual
set VENV_NAME=mtvenv

rem Ruta al script de Python que deseas ejecutar
set SCRIPT_PATH=C:\Users\SaidJ\OneDrive\Documentos\projects\forex_ml_bot\forex_ml_bot\live_trading.py

rem Activa el entorno virtual usando activate.bat
call "%VENV_DIR%\%VENV_NAME%\Scripts\activate.bat"

rem Ejecuta el script de Python
python "%SCRIPT_PATH%"

rem Esperar hasta que el usuario presione una tecla
pause
