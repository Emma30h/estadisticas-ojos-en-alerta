#!/bin/sh
# Regenera el catálogo de barrios a partir de las fuentes. Ejecutar desde la carpeta scripts/.
set -e
F=../fuentes
python -I equivalencias.py "$F/Barrios Ojos 234 (1).xlsx" "$F/234 barrios LIMITES AMPLIADOS.kml" "$F/SAE - SAE (1).csv" ../catalogo/equivalencias_barrios.csv
python -I catalogo.py "$F/Barrios Ojos 234 (1).xlsx" "$F/234 barrios LIMITES AMPLIADOS.kml" "$F/SAE - SAE (1).csv"
