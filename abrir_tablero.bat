@echo off
chcp 65001 >nul
echo Actualizando los datos del tablero con el CSV mas nuevo del SAE...
pushd "%~dp0scripts"
python preparar_tablero.py
popd
start "" "%~dp0tablero\index.html"
