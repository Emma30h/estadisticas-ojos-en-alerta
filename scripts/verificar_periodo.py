import csv, sys, collections, datetime
csv.field_size_limit(10**9)
D1, D2 = datetime.date(*map(int, sys.argv[2].split('-'))), datetime.date(*map(int, sys.argv[3].split('-')))
def fx(s):
    try: return s.encode('latin1').decode('utf-8')
    except Exception: return s
def num(v):
    v = v.strip().rstrip('|')
    try: return int(float(v.replace(',', '.')))
    except Exception: return 0
rows = []
with open(sys.argv[1], encoding='utf-8', errors='replace', newline='') as f:
    r = csv.reader(f); h = [fx(x) for x in next(r)]
    for x in r:
        d = x[h.index('Fecha Creacion')]
        try:
            dd, mm, rest = d.split('/', 2); yy, hh = rest.split(' ')
            dt = datetime.datetime(int(yy), int(mm), int(dd), int(hh.split(':')[0]), int(hh.split(':')[1]))
        except Exception: continue
        if D1 <= dt.date() <= D2: rows.append((dt, dict(zip(h, x))))
ids = collections.Counter(r['Suceso ID'] for _, r in rows)
print('Filas:', len(rows), '| IDs únicos:', len(ids), '| IDs repetidos:', sum(1 for v in ids.values() if v > 1))
seen = set(); uniq = []
for dt, r in rows:
    if r['Suceso ID'] in seen: continue
    seen.add(r['Suceso ID']); uniq.append((dt, r))
for nombre, data in (('TODAS', rows), ('ÚNICAS', uniq)):
    pos = [r for _, r in data if r['Resultado'] == 'Positivo']
    print(f"\n== {nombre}: alertas {len(data)} | positivos {len(pos)}")
    for c in ['aprehendidos totales', 'mayores aprehendidos', 'menores aprehendidos', 'masculinos aprehendidos', 'femeninas aprehendidas',
              'armas de fuego secuestradas', 'armas blancas secuestradas', 'estupefacientes secuestrados', 'vehículos secuestrados', 'otros elementos secuestrados']:
        print(f"   {c}: {sum(num(r[c]) for _, r in data)}")
dj = collections.Counter(r['Comuna'] or '(vacío)' for _, r in uniq)
djp = collections.Counter(r['Comuna'] or '(vacío)' for _, r in uniq if r['Resultado'] == 'Positivo')
print('\nPor Comuna (únicas):', sorted(((k, v, djp[k]) for k, v in dj.items()), key=lambda t: t[0]))
dn = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
print('Día:', {dn[k]: v for k, v in sorted(collections.Counter(dt.weekday() for dt, _ in uniq).items())})
print('Hora:', [collections.Counter(dt.hour for dt, _ in uniq)[i] for i in range(24)])
print('Hora pos:', [collections.Counter(dt.hour for dt, r in uniq if r['Resultado'] == 'Positivo')[i] for i in range(24)])
print('Tipología positivos:', collections.Counter(fx(r['Tipo y Subtipo']) for _, r in uniq if r['Resultado'] == 'Positivo').most_common(8))
