"""Zona cubierta por el programa según la fecha (barrios originales antes de la ampliación, los 234 después)."""
import datetime as dt
import json
import os
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.abspath(__file__))
KML = os.path.join(BASE, '..', 'fuentes', '234 barrios LIMITES AMPLIADOS.kml')
CRITERIOS = os.path.join(BASE, '..', 'catalogo', 'criterios.json')
_NS = {'k': 'http://www.opengis.net/kml/2.2'}


def criterios():
    with open(CRITERIOS, encoding='utf-8') as f:
        c = json.load(f)
    c['fecha_ampliacion'] = dt.date.fromisoformat(c['fecha_ampliacion'])
    return c


def _dentro(x, y, poly):
    ins, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


class Cobertura:
    def __init__(self):
        self.fecha_ampliacion = criterios()['fecha_ampliacion']
        doc = ET.parse(KML).getroot().find('k:Document', _NS)
        self.barrios = []    # (nombre KML, es_nuevo, puntos, caja)
        for f in doc.findall('k:Folder', _NS):
            if f.findtext('k:name', '', _NS) != 'Cobertura por Barrio':
                continue
            for p in f.findall('k:Placemark', _NS):
                nombre = p.findtext('k:name', '', _NS)
                nuevo = (p.findtext('k:description', '', _NS) or '').strip() == 'Cobertura Proyectada'
                for c in p.findall('.//k:Polygon/k:outerBoundaryIs//k:coordinates', _NS):
                    pts = [tuple(map(float, t.split(',')[:2])) for t in c.text.split()]
                    xs, ys = [a for a, _ in pts], [b for _, b in pts]
                    self.barrios.append((nombre, nuevo, pts, (min(xs), max(xs), min(ys), max(ys))))

    def barrio_en(self, lat, lon):
        """Barrio del programa (nombre KML, es_nuevo) que contiene el punto, o None."""
        for nombre, nuevo, pts, (a, b, c, d) in self.barrios:
            if a <= lon <= b and c <= lat <= d and _dentro(lon, lat, pts):
                return nombre, nuevo
        return None

    def cubierto(self, lat, lon, fecha):
        """True si el punto estaba dentro de la zona del programa en esa fecha."""
        if lat is None:
            return False
        b = self.barrio_en(lat, lon)
        if not b:
            return False
        return (not b[1]) or fecha >= self.fecha_ampliacion
