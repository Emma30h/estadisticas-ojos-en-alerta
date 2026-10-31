"""Arma los mensajes de WhatsApp de "Hechos ingresados a través del 911" a partir de la "Tabla de Incidentes".

Dos modelos (acordados con la usuaria el 26/10/2026):
  corto     la numérica que pidió la jefa: total de hechos, positivos y hechos/positivos por zona.
  detallado además de lo anterior, aprehendidos y, por zona, la tipificación de cada hecho.
  positivos igual que detallado, pero por zona solo la tipificación de los hechos positivos.
  numerica  (27/10/2026) un solo mensaje con dos bloques, "SUCESOS INGRESADOS A TRAVÉS DEL 911" (hechos de
            --operadores, los del 101) y "... DEL PROGRAMA CORDOBESES EN ALERTA" (el resto, Base Olimpo):
            cantidad de sucesos y sucesos por zona; en el bloque del 911 las zonas van con dos cifras (01).

Las zonas están en catalogo/zonas_mensaje.json (DJP -> zona). Los hechos sin Cuadricula van a "FUERA DE
CUADRANTE", aparte de las zonas. Si tienen Cuadricula pero la Comuna viene vacía (pasa en el SAE: el cuadrante
queda en Comisaria), el DJP sale del barrio en catalogo/equivalencias_barrios.csv (27/10/2026).

Uso (desde scripts/):
  python mensaje_whatsapp.py --operadores luca.bustamante,martina.ariza
  python mensaje_whatsapp.py --operadores "Bustamante Luca David,Ariza Martina"   # también con nombres
  python mensaje_whatsapp.py --csv "C:/ruta/Tabla de Incidentes (1).csv" --operadores ... --desde 07:00 --hasta 19:00
  python mensaje_whatsapp.py --modelo numerica --operadores luca.bustamante,martina.ariza --desde 19:00 --hasta 07:00
Si --hasta es anterior a --desde, el horario cruza la medianoche (19:00 a 07:00 del día siguiente) y --fecha es
el día en que empieza.
Con --resto se arma el de Base Olimpo: todos los hechos menos los de --operadores (los del 101).
Sin --operadores se cuentan todos los hechos de la tabla. Los .txt quedan en informes/ y se muestran por pantalla.
"""
import argparse
import csv
import datetime as dt
import glob
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter

csv.field_size_limit(10**9)
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SALIDA = os.path.join(BASE, 'informes')
DESCARGAS = os.path.join(os.path.expanduser('~'), 'Downloads')
FUERA = 'FUERA DE CUADRANTE'
BORDE_M = 10  # metros: un hecho sin barrio pegado al borde de un barrio con cobertura cuenta como dentro

# La tabla trae las tipificaciones en mayúsculas y sin tildes
ACENTOS = [('transito', 'tránsito'), ('alteracion', 'alteración'), ('publico', 'público'), ('publicos', 'públicos'),
           ('motovehiculo', 'motovehículo'), ('vehiculos', 'vehículos'), ('automovil', 'automóvil'),
           ('vehiculo', 'vehículo'), ('situacion', 'situación'), ('limpiavridos', 'limpiavidrios'),
           ('exoticos', 'exóticos'), ('via', 'vía'), ('publica', 'pública'), ('etiologia', 'etiología'), ('desaparicion', 'desaparición'),
           ('Desaparicion', 'Desaparición'), ('arboles', 'árboles'), ('caidos', 'caídos'), ('economico', 'económico'), ('obsenas', 'obscenas')]


def plural(n, uno, varios):
    return f'{n} {uno if n == 1 else varios}'


def tipo(t):
    """'EMERGENCIA DE SALUD (107) (INDIVIDUO DESCOMPUESTO)' -> 'Emergencia de salud 107 (individuo descompuesto)'."""
    m = re.match(r'(.*?) \((.*)\)$', t)
    a, b = (m.group(1).strip(), m.group(2).strip()) if m else (t.strip(), '')
    s = a.capitalize() if (not b or b.upper() == a.upper()) else a.capitalize() + ' (' + b.lower() + ')'
    s = s.replace('Emergencia de salud (107) ', 'Emergencia de salud 107 ').replace('(107) (', '107 (')
    for x, y in ACENTOS:
        s = re.sub(r'\b' + x + r'\b', y, s)
    return s


