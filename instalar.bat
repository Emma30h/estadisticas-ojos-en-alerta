@echo off
chcp 65001 >nul
echo === Instalacion de Estadisticas Ojos en Alerta ===
echo.
where python >nul 2>nul || (echo Falta Python. Instalalo desde https://www.python.org/downloads/ marcando "Add python.exe to PATH". & pause & exit /b 1)
where node >nul 2>nul || (echo Falta Node.js. Instalalo desde https://nodejs.org/ ^(version LTS^). & pause & exit /b 1)
if not exist "C:\Program Files\Google\Chrome\Application\chrome.exe" if not exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
  echo Falta Google Chrome o Microsoft Edge. & pause & exit /b 1
)
echo Instalando librerias de Python...
python -m pip install --user -r "%~dp0requirements.txt" || (echo Error instalando librerias de Python. & pause & exit /b 1)
echo Instalando el impresor de PDF...
pushd "%~dp0scripts"
call npm install --no-fund --no-audit || (popd & echo Error en npm install. & pause & exit /b 1)
popd
if not exist "%~dp0fuentes" mkdir "%~dp0fuentes"
echo.
echo Listo. Descarga el CSV del SAE (queda en Descargas) y pedile a Claude el informe.
pause
