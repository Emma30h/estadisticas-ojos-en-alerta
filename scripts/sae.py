"""Lectura del CSV del SAE y cálculo de indicadores para los informes."""
import csv
import datetime as dt
from collections import Counter

csv.field_size_limit(10**9)

# DJP que aparecen en los informes, en el orden de las páginas
DJP_INFORME = ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15',
               '17', '19', '20', '21', '22', '23', '24']
FUERA = 'FUERA DE CUADRANTE'

SECUESTROS = [('fuego', 'armas de fuego secuestradas'), ('blancas', 'armas blancas secuestradas'),
              ('estupefacientes', 'estupefacientes secuestrados'), ('vehiculos', 'vehículos secuestrados'),
              ('otros', 'otros elementos secuestrados')]


def _fix(s, corregir):
    """El CSV trae texto con doble codificación (ej. 'RIÃ‘A'). Se corrige salvo que se pida lo contrario."""
    if not corregir:
        return s
    for cod in ('cp1252', 'latin1'):
        try:
            return s.encode(cod).decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return s


def _num(v):
    v = (v or '').strip().rstrip('|').replace(',', '.')
    try:
        return int(float(v))
    except ValueError:
        return 0


def _fecha(s):
    d, m, rest = s.strip().split('/', 2)
    y, h = rest.split(' ')
    hh, mm = h.split(':')[:2]
    return dt.datetime(int(y), int(m), int(d), int(hh), int(mm))


def rango_fechas(path):
    """Primera y última Fecha Creacion del CSV, para avisar si no cubre el período pedido."""
    lo = hi = None
    with open(path, encoding='utf-8', errors='replace', newline='') as f:
        r = csv.reader(f)
        h = [_fix(x, True) for x in next(r)]
        i = h.index('Fecha Creacion')
        for x in r:
            try:
                fc = _fecha(x[i])
            except (ValueError, IndexError):
                continue
            lo = fc if lo is None or fc < lo else lo
            hi = fc if hi is None or fc > hi else hi
    return lo, hi


def cargar(path, desde, hasta, corregir_texto=True):
    """Devuelve los sucesos del período [desde, hasta] (fechas inclusive), sin IDs repetidos."""
    out, vistos = [], set()
    with open(path, encoding='utf-8', errors='replace', newline='') as f:
        r = csv.reader(f)
        h = [_fix(x, True) for x in next(r)]
        ix = {k: i for i, k in enumerate(h)}
        for x in r:
            try:
                fc = _fecha(x[ix['Fecha Creacion']])
            except (ValueError, IndexError):
                continue
            if not (desde <= fc.date() <= hasta):
                continue
            sid = x[ix['Suceso ID']]
            if sid in vistos:
                continue
            vistos.add(sid)
            comuna = x[ix['Comuna']].replace('DISTRITO', '').strip()
            cuad = x[ix['Cuadricula']].strip()
            djp = FUERA if not cuad or not comuna else comuna
            try:
                lat, lon = map(float, x[ix['lat.long']].split(','))
            except ValueError:
                lat = lon = None
            out.append({
                'fecha': fc,
                'djp': djp,
                'positivo': x[ix['Resultado']].strip() == 'Positivo',
                'tipo': _fix(x[ix['Tipo y Subtipo']].strip(), corregir_texto),
                'lat': lat, 'lon': lon,
                'aprehendidos': _num(x[ix['aprehendidos totales']]),
                'mayores': _num(x[ix['mayores aprehendidos']]),
                'menores': _num(x[ix['menores aprehendidos']]),
                'masculinos': _num(x[ix['masculinos aprehendidos']]),
                'femeninas': _num(x[ix['femeninas aprehendidas']]),
                **{k: _num(x[ix[c]]) for k, c in SECUESTROS},
            })
    # Los informes solo muestran los DJP del programa y "Fuera de Cuadrante"
    return [s for s in out if s['djp'] in DJP_INFORME or s['djp'] == FUERA]


def _top(counter, n):
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def indicadores(sucesos, n_tipo_alertas=15, n_tipo_positivos=15):
    pos = [s for s in sucesos if s['positivo']]
    # weekday(): lunes=0 … domingo=6; los informes van de domingo a sábado
    orden_dias = [6, 0, 1, 2, 3, 4, 5]
    da, dp = Counter(s['fecha'].weekday() for s in sucesos), Counter(s['fecha'].weekday() for s in pos)
    ha, hp = Counter(s['fecha'].hour for s in sucesos), Counter(s['fecha'].hour for s in pos)
    return {
        'alertas': len(sucesos),
        'positivos': len(pos),
        'aprehendidos': sum(s['aprehendidos'] for s in sucesos),
        'mayores': sum(s['mayores'] for s in sucesos),
        'menores': sum(s['menores'] for s in sucesos),
        'masculinos': sum(s['masculinos'] for s in sucesos),
        'femeninas': sum(s['femeninas'] for s in sucesos),
        'secuestros': {k: sum(s[k] for s in sucesos) for k, _ in SECUESTROS},
        'dias': [(da[d], dp[d]) for d in orden_dias],
        'horas': [(ha[h], hp[h]) for h in range(24)],
        'tipo_alertas': _top(Counter(s['tipo'] for s in sucesos), n_tipo_alertas),
        'tipo_positivos': _top(Counter(s['tipo'] for s in pos), n_tipo_positivos),
        # Placa: la lista "POSITIVOS" cuenta los sucesos con aprehendidos
        'tipo_con_aprehendidos': _top(Counter(s['tipo'] for s in sucesos if s['aprehendidos'] > 0), 15),
        'puntos': [(s['lat'], s['lon']) for s in pos if s['lat'] is not None],
        'puntos_alertas': [(s['lat'], s['lon']) for s in sucesos if s['lat'] is not None],
    }


def por_djp(sucesos):
    return {d: [s for s in sucesos if s['djp'] == d] for d in DJP_INFORME + [FUERA]}
