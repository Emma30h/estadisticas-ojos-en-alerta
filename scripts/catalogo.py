import sys, csv, re, collections, difflib
src = open('b2023.py', encoding='utf-8').read().split('# 1) nombre oficial')[0]
exec(src)
from web_barrios import WEB

# Excel -> nombre web
web = [(q, b) for q, v in WEB.items() for b in v.split('|')]
wn = {norm(b): b for q, b in web}
FIX = {'Procrear': 'Procrear Marqués', 'CAPDEVILA DE HORIZONTE': 'Horizonte', 'Juan B Justo': 'Juan B. Justo (Mariano Fragueiro Anexo)',
       'IPV': 'Yofre IPV', 'AMP. JARDÍN ESPINOSA': 'Ampliación Jardín Espinosa', 'SMATA': 'SMATA 1', 'Procrear Liceo': 'Procrear Liceo',
       'JARDÍN ESPINOSA': 'Jardín Espinosa'}
libres = set(wn)
ofi2web = {}
for o in oficial:
    b = o['barrio']
    if b in FIX: w = FIX[b]
    elif norm(b) in wn: w = wn[norm(b)]
    else: w = None
    if w: ofi2web[b] = w; libres.discard(norm(w))
for o in oficial:
    b = o['barrio']
    if b in ofi2web: continue
    m = difflib.get_close_matches(norm(b), sorted(libres), 1, 0.5)
    ofi2web[b] = wn[m[0]]; libres.discard(m[0])
assert not libres, libres

# superposición con barrios municipales 2023
def sample(pts, k=12):
    xs = [x for x, y in pts]; ys = [y for x, y in pts]
    a, b, c, d = min(xs), max(xs), min(ys), max(ys)
    return [(a + (b - a) * i / k, c + (d - c) * j / k) for i in range(1, k) for j in range(1, k)
            if inside(a + (b - a) * i / k, c + (d - c) * j / k, pts)]
poly_by_ofi = collections.defaultdict(list); kml_by_ofi = collections.defaultdict(list)
for lab, pts, bb in polys:
    o = kml2ofi.get(lab)
    if o:
        poly_by_ofi[o['barrio']].append(pts)
        if lab not in kml_by_ofi[o['barrio']]: kml_by_ofi[o['barrio']].append(lab)

# nombres del sistema
sis = collections.defaultdict(list)
for nombre, barrio, cu, di, met, n, pct, _ in list(csv.reader(open('../catalogo/equivalencias_barrios.csv', encoding='utf-8-sig'), delimiter=';'))[1:]:
    if barrio:
        try: nombre = nombre.encode('latin1').decode('utf-8')
        except Exception: pass
        sis[barrio].append((nombre, int(n)))

rows = []
for o in oficial:
    b = o['barrio']
    over = collections.Counter()
    for pts in poly_by_ofi[b]:
        for x, y in sample(pts): over[loc23(x, y) or '(fuera de capital)'] += 1
    t = sum(over.values())
    muni = ' / '.join(f"{k} ({v*100//t}%)" for k, v in over.most_common(2) if v * 100 // t >= 10) if t else ''
    s = sorted(sis[b], key=lambda x: -x[1])
    regla = 'nombre del sistema' if s else 'coordenada (sin nombre en sistema)'
    if b == 'CAPDEVILA DE HORIZONTE': regla = 'coordenada (sistema lo carga como Yofre IPV/H)'
    rows.append([ofi2web[b], o['cuadrante'], o['distrito'], b, ' / '.join(kml_by_ofi[b]), muni,
                 ' / '.join(f"{x[0]} ({x[1]})" for x in s), sum(x[1] for x in s), regla])
rows.sort(key=lambda r: (r[1], r[0]))
with open('../catalogo/catalogo_barrios.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['barrio (nombre oficial web)', 'cuadrante', 'DJP', 'nombre en Excel', 'nombre en KML programa',
                'barrio municipal 2023 (superposición)', 'nombres en sistema SAE (sucesos)', 'sucesos por nombre', 'regla de asignación'])
    w.writerows(rows)
print('Filas:', len(rows), '| reglas:', dict(collections.Counter(r[8] for r in rows)))
for r in rows:
    if r[0] in ('Procrear Marqués', 'Marqués de Sobremonte', 'Horizonte', 'Yofre IPV', '2 de Abril', 'Kronfuss'): print(r)
