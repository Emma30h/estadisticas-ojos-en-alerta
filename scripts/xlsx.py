import sys, zipfile, re
import xml.etree.ElementTree as ET
N = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
     'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

def read_xlsx(path):
    z = zipfile.ZipFile(path)
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', N):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t' % N['m'])))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rmap = {r.get('Id'): r.get('Target') for r in rels}
    out = {}
    for s in wb.find('m:sheets', N):
        tgt = rmap[s.get('{%s}id' % N['r'])].lstrip('/')
        if not tgt.startswith('xl/'): tgt = 'xl/' + tgt
        rows = []
        for row in ET.fromstring(z.read(tgt)).iter('{%s}row' % N['m']):
            cells = {}
            for c in row.findall('m:c', N):
                col = re.match(r'[A-Z]+', c.get('r')).group()
                idx = 0
                for ch in col: idx = idx * 26 + ord(ch) - 64
                v = c.find('m:v', N); t = c.get('t')
                if t == 's' and v is not None: val = ss[int(v.text)]
                elif t == 'inlineStr': val = ''.join(x.text or '' for x in c.iter('{%s}t' % N['m']))
                else: val = v.text if v is not None else ''
                cells[idx - 1] = val
            if cells:
                rows.append([cells.get(i, '') for i in range(max(cells) + 1)])
        out[s.get('name')] = rows
    return out

if __name__ == '__main__':
    for name, rows in read_xlsx(sys.argv[1]).items():
        print(f"\n=== Hoja: {name} | filas: {len(rows)}")
        for r in rows:
            print(' | '.join(str(x) for x in r))
