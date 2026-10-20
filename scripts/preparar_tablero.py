"""Prepara los datos del tablero interactivo (tablero/datos.js) a partir del CSV del SAE.

Uso (desde scripts/):
    python preparar_tablero.py              (CSV más nuevo de fuentes/ o Descargas)
    python preparar_tablero.py --csv RUTA

Solo guarda lo que el tablero necesita (fecha, DJP, resultado, tipología, coordenada, aprehendidos y secuestros):
no incluye teléfonos, nombres, relatos ni usuarios. Igual queda fuera del repositorio (ver .gitignore).
"""
import argparse
import datetime as dt
import json
import os

import sae
from generar_informe import csv_mas_nuevo

BASE = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(BASE, '..', 'tablero', 'datos.js')
EPOCA = dt.datetime(2020, 1, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv')
    a = ap.parse_args()
    path = os.path.abspath(a.csv) if a.csv else csv_mas_nuevo()
    lo, hi = sae.rango_fechas(path)
    suc = sae.cargar(path, lo.date(), hi.date())
    djps = sae.DJP_INFORME + [sae.FUERA]
    tipos = sorted({s['tipo'] for s in suc})
    ti = {t: i for i, t in enumerate(tipos)}
    cols = {k: [] for k in ['t', 'd', 'p', 'y', 'la', 'lo', 'ap', 'ma', 'me', 'm', 'f',
                            'fuego', 'blancas', 'estupefacientes', 'vehiculos', 'otros']}
    for s in sorted(suc, key=lambda s: s['fecha']):
        cols['t'].append(int((s['fecha'] - EPOCA).total_seconds() // 60))
        cols['d'].append(djps.index(s['djp']))
        cols['p'].append(int(s['positivo']))
        cols['y'].append(ti[s['tipo']])
        cols['la'].append(round(s['lat'] * 1e5) if s['lat'] is not None else 0)
        cols['lo'].append(round(s['lon'] * 1e5) if s['lon'] is not None else 0)
        for k, c in [('ap', 'aprehendidos'), ('ma', 'mayores'), ('me', 'menores'), ('m', 'masculinos'), ('f', 'femeninas'),
                     ('fuego', 'fuego'), ('blancas', 'blancas'), ('estupefacientes', 'estupefacientes'),
                     ('vehiculos', 'vehiculos'), ('otros', 'otros')]:
            cols[k].append(s[c])
    datos = {
        'generado': dt.datetime.now().strftime('%d/%m/%Y %H:%M'),
        'csv': os.path.basename(path),
        'desde': lo.strftime('%Y-%m-%d'), 'hasta': hi.strftime('%Y-%m-%d %H:%M'),
        'epoca': EPOCA.strftime('%Y-%m-%dT%H:%M:%S'),
        'djps': djps, 'tipos': tipos, 'n': len(suc), 'cols': cols,
    }
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, 'w', encoding='utf-8') as f:
        f.write('window.SAE = ')
        json.dump(datos, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    print(f'{len(suc):,} sucesos del {lo:%d/%m/%Y} al {hi:%d/%m/%Y %H:%M} → {os.path.abspath(DESTINO)} '
          f'({os.path.getsize(DESTINO) / 1e6:.1f} MB)'.replace(',', '.'))


if __name__ == '__main__':
    main()