def hora_arg(s):
    h, m = s.split(':')
    return dt.time(int(h), int(m))


def csv_mas_nuevo():
    cand = glob.glob(os.path.join(DESCARGAS, 'Tabla de Incidentes*.csv'))
    if not cand:
        sys.exit('No encontré "Tabla de Incidentes*.csv" en Descargas: pasalo con --csv.')
    return max(cand, key=os.path.getmtime)


def _plano(t):
    t = unicodedata.normalize('NFD', t.lower())
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn')


def resolver_operadores(pedidos, usuarios):
    """Cada pedido puede ser un usuario del SAE ('luca.bustamante') o un nombre completo ('Bustamante Luca David').
    Un usuario 'nombre.apellido' coincide si su nombre y su apellido están entre las palabras del pedido.
    Devuelve (usuarios encontrados, pedidos que no aparecen en la tabla)."""
    por_plano = {_plano(u.strip()): u for u in usuarios if u.strip()}
    encontrados, faltan = set(), []
    for ped in pedidos:
        ped = ped.strip()
        if not ped:
            continue
        if '.' in ped and ' ' not in ped:
            hit = [u for pl, u in por_plano.items() if pl == _plano(ped)]
        else:
            palabras = set(re.split(r'\s+', _plano(ped)))
            hit = [u for pl, u in por_plano.items() if all(parte in palabras for parte in pl.split('.'))]
        if hit:
            encontrados.update(hit)
        else:
            faltan.append(ped)
    return encontrados, faltan


def cargar(path, operadores, resto=False):
    with open(path, encoding='utf-8-sig', newline='') as f:
        filas = list(csv.DictReader(f, delimiter=';'))
    for r in filas:
        r['_fc'] = dt.datetime.strptime(r['Fecha Creacion'], '%d-%m-%y %H:%M:%S')
    ultimo = max(r['_fc'] for r in filas)  # hora del último hecho de toda la tabla (cuándo se exportó)
    usados, faltan = None, []
    if operadores:
        usados, faltan = resolver_operadores(operadores, {r['Usuario Operador'] for r in filas})
        filas = [r for r in filas if (r['Usuario Operador'] in usados) != resto]
    return filas, ultimo, usados, faltan


def _barrio(t):
    return _plano(re.sub(r'^C \d+-', '', t.strip())).upper()


_DJP_BARRIO = None


def djp_del_barrio(cuadricula):
    """DJP del barrio según catalogo/equivalencias_barrios.csv ('C 2-VILLA BELGRANO' o 'VILLA BELGRANO' -> '24')."""
    global _DJP_BARRIO
    if _DJP_BARRIO is None:
        with open(os.path.join(BASE, 'catalogo', 'equivalencias_barrios.csv'), encoding='utf-8-sig', newline='') as f:
            _DJP_BARRIO = {_barrio(x['nombre_sistema']): x['distrito'] for x in csv.DictReader(f, delimiter=';')}
    return _DJP_BARRIO.get(_barrio(cuadricula))


_POLIGONOS = None


