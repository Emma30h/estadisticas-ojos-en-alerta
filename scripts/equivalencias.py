import sys, csv, re, unicodedata, difflib, collections
sys.path.insert(0, '.')
from xlsx import read_xlsx
import xml.etree.ElementTree as ET
csv.field_size_limit(10**9)
XLSX, KML, SAE, OUT = sys.argv[1:5]
ns = {'k': 'http://www.opengis.net/kml/2.2'}

def norm(s):
    s = unicodedata.normalize('NFD', s.upper())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

# --- tabla oficial (Excel)
rows = [r for r in read_xlsx(XLSX)['Por cuadrante'][1:] if len(r) > 4 and r[4].strip()]
oficial = []; cuad = dist = None
for r in rows:
    if r[2].strip(): cuad = r[2].strip()
    if r[3].strip(): dist = r[3].strip()
    oficial.append({'barrio': r[4].strip(), 'cuadrante': cuad, 'distrito': dist})
ofi_by = {norm(o['barrio']): o for o in oficial}

# --- polígonos (KML)
doc = ET.parse(KML).getroot().find('k:Document', ns)
polys = []
for f in doc.findall('k:Folder', ns):
    if f.findtext('k:name', '', ns) != 'Cobertura por Barrio': continue
    for p in f.findall('k:Placemark', ns):
        lab = p.findtext('k:name', '', ns)
        for c in p.findall('.//k:Polygon/k:outerBoundaryIs//k:coordinates', ns):
            pts = [tuple(map(float, t.split(',')[:2])) for t in c.text.split()]
            xs = [a for a, b in pts]; ys = [b for a, b in pts]
            polys.append((lab, pts, (min(xs), max(xs), min(ys), max(ys))))
kml_names = sorted({p[0] for p in polys})

# --- KML -> barrio oficial
MANUAL = {
    'Country QUINTAS DE ITALIA': 'QUINTAS DE ITALIA',
    'Ampliasion Velez Sarsfield  - Cooperativa Horizonte': 'AMPLIACION VELEZ SARSFIELD',
    'RESIDENCIAL VELEZ SÁRSFIELD': 'RESIDENCIAL VELEZ SARSFIELD',
    'SMATA 1': 'SMATA',
    'JUAN B. JUSTO (MARIANO FREGUEIRO ANEXO)': 'Juan B Justo',
    'Yofre IPV': 'IPV',
    'LEANDRO N. ALEM': 'ALEM',
    'YOFRE Horizonte': 'CAPDEVILA DE HORIZONTE',
    'JARDÍN DE HORIZONTE': 'Jardin de Horizonte',
    'AMPLIACIÓN JARDÍN ESPINOZA': 'AMP. JARDÍN ESPINOSA',
    'JARDÍN ESPINOSA': 'JARDÍN ESPINOSA',
    'HOGAR CLASE MEDIA - MARQUES DE SOBREMONTE': 'Procrear',
    'QUINTAS DE INAUDI': 'QUINTAS DE INAUDI',
    'LA FRATERNIDAD': 'FRATERNIDAD',
    'GRANADERO PRINGLES': 'Pringles',
}
# nombres del sistema que no se parecen al oficial
ALIAS_SIS = {
    'SAN FRANCISCO': 'PARQUE SAN FRANCISCO',
    'AMP VELEZ SARSFIELD COOP HORIZONTE': 'AMPLIACION VELEZ SARSFIELD',
    'AMPLIACION VELEZ SASRFIELD COOP HORIZONTE': 'AMPLIACION VELEZ SARSFIELD',
    'GRANADEROS PRINGLES': 'Pringles',
    'MARQUES DE SOBREMONTE II': 'Procrear',
    'VILLA EUCARISTIA': 'VILLA EUCARISTICA',
    'SANTA ISABEL 1A SECCION': 'SANTA ISABEL 1º SECC.',
}
kml2ofi = {}
for k in kml_names:
    if k in MANUAL: kml2ofi[k] = ofi_by[norm(MANUAL[k])]; continue
    n = norm(k)
    if n in ofi_by: kml2ofi[k] = ofi_by[n]; continue
    m = difflib.get_close_matches(n, list(ofi_by), 1, 0.6)
    kml2ofi[k] = ofi_by[m[0]] if m else None
