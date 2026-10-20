"""Control de calidad de un CSV del SAE antes de usarlo en los informes.

Uso (desde scripts/):
    python revisar_csv.py                 (revisa el CSV más nuevo de fuentes/ o Descargas)
    python revisar_csv.py --csv RUTA
    python revisar_csv.py --crear-referencia   (guarda columnas y valores del CSV actual como "conocidos")

Imprime un informe en texto y lo guarda en informes/controles/.
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import re
import statistics
import sys

import cobertura
import sae
from generar_informe import csv_mas_nuevo

BASE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(BASE, '..', 'catalogo', 'valores_conocidos.json')
EQUIV = os.path.join(BASE, '..', 'catalogo', 'equivalencias_barrios.csv')
SALIDA = os.path.join(BASE, '..', 'informes', 'controles')
csv.field_size_limit(10**9)

# Columnas que usa el generador: si falta alguna, los informes no se pueden hacer
CRITICAS = ['Suceso ID', 'Cuadricula', 'Comuna', 'Resultado', 'Tipo y Subtipo', 'Fecha Creacion', 'lat.long',
            'aprehendidos totales', 'mayores aprehendidos', 'menores aprehendidos', 'masculinos aprehendidos',
            'femeninas aprehendidas'] + [c for _, c in sae.SECUESTROS]
MOJIBAKE = re.compile(r'Ã.|Â.')


def fix(s):
    return sae._fix(s, True)


def leer(path):
    with open(path, encoding='utf-8', errors='replace', newline='') as f:
        r = csv.reader(f)
        h = [fix(x).strip() for x in next(r)]
        filas = list(r)
    return h, filas


def crear_referencia(path):
    h, filas = leer(path)
    ix = {k: i for i, k in enumerate(h)}
    col = lambda c: sorted({fix(x[ix[c]].strip()) for x in filas if len(x) == len(h) and x[ix[c]].strip()})
    ref = {'creado': dt.datetime.now().isoformat(timespec='minutes'), 'csv': os.path.basename(path), 'columnas': h,
           'resultados': col('Resultado'), 'comunas': col('Comuna'), 'tipos': col('Tipo y Subtipo')}
    with open(REF, 'w', encoding='utf-8') as f:
        json.dump(ref, f, ensure_ascii=False, indent=1)
    print(f'Referencia guardada en {REF}: {len(h)} columnas, {len(ref["tipos"])} tipologías, {len(ref["comunas"])} comunas.')


def revisar(path):
    ref = json.load(open(REF, encoding='utf-8')) if os.path.exists(REF) else None
    crit = cobertura.criterios()
    reg = crit['region_cordoba']
    h, filas = leer(path)
    out, graves, avisos = [], [], []
    p = out.append
    p(f'CONTROL DEL CSV DEL SAE\nArchivo: {path}\nRevisado: {dt.datetime.now():%d/%m/%Y %H:%M}\n')

    # 1. Estructura
    p('1. ESTRUCTURA')
    faltan = [c for c in CRITICAS if c not in h]
    if faltan:
        graves.append(f'Faltan columnas necesarias para los informes: {faltan}')
    if ref:
        nuevas = [c for c in h if c not in ref['columnas']]
        quitadas = [c for c in ref['columnas'] if c not in h]
        if nuevas: avisos.append(f'Columnas nuevas: {nuevas}')
        if quitadas: avisos.append(f'Columnas que ya no vienen: {quitadas}')
        if not nuevas and not quitadas and h != ref['columnas']:
            avisos.append('Las columnas cambiaron de orden (no afecta, se leen por nombre).')
    desparejas = sum(1 for x in filas if len(x) != len(h))
    p(f'   {len(h)} columnas, {len(filas):,} filas. Filas con cantidad de columnas distinta: {desparejas}'.replace(',', '.'))
    if desparejas:
        avisos.append(f'{desparejas} filas tienen una cantidad de columnas distinta (posible CSV dañado o editado a mano).')
    if faltan:
        p('   ✗ ' + graves[-1])
        return out, graves, avisos
    ix = {k: i for i, k in enumerate(h)}
    filas = [x for x in filas if len(x) == len(h)]
    g = lambda x, c: x[ix[c]].strip()

    # 2. Fechas
    p('\n2. FECHAS')
    fechas, malas, excel = [], 0, 0
    for x in filas:
        v = g(x, 'Fecha Creacion')
        try:
            fechas.append(sae._fecha(v))
        except (ValueError, IndexError):
            malas += 1
            excel += v.startswith('#')
    if malas:
        avisos.append(f'{malas} sucesos con Fecha Creacion ilegible ({excel} con "#####", típico de abrir y guardar el CSV en Excel). No se cuentan en los informes.')
    f0, f1 = min(fechas), max(fechas)
    p(f'   Cubre del {f0:%d/%m/%Y %H:%M} al {f1:%d/%m/%Y %H:%M}')
    por_dia = collections.Counter(f.date() for f in fechas)
    huecos = [f0.date() + dt.timedelta(days=i) for i in range((f1.date() - f0.date()).days + 1)
              if por_dia[f0.date() + dt.timedelta(days=i)] == 0]
    if huecos:
        avisos.append(f'Días sin ningún suceso: {", ".join(d.strftime("%d/%m/%Y") for d in huecos[:15])}{" …" if len(huecos) > 15 else ""}')
    ult = f1.date()
    previos = [por_dia[ult - dt.timedelta(days=i)] for i in range(1, 15) if por_dia[ult - dt.timedelta(days=i)]]
    if previos and por_dia[ult] < 0.6 * statistics.median(previos):
        avisos.append(f'El último día ({ult:%d/%m/%Y}) tiene {por_dia[ult]} sucesos contra ~{int(statistics.median(previos))} habituales: '
                      f'el export parece cortado ese día (último suceso {f1:%H:%M}).')
    tel_sci = sum(1 for x in filas if 'E+' in g(x, 'Telefono Denunciante')) if 'Telefono Denunciante' in ix else 0
    arr_excel = sum(1 for x in filas if g(x, 'Fecha Arribo').startswith('#')) if 'Fecha Arribo' in ix else 0
    if tel_sci or arr_excel:
        avisos.append(f'Señales de que el CSV pasó por Excel o Google Sheets: {tel_sci} teléfonos en notación científica, {arr_excel} fechas de arribo "#####". '
                      'Conviene pasar el CSV tal como sale del SAE.')

    # 3. Duplicados y codificación
    p('\n3. DUPLICADOS Y TEXTO')
    ids = collections.Counter(g(x, 'Suceso ID') for x in filas)
    rep = {k: v for k, v in ids.items() if v > 1}
    p(f'   Suceso ID repetidos: {len(rep)} (se toma una sola vez cada uno)')
    moj = sum(1 for x in filas if MOJIBAKE.search(x[ix['Tipo y Subtipo']]))
    p(f'   Tipologías con acentos mal codificados: {moj} (se corrigen solas)')

    # 4. Datos de ubicación
    p('\n4. UBICACIÓN')
    sin_com = sum(1 for x in filas if not g(x, 'Comuna'))
    sin_cua = [x for x in filas if not g(x, 'Cuadricula')]
    sin_coord, fuera_reg = 0, 0
    coords = {}
    for i, x in enumerate(filas):
        try:
            lat, lon = map(float, g(x, 'lat.long').split(','))
            if reg['lat_min'] < lat < reg['lat_max'] and reg['lon_min'] < lon < reg['lon_max']:
                coords[i] = (lat, lon)
            else:
                fuera_reg += 1
        except ValueError:
            sin_coord += 1
    n = len(filas)
    pct = lambda k: f'{k:,} ({k * 100 / n:.1f}%)'.replace(',', '.')
    p(f'   Sin Comuna (DJP): {pct(sin_com)} | sin Cuadrícula: {pct(len(sin_cua))} | sin coordenada: {pct(sin_coord)} | coordenada fuera de Córdoba: {fuera_reg}')
    if fuera_reg:
        avisos.append(f'{fuera_reg} sucesos con coordenada fuera de la región de Córdoba (dato mal cargado): no aparecen en los mapas.')

    cob = cobertura.Cobertura()
    idx = {id(x): i for i, x in enumerate(filas)}
    dentro = collections.Counter()
    barrios_dentro = collections.Counter()
    for x in sin_cua:
        i = idx[id(x)]
        if i not in coords:
            continue
        try:
            fecha = sae._fecha(g(x, 'Fecha Creacion')).date()
        except (ValueError, IndexError):
            continue
        if cob.cubierto(*coords[i], fecha):
            dentro[fecha.strftime('%Y-%m')] += 1
            barrios_dentro[cob.barrio_en(*coords[i])[0]] += 1
    p(f'   Sin cuadrícula pero dentro de la zona que cubría el programa en su fecha (ampliación: {cob.fecha_ampliacion:%d/%m/%Y}):')
    for mes in sorted(dentro)[-6:]:
        p(f'      {mes}: {dentro[mes]}')
    if barrios_dentro:
        p('      Barrios donde más pasa: ' + ', '.join(f'{b} ({v})' for b, v in barrios_dentro.most_common(8)))
    meses = sorted(dentro)
    if len(meses) >= 3:
        ult3 = [dentro[m] for m in meses[-4:-1]]
        if dentro[meses[-1]] > 1.5 * statistics.mean(ult3) + 20:
            avisos.append(f'En {meses[-1]} subieron los sucesos sin cuadrícula dentro de la zona ({dentro[meses[-1]]} contra ~{int(statistics.mean(ult3))}): '
                          'puede que no se esté cargando la cuadrícula.')

    # 5. Valores nuevos
    p('\n5. VALORES NUEVOS (respecto de la referencia)')
    if ref:
        for col, clave in (('Resultado', 'resultados'), ('Comuna', 'comunas'), ('Tipo y Subtipo', 'tipos')):
            nuevos = collections.Counter(fix(g(x, col)) for x in filas if g(x, col) and fix(g(x, col)) not in ref[clave])
            if nuevos:
                lst = ', '.join(f'{k} ({v})' for k, v in nuevos.most_common(10))
                p(f'   {col}: {lst}')
                (avisos if col != 'Tipo y Subtipo' else out).append(f'{col} con valores nuevos: {lst}' if col != 'Tipo y Subtipo' else '')
        out[:] = [l for l in out if l != '']
    else:
        p('   (no hay referencia guardada: correr con --crear-referencia)')
    conocidas = {r[0] for r in csv.reader(open(EQUIV, encoding='utf-8-sig'), delimiter=';')}
    nuevas_cua = collections.defaultdict(collections.Counter)
    for i, x in enumerate(filas):
        c = g(x, 'Cuadricula')
        if c and c not in conocidas:
            b = cob.barrio_en(*coords[i]) if i in coords else None
            nuevas_cua[c][b[0] if b else '(fuera de los 234)'] += 1
    if nuevas_cua:
        p('   Cuadrículas que no están en la tabla de equivalencias (no afectan los PDF; sí las consultas por barrio):')
        for c, cnt in sorted(nuevas_cua.items(), key=lambda kv: -sum(kv[1].values()))[:15]:
            b, v = cnt.most_common(1)[0]
            p(f'      "{c}" ({sum(cnt.values())} sucesos) → por coordenada parece {b} ({v * 100 // sum(cnt.values())}%)')
        avisos.append(f'{len(nuevas_cua)} nombres de cuadrícula nuevos para revisar y agregar a las equivalencias.')
    else:
        p('   Cuadrículas: todas conocidas.')

    # 6. Coherencia de aprehendidos
    p('\n6. COHERENCIA DE APREHENDIDOS')
    num = sae._num
    edad = sum(1 for x in filas if num(g(x, 'aprehendidos totales')) != num(g(x, 'mayores aprehendidos')) + num(g(x, 'menores aprehendidos')))
    gen = sum(1 for x in filas if num(g(x, 'aprehendidos totales')) != num(g(x, 'masculinos aprehendidos')) + num(g(x, 'femeninas aprehendidas')))
    p(f'   Total ≠ mayores + menores: {edad} | total ≠ masculinos + femeninas: {gen}')
    if edad or gen:
        avisos.append(f'Aprehendidos inconsistentes: {edad} sucesos por edad y {gen} por género. Los informes suman cada columna por separado, '
                      'así que el total puede no coincidir con mayores + menores.')

    # 7. Volumen
    p('\n7. VOLUMEN MENSUAL')
    vol = collections.Counter(f.strftime('%Y-%m') for f in fechas)
    p('   ' + ' | '.join(f'{m}: {vol[m]:,}'.replace(',', '.') for m in sorted(vol)[-6:]))
    return out, graves, avisos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv')
    ap.add_argument('--crear-referencia', action='store_true')
    a = ap.parse_args()
    path = os.path.abspath(a.csv) if a.csv else csv_mas_nuevo()
    if a.crear_referencia:
        return crear_referencia(path)
    out, graves, avisos = revisar(path)
    res = ['\nRESULTADO']
    if graves:
        res += ['   ✗ NO SE PUEDEN HACER INFORMES CON ESTE CSV:'] + [f'     - {x}' for x in graves]
    if avisos:
        res += ['   ⚠ Para revisar:'] + [f'     - {x}' for x in avisos]
    if not graves and not avisos:
        res.append('   ✓ Sin problemas. Se puede usar.')
    texto = '\n'.join(out + res)
    print(texto)
    os.makedirs(SALIDA, exist_ok=True)
    nombre = f'control {os.path.splitext(os.path.basename(path))[0]} {dt.datetime.now():%Y-%m-%d %H%M}.txt'
    with open(os.path.join(SALIDA, nombre), 'w', encoding='utf-8') as f:
        f.write(texto)
    sys.exit(2 if graves else 0)


if __name__ == '__main__':
    main()
