@echo off

rem Ruta al directorio que contiene el entorno virtual
set VENV_DIR=C:\Users\SaidJ\OneDrive\Documentos\projects\MachineTrading\code

rem Nombre del entorno virtual
set VENV_NAME=mtvenv

rem Ruta al script de Python que deseas ejecutar
set SCRIPT_PATH=C:\Users\SaidJ\OneDrive\Documentos\projects\MachineTrading\code\trading.py

rem Activa el entorno virtual
call "%VENV_DIR%\%VENV_NAME%\Scripts\activate"

rem Ejecuta el script de Python
python "%SCRIPT_PATH%"

rem Desactiva el entorno virtual
deactivate

rem Espera a que el usuario presione Enter
pause