def _dentro(x, y, anillo):
    hit = False
    for (x1, y1), (x2, y2) in zip(anillo, anillo[1:] + anillo[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


# Zona de cada cuadrante (coincide con la zona por DJP en los 234 barrios del catálogo, controlado el 29/10/2026)
ZONA_CUADRANTE = {'1': 'CENTRO/OESTE', '7': 'CENTRO/OESTE', '2': 'NORTE', '3': 'ESTE', '4': 'ESTE', '8': 'ESTE',
                  '5': 'SUR', '6': 'SUR'}
KML_COBERTURA = 'SECTORES OJOS EN ALERTA.kml'   # KML actualizado que pasó la usuaria el 29/10/2026


def _cargar_kml():
    """Del KML de cobertura: perímetros de las carpetas CUADRANTE 1..8 y los barrios (carpeta "Barrios")."""
    kml = open(os.path.join(BASE, 'fuentes', KML_COBERTURA), encoding='utf-8').read()
    cuadrantes, barrios = [], []
    for carpeta in re.split(r'<Folder>', kml)[1:]:
        nombre = re.search(r'<name>(.*?)</name>', carpeta).group(1).strip()
        destino = cuadrantes if nombre.startswith('CUADRANTE') else barrios if nombre == 'Barrios' else None
        if destino is None:
            continue  # SEMC (zonas de salud)
        for pm in re.findall(r'<Placemark>(.*?)</Placemark>', carpeta, re.S):
            m = re.search(r'<name>(.*?)</name>', pm, re.S)
            etiqueta = nombre[-1] if destino is cuadrantes else (m.group(1).strip() if m else '')
            for c in re.findall(r'<outerBoundaryIs>.*?<coordinates>(.*?)</coordinates>', pm, re.S):
                destino.append((etiqueta, [tuple(map(float, p.split(',')[:2])) for p in c.split()]))
    return cuadrantes, barrios


def _cerca(lon, lat, poligonos, tope):
    """Etiqueta del polígono que contiene el punto o, si no, del más cercano a menos de `tope` metros."""
    hit = next((e for e, a in poligonos if _dentro(lon, lat, a)), None)
    if hit or not tope:
        return hit
    mx, my = 111320 * math.cos(math.radians(lat)), 110540
    mejor = None
    for e, a in poligonos:
        for (x1, y1), (x2, y2) in zip(a, a[1:] + a[:1]):
            ax, ay, bx, by = (x1 - lon) * mx, (y1 - lat) * my, (x2 - lon) * mx, (y2 - lat) * my
            L = (bx - ax) ** 2 + (by - ay) ** 2
            t = max(0, min(1, -(ax * (bx - ax) + ay * (by - ay)) / L)) if L else 0
            dist = math.hypot(ax + t * (bx - ax), ay + t * (by - ay))
            if dist <= tope and (mejor is None or dist < mejor[0]):
                mejor = (dist, e)
    return mejor[1] if mejor else None


def barrio_por_coordenada(r):
    """('C2 · VILLA BELGRANO', 'NORTE') si la coordenada cae en la cobertura (cuadrantes del KML), o None."""
    global _POLIGONOS
    if _POLIGONOS is None:
        _POLIGONOS = _cargar_kml()
    try:
        lat, lon = float(r['Latitud']), float(r['Longitud'])
    except ValueError:
        return None
    cuadrantes, barrios = _POLIGONOS
    # pegado al borde (calle límite): hasta BORDE_M metros del perímetro cuenta como dentro (acordado 28/10/2026)
    q = _cerca(lon, lat, cuadrantes, BORDE_M)
    if not q:
        return None
    return f'C{q} · {_cerca(lon, lat, barrios, 50) or "barrio sin nombre en el KML"}', ZONA_CUADRANTE[q]


_MANUALES = None


def ubicacion_manual(r):
    """Hechos ubicados a mano por la usuaria (catalogo/ubicaciones_manuales.json: Suceso ID -> barrio y DJP)."""
    global _MANUALES
    if _MANUALES is None:
        ruta = os.path.join(BASE, 'catalogo', 'ubicaciones_manuales.json')
        _MANUALES = json.load(open(ruta, encoding='utf-8')) if os.path.exists(ruta) else {}
    return _MANUALES.get(r['Suceso ID'].strip())


def comuna_confirmada(r, djp_b, zonas):
    """El barrio dice una zona, pero Comuna, Comisaria y coordenada coinciden en otra: mandan esas tres.
    Caso del SAE con dos "LAS FLORES" (C6/DJP 4 y C7/DJP 20); criterio de la usuaria del 30/10/2026."""
    zc = _zona_djp(r['Comuna'].replace('DISTRITO', '').strip(), zonas)
    if not zc or zc == _zona_djp(djp_b, zonas):
        return False
    q = r['Comisaria'].replace('CUADRANTE', '').strip()
    b = barrio_por_coordenada(r)
    return ZONA_CUADRANTE.get(q) == zc and b is not None and b[1] == zc


def zona_de(r, zonas):
    comuna = r['Comuna'].replace('DISTRITO', '').strip()
    m = ubicacion_manual(r)
    if m:
        return _zona_djp(m['djp'], zonas)
    djp_b = djp_del_barrio(r['Cuadricula']) if r['Cuadricula'].strip() else None
    if djp_b:
        if comuna_confirmada(r, djp_b, zonas):
            return _zona_djp(comuna, zonas)
        # con barrio: manda el barrio; la Comuna del SAE a veces viene vacía o mal cargada (27 y 28/10/2026)
        return _zona_djp(djp_b, zonas)
    # sin barrio (o con algo que no es barrio, ej. "COMISARIA 23B"): cuenta si la coordenada cae en la cobertura
    b = barrio_por_coordenada(r)
    return b[1] if b else FUERA


def _zona_djp(djp, zonas):
    return next((z for z, djps in zonas.items() if djp in djps), None)  # None: DJP que no está en ninguna zona


def armar(filas, zonas, fecha, desde, hasta, modelo, titulo='DEL 911'):
    n = len(filas)
    pos = sum(r['Resultado'] == 'Positivo' for r in filas)
    apre = [r for r in filas if int(r['Detenidos Totales'] or 0) > 0]
    total_apre = sum(int(r['Detenidos Totales']) for r in apre)
    por_zona = {z: [r for r in filas if zona_de(r, zonas) == z] for z in list(zonas) + [FUERA]}

    def linea(nombre, sel, con_apre):
        p = sum(r['Resultado'] == 'Positivo' for r in sel)
        a = sum(int(r['Detenidos Totales'] or 0) for r in sel)
        s = f'*{nombre}* · {plural(len(sel), "hecho", "hechos")} · {plural(p, "positivo", "positivos")}'
        return s + (f' · {plural(a, "aprehendido", "aprehendidos")}' if con_apre and a else '')

    cab = [f'*HECHOS INGRESADOS A TRAVÉS {titulo}*', '', f'*FECHA: {fecha:%d/%m/%Y}*', '',
           f'*HORARIO: {desde:%H:%M}Hs a {hasta:%H:%M}Hs*', '', f'📋 *Cantidad de Hechos:* {n}', f'✅ *Positivos:* {pos}']
    detalle = modelo in ('detallado', 'positivos')
    if detalle:
        cab.append(f'🚔 *Aprehendidos:* {total_apre}' + (f' ({plural(len(apre), "hecho", "hechos")})' if apre else ''))
    L = cab + ['', '', '*ZONA*', '']
    for nombre, sel in por_zona.items():
        L.append(linea(nombre, sel, detalle) + (' ' if modelo == 'corto' else ''))
        if detalle:
            # "positivos": solo la tipificación de los hechos con resultado Positivo
            sel_t = [r for r in sel if r['Resultado'] == 'Positivo'] if modelo == 'positivos' else sel
            for t, c in sorted(Counter(tipo(r['Tipo y Subtipo']) for r in sel_t).items(), key=lambda x: (-x[1], x[0])):
                L.append(f'  • {c} {t}')
        L.append('')
    if detalle and apre:
        L.append('*Aprehendidos:*')
        for r in apre:
            L.append(f'  • {zona_de(r, zonas).title()} · {r["Cuadricula"].title()} · {tipo(r["Tipo y Subtipo"])} · {r["Detenidos Totales"]}')
    return '\n'.join(L).strip()


def numerica(filas_101, filas_cea, zonas, fecha, desde, hasta):
    """Modelo de la jefa (27/10/2026): bloque del 911 (101) y bloque de Cordobeses en Alerta (Base Olimpo)."""
    def cuenta(sel):
        return {z: sum(zona_de(r, zonas) == z for r in sel) for z in list(zonas) + [FUERA]}

    c = cuenta(filas_101)
    L = ['*SUCESOS INGRESADOS A TRAVÉS DEL 911*', '', f'*FECHA: {fecha:%d/%m/%Y}*', '',
         f'*HORARIO: {desde:%H:%M}Hs a {hasta:%H:%M}Hs*', '', f'📋 *CANTIDAD DE SUCESOS:* {len(filas_101)}', '']
    # mismos signos en todas las líneas, como "CANTIDAD DE SUCESOS:" (pedido de la usuaria, 28/10/2026)
    for z in zonas:
        L += [f'*Z. {z}:* {c[z]:02d}', '']
    L += [f'*{FUERA}:* {c[FUERA]:02d}', '']
    c = cuenta(filas_cea)
    L += ['*SUCESOS INGRESADOS A TRAVÉS DEL PROGRAMA CORDOBESES EN ALERTA*', '',
          f'📋 *CANTIDAD DE SUCESOS:* {len(filas_cea)}', '']
    for z in zonas:
        L += [f'*Z. {z}:* {c[z]}', '']
    L += [f'*{FUERA}:* {c[FUERA]}']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--csv', help='Tabla de Incidentes (por defecto la más nueva de Descargas)')
    ap.add_argument('--operadores', help='separados por coma: usuarios del SAE (luca.bustamante) o nombres ("Bustamante Luca"); sin esto, todos')
    ap.add_argument('--resto', action='store_true', help='Base Olimpo: todos los hechos EXCEPTO los de --operadores (los del 101)')
    ap.add_argument('--desde', default='07:00', help='hora de inicio del horario (HH:MM)')
    ap.add_argument('--hasta', default='19:00', help='hora de fin del horario (HH:MM)')
    ap.add_argument('--fecha', help='AAAA-MM-DD (por defecto la de los hechos)')
    ap.add_argument('--modelo', choices=['corto', 'detallado', 'positivos', 'ambos', 'numerica'], default='ambos',
                    help='ambos = corto + detallado; numerica = 911 (101) + Cordobeses en Alerta en un mensaje')
    ap.add_argument('--csv911', help='numerica: Tabla de Incidentes exportada del SAE solo con los hechos de origen 911; '
                                     'manda sobre --operadores para armar el bloque del 911 (28/10/2026)')
    a = ap.parse_args()

    path = os.path.abspath(a.csv) if a.csv else csv_mas_nuevo()
    ops = a.operadores.split(',') if a.operadores else None
    if a.modelo == 'numerica' and (a.resto or not (ops or a.csv911)):
        sys.exit('numerica necesita --csv911 o --operadores (los del 101) y no lleva --resto: el resto va al bloque de Cordobeses en Alerta.')
    if a.resto and not ops:
        sys.exit('--resto necesita --operadores (los del 101, que se excluyen).')
    filas, ultimo, usados, faltan = cargar(path, None if a.modelo == 'numerica' else ops, a.resto)
    if a.modelo == 'numerica' and ops:
        usados, faltan = resolver_operadores(ops, {r['Usuario Operador'] for r in filas})
    ids911 = None
    if a.csv911:
        with open(a.csv911, encoding='utf-8-sig', newline='') as f:
            ids911 = {r['Suceso ID'].strip() for r in csv.DictReader(f, delimiter=';')}
        print(f'Origen 911 (--csv911): {len(ids911)} hechos', file=sys.stderr)
        if a.modelo != 'numerica':
            # corto/detallado/positivos del 911: los hechos de la exportación por origen, con los datos de la tabla completa
            filas = [r for r in filas if (r['Suceso ID'].strip() in ids911) != a.resto]
        falta = ids911 - {r['Suceso ID'].strip() for r in filas}
        if falta:
            print(f'AVISO: {len(falta)} hecho(s) del 911 no están en la tabla completa (--csv): ' + ', '.join(sorted(falta)), file=sys.stderr)
        if usados:
            ops_ids = {r['Suceso ID'].strip() for r in filas if r['Usuario Operador'] in usados}
            if ids911 - ops_ids:
                print('AVISO: del 911 pero de otro operador: ' + ', '.join(
                    f'{r["Suceso ID"]} ({r["Usuario Operador"].strip()})' for r in filas
                    if r['Suceso ID'].strip() in ids911 - ops_ids), file=sys.stderr)
            if ops_ids - ids911:
                print('AVISO: de los operadores del 101 pero NO de origen 911: ' + ', '.join(sorted(ops_ids - ids911)), file=sys.stderr)
    titulo, origen = ('DE BASE OLIMPO', 'Base Olimpo') if a.resto else ('DEL 911', '911')
    if usados is not None:
        print(('Operadores EXCLUIDOS (101): ' if a.resto else 'Operadores del 101: ' if a.modelo == 'numerica' else 'Operadores incluidos: ') + ', '.join(sorted(u.strip() for u in usados)), file=sys.stderr)
    for f in faltan:
        print(f'AVISO: "{f}" no aparece como operador en esta tabla (no cargó hechos o su usuario se escribe distinto).', file=sys.stderr)
    if not filas:
        sys.exit('No hay hechos de esos operadores en el CSV.')
    desde, hasta = hora_arg(a.desde), hora_arg(a.hasta)
    noche = hasta <= desde  # 19:00 a 07:00: termina al día siguiente
    fechas = {r['_fc'].date() for r in filas}
    if a.fecha:
        fecha = dt.date.fromisoformat(a.fecha)
    else:
        u = max(r['_fc'] for r in filas)
        fecha = u.date() - dt.timedelta(days=1) if noche and u.time() <= hasta else u.date()
        if len(fechas) > 1:
            print(f'AVISO: el CSV tiene hechos de {len(fechas)} días; uso el {fecha:%d/%m/%Y}'
                  + (' (inicio del horario nocturno).' if noche else '.'), file=sys.stderr)
    ini = dt.datetime.combine(fecha, desde)
    fin = dt.datetime.combine(fecha + dt.timedelta(days=noche), hasta)
    dentro = [r for r in filas if ini <= r['_fc'] <= fin]
    fuera_hora = [r for r in filas if r not in dentro]
    zonas = json.load(open(os.path.join(BASE, 'catalogo', 'zonas_mensaje.json'), encoding='utf-8'))

    # Controles para revisar antes de mandar
    print(f'CSV: {path}', file=sys.stderr)
    print(f'Hechos del CSV: {len(filas)} · dentro del horario: {len(dentro)}', file=sys.stderr)
    if fuera_hora:
        print(f'AVISO: {len(fuera_hora)} hechos quedan fuera del horario o del día: '
              + ', '.join(r['Suceso ID'] for r in fuera_hora), file=sys.stderr)
    sin_zona = [r for r in dentro if zona_de(r, zonas) is None]
    if sin_zona:
        print('AVISO: DJP que no está en ninguna zona (no se cuenta): '
              + ', '.join(sorted({r['Comuna'] for r in sin_zona})), file=sys.stderr)
    manuales = [(r, ubicacion_manual(r)) for r in dentro if ubicacion_manual(r)]
    if manuales:
        print(f'AVISO: {len(manuales)} hecho(s) ubicados a mano (catalogo/ubicaciones_manuales.json): '
              + ', '.join(f'{r["Suceso ID"]} ({m["barrio"]} -> DJP {m["djp"]})' for r, m in manuales), file=sys.stderr)
    con_barrio = [(r, djp_del_barrio(r['Cuadricula'])) for r in dentro
                  if r['Cuadricula'].strip() and not ubicacion_manual(r) and djp_del_barrio(r['Cuadricula'])]
    sin_comuna = [(r, d) for r, d in con_barrio if not r['Comuna'].strip()]
    if sin_comuna:
        print(f'AVISO: {len(sin_comuna)} hecho(s) con barrio pero sin Comuna: el DJP sale del barrio: '
              + ', '.join(f'{r["Suceso ID"]} ({r["Cuadricula"].strip()} -> DJP {d})' for r, d in sin_comuna), file=sys.stderr)
    confirmada = [(r, d) for r, d in con_barrio if comuna_confirmada(r, d, zonas)]
    if confirmada:
        print(f'AVISO: {len(confirmada)} hecho(s) cuyo barrio es de otra zona, pero Comuna, cuadrante y coordenada coinciden: '
              'se cuenta por la Comuna: ' + ', '.join(f'{r["Suceso ID"]} ({r["Cuadricula"].strip()}, {r["Comisaria"].strip()}, '
                                                       f'{r["Comuna"].strip()})' for r, d in confirmada), file=sys.stderr)
    otra_zona = [(r, d) for r, d in con_barrio if r['Comuna'].strip() and not comuna_confirmada(r, d, zonas)
                 and _zona_djp(r['Comuna'].replace('DISTRITO', '').strip(), zonas) != _zona_djp(d, zonas)]
    if otra_zona:
        print(f'AVISO: {len(otra_zona)} hecho(s) con una Comuna de otra zona que su barrio: se cuenta por el barrio: '
              + ', '.join(f'{r["Suceso ID"]} ({r["Cuadricula"].strip()} DJP {d}, el SAE dice {r["Comuna"].strip()})'
                          for r, d in otra_zona), file=sys.stderr)
    por_coord = [(r, barrio_por_coordenada(r)) for r in dentro
                 if not ubicacion_manual(r) and not (r['Cuadricula'].strip() and djp_del_barrio(r['Cuadricula']))]
    por_coord = [(r, b) for r, b in por_coord if b]
    if por_coord:
        print(f'AVISO: {len(por_coord)} hecho(s) sin barrio en el SAE ubicados por coordenada: '
              + ', '.join(f'{r["Suceso ID"]} ({b[0]} -> {b[1]})' for r, b in por_coord), file=sys.stderr)
    abiertos = [r for r in dentro if not r['Resultado'].strip()]
    if abiertos:
        print(f'AVISO: {len(abiertos)} hecho(s) sin finalizar (sin resultado): '
              + ', '.join(f'{r["Suceso ID"]} ({r["Tipo y Subtipo"]})' for r in abiertos), file=sys.stderr)
    if ultimo < fin and noche:
        print(f'AVISO: la tabla se exportó el {ultimo:%d/%m} a las {ultimo:%H:%M} Hs y el horario llega hasta el '
              f'{fin:%d/%m} a las {hasta:%H:%M} Hs: pueden faltar hechos.', file=sys.stderr)
    elif ultimo < fin:
        print(f'AVISO: la tabla se exportó a las {ultimo:%H:%M} Hs y el horario llega hasta las {hasta:%H:%M}: pueden faltar hechos.', file=sys.stderr)

    os.makedirs(SALIDA, exist_ok=True)
    if a.modelo == 'numerica':
        f101 = [r for r in dentro if (r['Suceso ID'].strip() in ids911 if ids911 is not None
                                      else r['Usuario Operador'] in usados)]
        msg = numerica(f101, [r for r in dentro if r not in f101], zonas, fecha, desde, hasta)
        ruta = os.path.join(SALIDA, f'Mensaje WhatsApp numerica {fecha:%d-%m-%Y} {desde:%H%M}-{hasta:%H%M}.txt')
        open(ruta, 'w', encoding='utf-8').write(msg)
        print(f'\n===== NUMÉRICA ({ruta}) =====\n{msg}')
        return
    for modelo in (['corto', 'detallado'] if a.modelo == 'ambos' else [a.modelo]):
        msg = armar(dentro, zonas, fecha, desde, hasta, modelo, titulo)
        ruta = os.path.join(SALIDA, f'Mensaje WhatsApp {origen} {modelo} {fecha:%d-%m-%Y} {desde:%H%M}-{hasta:%H%M}.txt')
        open(ruta, 'w', encoding='utf-8').write(msg)
        print(f'\n===== {modelo.upper()} ({ruta}) =====\n{msg}')


if __name__ == '__main__':
    main()
