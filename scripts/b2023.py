import sys, re, html, csv, collections, difflib, zipfile
src = open('equivalencias.py', encoding='utf-8').read().split('# --- nombres del sistema')[0]
src = src.replace('XLSX, KML, SAE, OUT = sys.argv[1:5]', 'XLSX, KML, SAE = sys.argv[1:4]')
exec(src)

r23 = ET.fromstring(zipfile.ZipFile('../fuentes/Barrio_1.kmz').read('doc.kml'))
n23 = {'k': r23.tag.split('}')[0][1:]}
B23 = []
for p in r23.findall('.//k:Placemark', n23):
    d = p.findtext('k:description', '', n23)
    tds = [html.unescape(re.sub(r'<[^>]+>', '', t)).strip() for t in re.findall(r'<td>(.*?)</td>', d, re.S)]
    a = dict(zip(tds[1::2], tds[2::2]))
    for c in p.findall('.//k:outerBoundaryIs//k:coordinates', n23):
        pts = [tuple(map(float, t.split(',')[:2])) for t in c.text.split()]
        xs = [x for x, y in pts]; ys = [y for x, y in pts]
        B23.append((a.get('Nombre', ''), a.get('TipoBarrio', ''), pts, (min(xs), max(xs), min(ys), max(ys))))
names23 = {norm(b[0]): b[0] for b in B23}
print('Polígonos 2023:', len(B23), '| nombres:', len(names23))

def loc23(x, y):
    for n, t, pts, (a, b, c, d) in B23:
        if a <= x <= b and c <= y <= d and inside(x, y, pts): return n
    return None

# 1) nombre oficial -> 2023 por nombre; y por superposición con nuestro polígono (muestra de puntos)
def sample(pts, k=12):
    xs = [x for x, y in pts]; ys = [y for x, y in pts]
    a, b, c, d = min(xs), max(xs), min(ys), max(ys); out = []
    for i in range(1, k):
        for j in range(1, k):
            x = a + (b - a) * i / k; y = c + (d - c) * j / k
            if inside(x, y, pts): out.append((x, y))
    return out

poly_by_ofi = collections.defaultdict(list)
for lab, pts, bb in polys:
    o = kml2ofi.get(lab)
    if o: poly_by_ofi[o['barrio']].append(pts)

print('\n=== Oficial (Excel) vs barrios 2023')
cnt = collections.Counter(); filas = []
for o in oficial:
    b = o['barrio']; n = norm(b)
    byname = names23.get(n)
    if not byname:
        m = difflib.get_close_matches(n, list(names23), 1, 0.8)
        byname = names23[m[0]] if m else None
    over = collections.Counter()
    for pts in poly_by_ofi.get(b, []):
        for x, y in sample(pts):
            over[loc23(x, y) or '(fuera)'] += 1
    tot = sum(over.values())
    top = ', '.join(f"{k} {v*100//tot}%" for k, v in over.most_common(3)) if tot else '(sin polígono)'
    estado = 'nombre' if byname and norm(byname) == n else ('parecido' if byname else 'no está')
    cnt[estado] += 1
    filas.append((b, byname or '', top, estado))
print(dict(cnt))
for b, bn, top, e in filas:
    if e != 'nombre': print(f"  [{e}] {b:38} 2023:{bn:30} superpone: {top}")

print('\n=== Barrios problemáticos')
for b in ['CAPDEVILA DE HORIZONTE', 'RESID. SAN ANTONIO', 'DOS DE ABRIL', 'QUINTAS DE INAUDI', 'Palmas de Claret',
          'Jardin Claret', 'Procrear', 'Procrear Liceo', 'IPV', 'Marques de Sobremonte']:
    f = [x for x in filas if x[0] == b][0]; print(f"  {b:28} 2023: {f[1]:30} superpone: {f[2]}")
pc = [k for k in names23 if 'PROCREAR' in k or 'CAPDEVILA' in k or 'SOBREMONTE' in k or 'ABRIL' in k]
print('  nombres 2023 relacionados:', [names23[k] for k in pc])

# 2) coincidencia sistema vs polígono 2023
eq = {r[0]: r[1] for r in list(csv.reader(open('../catalogo/equivalencias_barrios.csv', encoding='utf-8-sig'), delimiter=';'))[1:]}
ofi2_23 = {b: bn for b, bn, _, _ in filas}
ok = tot = fuera = 0; ok_old = 0; dis = collections.Counter()
with open(SAE, encoding='utf-8', errors='replace', newline='') as f:
    r = csv.reader(f); h = next(r); ci, li = h.index('Cuadricula'), h.index('lat.long')
    for row in r:
        ofi = eq.get(row[ci].strip())
        if not ofi or not ofi2_23.get(ofi): continue
        try: lat, lon = map(float, row[li].split(','))
        except Exception: continue
        g = loc23(lon, lat); tot += 1
        if g is None: fuera += 1
        elif norm(g) == norm(ofi2_23[ofi]): ok += 1
        else: dis[(ofi, g)] += 1
print(f"\n=== Sistema vs polígonos 2023: coincide {ok*100/tot:.1f}% de {tot} | fuera de Córdoba capital: {fuera}")
print('Discrepancias más grandes (oficial -> cae en):')
for (a, b), n in dis.most_common(15): print(f"   {n:>5} {a} -> {b}")