sin_ofi = [k for k, v in kml2ofi.items() if v is None]
cubiertos = {id(v) for v in kml2ofi.values() if v}
ofi_sin_poly = [o['barrio'] for o in oficial if id(o) not in cubiertos]

def inside(x, y, poly):
    ins, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins

def locate(x, y):
    for lab, pts, (a, b, c, d) in polys:
        if a <= x <= b and c <= y <= d and inside(x, y, pts): return lab
    return None

# --- nombres del sistema
sis = collections.defaultdict(collections.Counter)
with open(SAE, encoding='utf-8', errors='replace', newline='') as f:
    r = csv.reader(f); h = next(r)
    ci, li = h.index('Cuadricula'), h.index('lat.long')
    for row in r:
        name = row[ci].strip()
        if not name: continue
        try:
            lat, lon = map(float, row[li].split(','))
            lab = locate(lon, lat)
        except Exception:
            lab = None
        o = kml2ofi.get(lab) if lab else None
        sis[name][o['barrio'] if o else '(fuera de los 234)'] += 1

# alias por nombre: oficial + nombres KML
alias = dict(ofi_by)
for k, o in kml2ofi.items():
    if o: alias.setdefault(norm(k), o)
for k, v in ALIAS_SIS.items():
    alias[norm(k)] = ofi_by[norm(v)]

out = []
for name, cnt in sorted(sis.items(), key=lambda kv: -sum(kv[1].values())):
    tot = sum(cnt.values())
    try: fixed = name.encode('latin1').decode('utf-8')
    except Exception: fixed = name
    base = norm(re.sub(r'^C\s*\d+\s*-\s*', '', fixed))
    top, topn = cnt.most_common(1)[0]
    o = alias.get(base); metodo = 'nombre'
    if not o:
        m = difflib.get_close_matches(base, list(alias), 1, 0.85)
        if m: o = alias[m[0]]; metodo = 'nombre parecido'
    if not o and top != '(fuera de los 234)' and topn / tot >= 0.6:
        o = ofi_by[norm(top)]; metodo = 'coordenadas'
    pct = cnt[o['barrio']] * 100 / tot if o else 0
    out.append([name, o['barrio'] if o else '', o['cuadrante'] if o else '', o['distrito'] if o else '',
                metodo if o else 'SIN RESOLVER', tot, f"{pct:.0f}%",
                ' | '.join(f"{k}:{v}" for k, v in cnt.most_common(3))])

with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['nombre_sistema', 'barrio_oficial', 'cuadrante', 'distrito', 'metodo', 'sucesos',
                'pct_dentro_del_poligono', 'donde_caen_las_coordenadas'])
    w.writerows(out)

print("KML sin barrio oficial:", sin_ofi)
print("Oficiales sin polígono:", ofi_sin_poly)
print("Nombres de sistema:", len(out), "| por método:", dict(collections.Counter(x[4] for x in out)))
print("Sucesos cubiertos:", sum(x[5] for x in out if x[1]), "de", sum(x[5] for x in out))
ok = sum(int(x[6][:-1]) * x[5] / 100 for x in out if x[1]); tot = sum(x[5] for x in out if x[1])
print(f"Coincidencia nombre del sistema vs polígono: {ok/tot*100:.1f}% de {tot} sucesos")
print("\nSIN RESOLVER:")
for x in out:
    if not x[1]: print(f"  {x[5]:>5}  {x[0]}  ->  {x[7]}")
print("\nResueltos por coordenadas o parecido (revisar):")
for x in out:
    if x[4] in ('coordenadas', 'nombre parecido'): print(f"  {x[5]:>5}  {x[0]}  =>  {x[1]} [{x[4]}, {x[6]}]")
print("\nResueltos por nombre pero con <50% dentro del polígono (sucesos>=30):")
for x in out:
    if x[4] == 'nombre' and x[5] >= 30 and int(x[6][:-1]) < 50: print(f"  {x[5]:>5}  {x[0]}  =>  {x[1]} ({x[6]}) | {x[7]}")
