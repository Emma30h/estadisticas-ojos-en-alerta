"""Genera los informes del SAE (mensual, semanal y placa numérica) replicando los modelos.

Uso (desde la carpeta scripts/):
    python generar_informe.py mensual 2026-09                 (mes completo)
    python generar_informe.py semanal                         (última semana viernes→jueves ya cerrada)
    python generar_informe.py semanal 2026-10-01              (7 días que terminan en esa fecha)
    python generar_informe.py semanal 2026-09-25 2026-10-01   (fechas exactas, inclusive)
    python generar_informe.py placa   2026-09
Opciones: --csv RUTA (por defecto, el CSV más nuevo de fuentes/ o de Descargas),
          --no-corregir (deja el texto del CSV tal cual, ej. "RIÃ‘A").
Al terminar imprime un resumen en JSON (totales, por DJP y avisos) para revisar antes de entregar.
"""
import argparse
import datetime as dt
import html
import json
import math
import os
import subprocess
import sys

import sae

BASE = os.path.dirname(os.path.abspath(__file__))
PLANT = os.path.join(BASE, '..', 'plantillas')
SALIDA = os.path.join(BASE, '..', 'informes')
CHROME = [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
          r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe']
MES = ['', 'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic']
DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']

AZUL_DJP, AZUL_HORA, AZUL_DIA, AZUL_TIPO = '#1590d1', '#1693d5', '#108acb', '#1492d4'
VERDE = '#39ff14'
MARCA_OPACIDAD = 0.11


# ---------------------------------------------------------------- utilidades

def miles(n):
    return f'{n:,}'.replace(',', '.')


def esc(s):
    return html.escape(str(s))


def periodo_looker(d1, d2):
    return f'{d1.day} {MES[d1.month]} {d1.year} - {d2.day} {MES[d2.month]} {d2.year}'


def nice_max(v, count=4):
    """Máximo del eje como lo calcula Looker (equivalente a d3.nice)."""
    if v <= 0:
        return 1
    step = v / count
    p = math.floor(math.log10(step))
    err = step / 10 ** p
    f = 10 if err >= math.sqrt(50) else 5 if err >= math.sqrt(10) else 2 if err >= math.sqrt(2) else 1
    step = f * 10 ** p
    return math.ceil(v / step) * step


def T(x, y, size, text, color='#ffffff', anchor='start', font='Arial', weight='normal', extra=''):
    """Texto con la parte superior del glifo en y (pt), como lo mide el PDF modelo."""
    tr = {'start': '', 'middle': 'transform:translateX(-50%);', 'end': 'transform:translateX(-100%);'}[anchor]
    return (f'<div class="t" style="left:{x:.2f}pt;top:{y:.2f}pt;font-size:{size}pt;color:{color};'
            f'font-family:{font};font-weight:{weight};{tr}{extra}">{esc(text)}</div>')


def R(x, y, w, h, color, extra=''):
    if w <= 0 or h <= 0:
        return ''
    return f'<div class="r" style="left:{x:.2f}pt;top:{y:.2f}pt;width:{w:.2f}pt;height:{h:.2f}pt;background:{color};{extra}"></div>'


def marca(x, y, color='#cccccc'):
    return T(x, y, 72, 'D.M.C.A.', color, font='Impact', extra=f'opacity:{MARCA_OPACIDAD};')


def img(src, x0, y0, x1, y1):
    return f'<img class="i" src="{src}" style="left:{x0}pt;top:{y0}pt;width:{x1 - x0}pt;height:{y1 - y0}pt">'


def leyenda(x, y, ytxt, size, color_txt, sep, col_a, ancho=17.2, alto=6.9):
    return (R(x, y, ancho, alto, col_a) + T(x + 22.5, ytxt, size, 'ALERTAS', color_txt) +
            R(x + sep, y, ancho, alto, VERDE) + T(x + sep + 22.5, ytxt, size, 'POSITIVOS', color_txt))


# ---------------------------------------------------------------- componentes

def secuestros(sec, tops):
    return ''.join(T(258.5, y, 22.5, sec[k], anchor='middle')
                   for k, y in zip(['fuego', 'blancas', 'estupefacientes', 'vehiculos', 'otros'], tops))


def medidor(x0, x1, y0, y1, alertas, positivos, borde):
    if alertas <= 0:
        return ''
    h = y1 - y0
    hp = h * positivos / alertas
    b = 'outline:0.75pt solid #b7b7b7;' if borde else ''
    out = R(x0, y0, x1 - x0, max(h - hp - 0.7, 0), '#1899de', b)
    if positivos:
        out += R(x0, y1 - hp, x1 - x0, hp, '#28ff00', b)
    return out


def tipologia(items, y0, color, n, ancho_txt=231):
    if not items:
        return T(153.75, y0 + 5.4, 7.5, 'No hay datos', anchor='middle')
    mx = max(v for _, v in items)
    dig = len(str(mx))
    num_der = 272.0 + (dig - 2) * 5.9
    bar_ini = num_der + 1.85
    bar_max = 294.8 - bar_ini
    out = []
    for i, (nombre, v) in enumerate(items[:n]):
        y = y0 + i * 21.75
        if i % 2 == 0:
            out.append(R(6.8, y, 294.0, 21.75, '#434343'))
        out.append(f'<div class="t tipo" style="left:12.8pt;top:{y + 5.4:.2f}pt;width:{ancho_txt}pt">{esc(nombre)}</div>')
        out.append(T(num_der, y + 5.4, 9, v, '#efefef', 'end'))
        out.append(R(bar_ini, y + 6, max(0.8, bar_max * v / mx), 9, color))
    return ''.join(out)


def dias_horizontal(dias, y_bar, paso, alto, y_lbl, cajas):
    """Días críticos: barras horizontales (alertas arriba, positivos abajo), de domingo a sábado.
    Como en Looker, solo se muestran los días con alertas y se reparten en todo el alto del gráfico."""
    ancho = 220.1
    filas = [(DIAS[i], a, p) for i, (a, p) in enumerate(dias) if a > 0]
    esc_ = ancho / nice_max(max([a for _, a, _ in filas] or [1]))
    k = paso / 22.5                      # las medidas base son las de la página DJP
    area_top = y_bar - 8.9 * k
    area_h = 163.5 * k
    out = [R(69.7, area_top, 0.75, area_h, '#b8b8b8')]
    if not filas:
        return ''.join(out)
    f = 7 / len(filas)
    pitch = paso * f
    pad = (area_h - 7 * paso) / 2
    for i, (dia, a, p) in enumerate(filas):
        top = area_top + pad + i * pitch
        ya = top + (y_bar - area_top - pad) * f
        yp = ya + paso * 0.30 * f
        h = alto * f
        out.append(T(64.7, top + pitch / 2 - 6.7 - 0.75 * k, 12, dia, '#f3f3f3', 'end'))
        wa, wp = a * esc_, p * esc_
        out.append(R(70.5, ya, wa, h, AZUL_DIA))
        out.append(R(70.5, yp, max(wp, 0.75 if p else 0), h, VERDE))
        if cajas:
            for w, y, v in ((wa, ya, a), (wp, yp, p)):
                txt = str(v)
                bw = 6.6 * len(txt) + 6
                bx = 70.5 + w + 9
                if bx + bw > 297:
                    bx = 70.5 + w - 9 - bw
                cy = y + h / 2
                out.append(R(bx, cy - 7.55, bw, 15, '#434343', 'border-radius:2pt;'))
                out.append(T(bx + 3, cy - 7.15, 12, txt, '#f3f3f3'))
        else:
            out.append(T(70.5 + wa + 1.5, ya + h / 2 - 7.1, 12, miles(a), '#f3f3f3'))
            out.append(T(70.5 + wp + 1.5, yp + h / 2 - 7.1, 12, miles(p), '#f3f3f3'))
    return ''.join(out)


def horas_horizontal(horas):
    """Hora crítica de las páginas DJP: barras horizontales. Solo las horas con alertas, repartidas en el alto."""
    filas = [(h, a, p) for h, (a, p) in enumerate(horas) if a > 0]
    esc_ = 272.3 / nice_max(max([a for _, a, _ in filas] or [1]))
    out = [R(621.7, 131.2, 0.75, 395.3, '#f3f3f3')]
    if not filas:
        return ''.join(out)
    pitch = 395.3 / len(filas)
    f = pitch / 16.45
    for i, (hora, a, p) in enumerate(filas):
        top = 131.2 + i * pitch
        ya, yp, hb = top + 1.7 * f, top + 9.1 * f, 6.8 * f
        out.append(T(613.1, top + pitch / 2 - 5.3, 9, hora, '#efefef', 'end'))
        wa, wp = a * esc_, p * esc_
        out.append(R(622.5, ya, wa, hb, AZUL_HORA))
        out.append(R(622.5 if p else 621.8, yp, wp if p else 0.75, hb, VERDE))
        out.append(T(622.5 + wa + 1.5, ya + hb / 2 - 5.8, 9.75, a))
        out.append(T(622.5 + wp + 1.5, yp + hb / 2 - 5.8, 9.75, p))
    return ''.join(out)


def horas_vertical(horas):
    """Hora crítica de la página General: columnas 0–23."""
    base, alto = 777.8, 181.5
    esc_ = alto / nice_max(max(a for a, _ in horas) or 1)
    out = [R(330.0, 777.75, 579.0, 0.75, '#f3f3f3')]
    for h, (a, p) in enumerate(horas):
        xa = 332.4 + h * 24.1
        xp = xa + 10.9
        ha, hp = a * esc_, p * esc_
        out.append(R(xa, base - ha, 9, ha, AZUL_HORA))
        out.append(R(xp, base - max(hp, 0.75), 9, max(hp, 0.75), VERDE))
        out.append(T(xa + 4.5, base - ha - 12.5, 9.75, a, anchor='middle'))
        out.append(T(xp + 4.5, base - max(hp, 0.75) - 12.5, 9.75, p, anchor='middle'))
        out.append(T(xa + 9.95, 782.0, 9, h, '#efefef', 'middle'))
    return ''.join(out)


def grafico_djp(por_djp):
    """Alerta/positivo por DJP (página General): columnas en escala logarítmica."""
    cats = sorted(sae.DJP_INFORME, key=str) + [sae.FUERA]
    base = 522.0
    mx = max(por_djp[c][0] for c in cats) or 1
    k = 179.1 / math.log10(mx + 1)
    out, rot = [], []
    for i, c in enumerate(cats):
        a, p = por_djp[c]
        xa = 35.0 + i * 39.29
        xp = xa + 13.4
        ha, hp = k * math.log10(a + 1), k * math.log10(p + 1)
        out.append(R(xa, base - ha, 12.75, ha, AZUL_DJP))
        out.append(R(xp, base - hp, 12.75, hp, VERDE))
        for x, h, v, adentro in ((xa, ha, a, False), (xp, hp, p, True)):
            txt = str(v)
            bw = 5.85 * len(txt) + 6
            cx = x + 6.375
            if adentro and v < 10 and h >= 14.5:
                top = base - h + 0.7
            elif not adentro and base - h - 23.2 < 340:
                top = base - h + 8.2
            else:
                top = base - h - 9.7 - 13.5
            out.append(R(cx - bw / 2, top, bw, 13.5, '#ffffff', 'border-radius:1.5pt;'))
            out.append(T(cx, top + 0.3, 10.5, txt, '#000000', 'middle'))
        etiqueta = 'FUER…' if c == sae.FUERA else c
        ax, ay = xa + 13.05 + 3.32, 524.74
        rot.append(f'<text x="{ax:.2f}" y="{ay:.2f}" text-anchor="end" transform="rotate(-30 {ax:.2f} {ay:.2f})">{esc(etiqueta)}</text>')
    out.append('<svg class="i" style="left:0;top:0;width:930pt;height:1314.96pt;z-index:3" viewBox="0 0 930 1314.96">'
               '<g font-family="Arial" font-size="9.75" fill="#d9d9d9">' + ''.join(rot) + '</g></svg>')
    out.append(R(22.5, 511.5, 876.0, 0.75, '#666666'))
    out.append(T(852.8, 516.0, 8.25, 'Fuera de', '#d9d9d9'))
    out.append(T(852.8, 522.8, 8.25, 'Cuadrante', '#d9d9d9'))
    return ''.join(out)


def mapa(mid, x0, y0, x1, y1, puntos, general, alternativos=()):
    # Atribución exigida por la licencia de los datos del mapa
    return (T(x1 - 4, y1 - 9, 5, '© OpenStreetMap · OpenFreeMap', '#6a6a6a', 'end', extra='z-index:4;') +f'<div class="mapa" id="{mid}" style="left:{x0}pt;top:{y0}pt;width:{x1 - x0}pt;height:{y1 - y0}pt" '
            f'data-puntos=\'{json.dumps(puntos)}\' data-alt=\'{json.dumps(list(alternativos))}\' data-general="{int(general)}"></div>')


# ---------------------------------------------------------------- páginas

def pagina_portada(tipo, d1, d2):
    txt = f'({d1:%d/%m/%y} al {d2:%d/%m/%y})'
    return ('<div class="page a4"><img class="bg" src="portada.png">' +
            T(465, 791.2, 30, f'INFORME {tipo.upper()}', anchor='middle', font="'Open Sans'", weight='700') +
            T(465, 832.4, 30, txt, anchor='middle', font="'Open Sans'", weight='700') + '</div>')


def pagina_general(ind, por_djp, periodo, mid):
    o = ['<div class="page a4"><img class="bg" src="fondo_general.png">']
    o.append(T(754.65, 50.0, 13.5, periodo, anchor='middle'))
    o.append(T(871.5, 51.0, 13.5, '▾', extra='transform:scaleX(1.4);'))
    o.append(secuestros(ind['secuestros'], [128.1, 169.4, 207.6, 245.1, 282.6]))
    o.append(medidor(354.0, 426.8, 105.0, 285.8, ind['alertas'], ind['positivos'], False))
    o.append(T(555, 156.4, 36, miles(ind['alertas']), '#efefef', 'middle'))
    o.append(T(555, 246.4, 36, miles(ind['positivos']), '#efefef', 'middle'))
    o.append(T(795, 238.2, 36, miles(ind['aprehendidos']), anchor='middle'))
    o.append(R(25.6, 321.8, 18.6, 7.4, AZUL_DJP) + T(49.8, 319.0, 10.5, 'ALERTA POR DJP'))
    o.append(R(147.8, 321.8, 18.6, 7.4, VERDE) + T(172.1, 319.0, 10.5, 'POSITIVO POR DJP'))
    o.append(grafico_djp(por_djp))
    o.append(leyenda(72.2, 578.9, 576.6, 8.25, '#d9d9d9', 64.5, AZUL_DIA, 14.6, 5.8))
    o.append(dias_horizontal(ind['dias'], 606.0, 26.6, 5.2, 604.9, cajas=False))
    o.append(leyenda(332.9, 578.4, 576.0, 9.75, '#f3f3f3', 75.0, AZUL_HORA))
    o.append(horas_vertical(ind['horas']))
    o.append(tipologia(ind['tipo_positivos'], 854.2, VERDE, 20))
    o.append(mapa(mid, 312.0, 807.8, 918.0, 1308.7, ind['puntos'], True))
    o.append(T(505.2, 815.4, 17.25, 'CONCENTRACIÓN DE POSITIVOS', '#cccccc', extra='z-index:5;'))
    o.append(R(318.2, 813.8, 37.0, 37.2, '#ffffff', 'z-index:5;border-radius:2pt;'))
    o.append('<svg class="i" style="left:328.5pt;top:823.5pt;width:16.5pt;height:16.5pt;z-index:6" viewBox="0 0 24 24">'
             '<path fill="#666" d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm8.94 3A8.99 8.99 0 0 0 13 3.06V1h-2v2.06A8.99 8.99 0 0 0 3.06 11H1v2h2.06A8.99 8.99 0 0 0 11 20.94V23h2v-2.06A8.99 8.99 0 0 0 20.94 13H23v-2h-2.06zM12 19a7 7 0 1 1 0-14 7 7 0 0 1 0 14z"/></svg>')
    o.append(T(325.5, 1282.6, 9, 'Resultado', '#b7b7b7', weight='bold', extra='z-index:5;'))
    o.append('<div class="punto" style="left:378.5pt;top:1284.4pt;z-index:5"></div>')
    o.append(T(391.5, 1282.6, 9, 'Positivo', '#b7b7b7', extra='z-index:5;'))
    o.append(img('logo_ojo.png', 824, 1267, 867, 1298) + img('logo_policia.png', 854, 1263, 923, 1298))
    for x, y, c in [(82.9, 620.4, '#cccccc'), (345.4, 350.4, '#cccccc'), (510.4, 1167.9, '#d9d9d9'),
                    (52.9, 1145.4, '#cccccc'), (525.4, 852.9, '#cccccc'), (532.9, 650.4, '#cccccc')]:
        o.append(marca(x, y, c))
    o.append(T(913.7, 1303.6, 9, '*** FUENTE DE INFORMACIÓN: SAE', anchor='end'))
    o.append('</div>')
    return ''.join(o)


def pagina_djp(djp, ind, periodo, mid):
    fuera = djp == sae.FUERA
    o = [f'<div class="page a4"><img class="bg" src="{"fondo_fuera.png" if fuera else "fondo_djp.png"}">']
    o.append(T(738.15, 52.3, 13.5, periodo, anchor='middle'))
    o.append(T(836.5, 53.2, 13.5, '▾', extra='transform:scaleX(1.4);'))
    if fuera:
        o.append(T(423.8, 52.0, 15, 'FUERA DE CUADRANTE', '#f3f3f3', 'middle', "'Ubuntu'", '700'))
        o.append(T(882.75, 46.7, 10.5, 'FUERA DE', '#efefef', 'middle', weight='bold'))
        o.append(T(882.75, 58.7, 10.5, 'CUADRANTE', '#efefef', 'middle', weight='bold'))
    else:
        o.append(T(877.5, 42.6, 22.5, djp, '#efefef', 'middle'))
    o.append(secuestros(ind['secuestros'], [132.6, 170.1, 207.6, 245.1, 282.6]))
    o.append(medidor(334.9, 385.9, 112.5, 293.2, ind['alertas'], ind['positivos'], True))
    o.append(T(487.5, 156.4, 36, miles(ind['alertas']), '#efefef', 'middle'))
    o.append(T(487.5, 246.4, 36, miles(ind['positivos']), '#efefef', 'middle'))
    o.append(T(442.5, 463.2, 36, miles(ind['aprehendidos']), anchor='middle'))
    o.append(leyenda(72.2, 353.9, 351.6, 8.25, '#d9d9d9', 64.5, AZUL_DIA, 14.6, 5.8))
    o.append(dias_horizontal(ind['dias'], 379.4, 22.5, 4.5, 377.3, cajas=True))
    o.append(leyenda(624.6, 113.4, 111.0, 9.75, '#f3f3f3', 75.0, AZUL_HORA))
    o.append(horas_horizontal(ind['horas']))
    o.append(T(153.75, 579.0, 15.75, 'ALERTAS', '#2398d5', 'middle'))
    o.append(tipologia(ind['tipo_alertas'], 599.2, AZUL_TIPO, 15))
    o.append(T(153.75, 946.5, 15.75, 'POSITIVOS', VERDE, 'middle'))
    o.append(tipologia(ind['tipo_positivos'], 966.8, VERDE, 15))
    o.append(mapa(mid, 312.0, 545.3, 918.0, 1301.0, ind['puntos'], False, ind['puntos_alertas']))
    o.append(T(370.2, 560.4, 17.25, 'CONCENTRACIÓN DE POSITIVOS', '#cccccc', extra='z-index:5;'))
    o.append(T(325.5, 1275.1, 9, 'Resultado', '#d9d9d9', weight='bold', extra='z-index:5;'))
    o.append('<div class="punto" style="left:378.5pt;top:1276.9pt;z-index:5"></div>')
    o.append(T(391.5, 1275.1, 9, 'Positivo', '#d9d9d9', extra='z-index:5;'))
    o.append(img('logo_ojo.png', 809, 1264, 856, 1299) + img('logo_policia.png', 839, 1260, 916, 1298))
    for x, y, c in [(45.4, 732.9, '#cccccc'), (697.9, 267.9, '#999999'), (502.9, 597.9, '#cccccc'),
                    (90.4, 395.4, '#cccccc'), (510.4, 1167.9, '#d9d9d9'), (37.9, 1092.9, '#cccccc')]:
        o.append(marca(x, y, c))
    o.append(T(910.2, 1303.6, 9, '* FUENTE DE INFORMACIÓN: SAE', anchor='end'))
    o.append('</div>')
    return ''.join(o)


def pagina_placa(ind, periodo):
    o = ['<div class="page placa"><img class="bg" src="fondo_placa.png">']
    o.append(T(25.5, 35.2, 15, 'Periodo:', weight='bold'))
    o.append(T(96.8, 35.0, 13.5, periodo))
    o.append(T(284.5, 36.8, 13.5, '▾', extra='transform:scaleX(1.4);'))
    o.append(T(455, 28.9, 16.5, 'Resumen Numérico', '#f3f3f3', 'middle', "'Ubuntu'"))
    o.append(img('placa_ojo.png', 794, 12, 855, 58) + img('placa_policia.png', 832, 5, 954, 67))
    o.append(T(232.5, 108.3, 27, miles(ind['alertas']), anchor='middle'))
    o.append(T(693.75, 108.3, 27, miles(ind['positivos']), anchor='middle'))
    # Anillo masculino / femenino
    m, f = ind['masculinos'], ind['femeninas']
    tot = (m + f) or 1
    cx, cy, r = 209.25, 367.55, 120.75
    a = 2 * math.pi * f / tot
    px, py = cx - r * math.sin(a), cy - r * math.cos(a)
    grande = 1 if f / tot > 0.5 else 0
    o.append(f'<svg class="i" style="left:0;top:0;width:930pt;height:600pt" viewBox="0 0 930 600">'
             f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#2500c9"/>'
             + (f'<path d="M{cx},{cy} L{cx},{cy - r} A{r},{r} 0 {grande} 0 {px:.2f},{py:.2f} Z" fill="#ff5bd6"/>' if f else '')
             + f'<circle cx="{cx}" cy="{cy}" r="61.5" fill="#434343" stroke="#000" stroke-width="1.5"/></svg>')
    pm, pf = m * 100 / tot, f * 100 / tot
    if f:
        ang = a / 2
        o.append(T(cx - 0.62 * r * math.sin(ang) - 13.85 + 13.85, cy - 0.62 * r * math.cos(ang) - 5.5, 9.75, f'{pf:.1f}%', '#000000', 'middle'))
    ang = a + (2 * math.pi - a) / 2
    o.append(T(cx - 0.75 * r * math.sin(ang), cy - 0.75 * r * math.cos(ang) - 5.5, 9.75, f'{pm:.1f}%', '#9f9f9f', 'middle'))
    o.append(R(111.8, 219.8, 16.5, 16.5, '#1652f6', 'outline:1.5pt solid #000;') + T(132.8, 223.0, 10.5, 'MASCULINO', '#efefef'))
    o.append(R(216.8, 219.8, 16.5, 16.5, '#ff3ef5', 'outline:1.5pt solid #000;') + T(237.8, 223.0, 10.5, 'FEMENINO', '#efefef'))
    o.append(T(207.75, 342.5, 13.5, 'TOTAL', anchor='middle'))
    o.append(T(207.75, 358.8, 27, miles(ind['aprehendidos']), anchor='middle'))
    o.append(T(105.0, 523.1, 27, miles(ind['mayores']), '#d9d9d9', 'middle'))
    o.append(T(303.75, 523.8, 27, miles(ind['menores']), '#d9d9d9', 'middle'))
    # Lista "POSITIVOS" (sucesos con aprehendidos)
    o.append(T(392.2, 177.2, 10.5, 'POSITIVOS', '#b7b7b7'))
    items = ind['tipo_con_aprehendidos']
    if items:
        mx = max(v for _, v in items)
        bar_max = 21 * (1 if len(str(mx)) <= 2 else 15 / 21)
        filas = ''.join(
            f'<div class="fila"><div class="nom">{esc(n)}</div><div class="num">{v}</div>'
            f'<div class="bar" style="width:{max(0.8, bar_max * v / mx):.2f}pt"></div></div>' for n, v in items)
        o.append(f'<div class="lista" style="left:396pt;top:{200.4 + 0.52:.2f}pt">{filas}</div>')
    sec = ind['secuestros']
    for k, y in zip(['fuego', 'blancas', 'vehiculos', 'estupefacientes', 'otros'], [243.3, 315.3, 383.6, 457.8, 525.3]):
        o.append(T(776.25, y, 27, sec[k], '#d9d9d9', 'middle'))
    o.append(R(-0.8, 584.2, 931.5, 16.6, '#241b1b'))
    o.append(T(902.4, 586.7, 10.5, '* FUENTE DE INFORMACION: SAE', anchor='end'))
    o.append('</div>')
    return ''.join(o)


# ---------------------------------------------------------------- HTML y PDF

CSS = """
@page { margin: 0; }
html, body { margin: 0; padding: 0; background: #111; }
.page { position: relative; overflow: hidden; page-break-after: always; break-after: page; }
.page:last-child { page-break-after: auto; break-after: auto; }
.a4 { width: 930pt; height: 1314.96pt; }
.placa { width: 930pt; height: 600pt; }
.bg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
.t { position: absolute; white-space: nowrap; line-height: 1.117; z-index: 3; }
.r, .i { position: absolute; z-index: 2; }
.tipo { font-family: Arial; font-size: 9pt; color: #efefef; overflow: hidden; text-overflow: ellipsis; }
.rot { transform-origin: 100% 81%; transform: translate(-100%, -81%) rotate(-30deg); font-family: Arial; }
.mapa { position: absolute; z-index: 1; background: #1d1f22; }
.punto { position: absolute; width: 7pt; height: 7pt; border-radius: 50%; background: #2bd629; }
.lista { position: absolute; z-index: 3; font-family: Arial; font-size: 9pt; color: #cccccc; }
.fila { position: relative; width: 237pt; line-height: 9pt; padding-bottom: 12.75pt; }
.fila .nom { width: 176pt; white-space: normal; }
.fila .num { position: absolute; right: 23pt; top: 0; }
.fila .bar { position: absolute; left: 216pt; top: 0.08pt; height: 9pt; background: #39ff14; }
"""

JS = """
(function () {
  // Estilo oscuro equivalente al tema "Dark" de Google Maps que usa Looker Studio
  var F = ['Noto Sans Regular'], FB = ['Noto Sans Bold'];
  var nombre = ['coalesce', ['get', 'name:es'], ['get', 'name']];
  var ancho = function (a, b) { return ['interpolate', ['exponential', 1.6], ['zoom'], 11, a, 17, b]; };
  var linea = function (id, clases, color, a, b) {
    return { id: id, type: 'line', source: 'omt', 'source-layer': 'transportation',
             filter: ['in', ['get', 'class'], ['literal', clases]],
             layout: { 'line-cap': 'round', 'line-join': 'round' },
             paint: { 'line-color': color, 'line-width': ancho(a, b) } };
  };
  var halo = { 'text-halo-color': '#212121', 'text-halo-width': 1.6 };
  var estilo = {
    version: 8,
    glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
    sources: { omt: { type: 'vector', url: 'https://tiles.openfreemap.org/planet' } },
    layers: [
      { id: 'fondo', type: 'background', paint: { 'background-color': '#212121' } },
      { id: 'verde', type: 'fill', source: 'omt', 'source-layer': 'landuse',
        filter: ['in', ['get', 'class'], ['literal', ['park', 'cemetery', 'stadium', 'pitch']]], paint: { 'fill-color': '#181818' } },
      { id: 'verde2', type: 'fill', source: 'omt', 'source-layer': 'park', paint: { 'fill-color': '#181818' } },
      { id: 'agua', type: 'fill', source: 'omt', 'source-layer': 'water', paint: { 'fill-color': '#000000' } },
      { id: 'rio', type: 'line', source: 'omt', 'source-layer': 'waterway', paint: { 'line-color': '#000000', 'line-width': ancho(1, 6) } },
      linea('tren', ['rail', 'transit'], '#2f2f2f', 0.6, 2),
      linea('calle', ['minor', 'service'], '#2c2c2c', 0.4, 9),
      linea('avenida', ['secondary', 'tertiary'], '#373737', 0.9, 13),
      linea('troncal', ['primary', 'trunk'], '#3c3c3c', 1.2, 15),
      linea('autopista', ['motorway'], '#4e4e4e', 1.5, 16),
      { id: 'nombre_calle', type: 'symbol', source: 'omt', 'source-layer': 'transportation_name', minzoom: 13,
        filter: ['in', ['get', 'class'], ['literal', ['minor', 'tertiary', 'secondary']]],
        layout: { 'symbol-placement': 'line', 'text-field': nombre, 'text-font': F, 'text-size': 10 },
        paint: Object.assign({ 'text-color': '#6b6b6b' }, halo) },
      { id: 'nombre_avenida', type: 'symbol', source: 'omt', 'source-layer': 'transportation_name', minzoom: 12,
        filter: ['in', ['get', 'class'], ['literal', ['primary', 'trunk', 'motorway']]],
        layout: { 'symbol-placement': 'line', 'text-field': nombre, 'text-font': F, 'text-size': 11 },
        paint: Object.assign({ 'text-color': '#8a8a8a' }, halo) },
      { id: 'barrio', type: 'symbol', source: 'omt', 'source-layer': 'place',
        filter: ['in', ['get', 'class'], ['literal', ['suburb', 'neighbourhood', 'quarter']]],
        layout: { 'text-field': nombre, 'text-font': F, 'text-transform': 'uppercase', 'text-letter-spacing': 0.08,
                  'text-max-width': 7, 'text-size': ['interpolate', ['linear'], ['zoom'], 11, 8.5, 15, 11.5] },
        paint: Object.assign({ 'text-color': '#8c8c8c' }, halo) },
      { id: 'localidad', type: 'symbol', source: 'omt', 'source-layer': 'place',
        filter: ['in', ['get', 'class'], ['literal', ['town', 'village', 'hamlet']]],
        layout: { 'text-field': nombre, 'text-font': F, 'text-size': 13, 'text-max-width': 8 },
        paint: Object.assign({ 'text-color': '#bdbdbd' }, halo) },
      { id: 'ciudad', type: 'symbol', source: 'omt', 'source-layer': 'place', filter: ['==', ['get', 'class'], 'city'],
        layout: { 'text-field': nombre, 'text-font': FB, 'text-size': 19 },
        paint: Object.assign({ 'text-color': '#d6d6d6' }, halo) }
    ]
  };

  function dibujar(el) {
    return new Promise(function (resolver) {
      var pts = JSON.parse(el.dataset.puntos), general = el.dataset.general === '1';
      var m = new maplibregl.Map({ container: el, style: estilo, attributionControl: false, interactive: false,
        pixelRatio: 3, preserveDrawingBuffer: true, fadeDuration: 0, center: [-64.1866, -31.415], zoom: 11 });
      m.on('error', function (e) { console.error(e && e.error ? e.error.message : e); });
      m.on('load', function () {
        m.addSource('pos', { type: 'geojson', data: { type: 'FeatureCollection', features: pts.map(function (p) {
          return { type: 'Feature', geometry: { type: 'Point', coordinates: [p[1], p[0]] } }; }) } });
        m.addLayer({ id: 'pos', type: 'circle', source: 'pos', paint: { 'circle-radius': 4.6, 'circle-color': '#2bd629' } });
        var encuadre = pts.length ? pts : JSON.parse(el.dataset.alt || '[]');
        if (!general && encuadre.length) {
          var b = new maplibregl.LngLatBounds();
          encuadre.forEach(function (p) { b.extend([p[1], p[0]]); });
          m.fitBounds(b, { padding: 50, maxZoom: 14.5, duration: 0 });
        }
        m.once('idle', function () {
          var img = new Image();
          img.style.cssText = 'width:100%;height:100%;display:block';
          img.onload = function () { m.remove(); el.innerHTML = ''; el.appendChild(img); resolver(); };
          img.src = m.getCanvas().toDataURL('image/jpeg', 0.92);
        });
      });
    });
  }

  // Un mapa por vez: el navegador limita la cantidad de contextos WebGL simultáneos
  var mapas = Array.prototype.slice.call(document.querySelectorAll('.mapa'));
  mapas.reduce(function (p, el) { return p.then(function () { return dibujar(el); }); }, Promise.resolve())
    .then(function () { document.title = 'LISTO'; });
})();
"""


def armar_html(paginas, titulo):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{esc(titulo)}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@700&family=Ubuntu:wght@400;700&display=block">
<style>{CSS}</style></head><body>{''.join(paginas)}
<script src="https://cdnjs.cloudflare.com/ajax/libs/maplibre-gl/4.7.1/maplibre-gl.min.js"></script>
<script>{JS}</script></body></html>"""


def a_pdf(html_path, pdf_path, ancho_pt, alto_pt):
    chrome = next((c for c in CHROME if os.path.exists(c)), None)
    if not chrome:
        sys.exit('No se encontró Chrome ni Edge para generar el PDF.')
    # Tamaño de página: lo fija el CSS (@page size) que agregamos acá
    with open(html_path, encoding='utf-8') as f:
        s = f.read()
    s = s.replace('@page { margin: 0; }', f'@page {{ margin: 0; size: {ancho_pt}pt {alto_pt}pt; }}')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(s)
    r = subprocess.run(['node', os.path.join(BASE, 'imprimir.js'), html_path, pdf_path, chrome],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit('Error al imprimir el PDF:\n' + r.stderr[-2000:])


MESES = ['', 'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE',
         'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
DESCARGAS = os.path.join(os.path.expanduser('~'), 'Downloads')


def csv_mas_nuevo():
    """El CSV del SAE más reciente entre fuentes/ y Descargas (los exportes se llaman 'SAE - SAE (n).csv')."""
    import glob
    cand = glob.glob(os.path.join(BASE, '..', 'fuentes', '*.csv')) + glob.glob(os.path.join(DESCARGAS, 'SAE*.csv'))
    if not cand:
        sys.exit('No encontré ningún CSV del SAE en fuentes/ ni en Descargas.')
    return os.path.abspath(max(cand, key=os.path.getmtime))


def resolver_periodo(tipo, desde, hasta):
    """Acepta 'AAAA-MM' (mes completo), 'AAAA-MM-DD AAAA-MM-DD', o para el semanal solo la fecha de cierre (7 días)."""
    import calendar
    if desde and len(desde) == 7 and not hasta:
        y, m = map(int, desde.split('-'))
        return dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])
    if tipo == 'semanal' and not desde:
        # Semana de viernes a jueves (como los modelos): la última ya cerrada
        hoy = dt.date.today()
        d2 = hoy - dt.timedelta(days=(hoy.weekday() - 3) % 7 or 7)
        return d2 - dt.timedelta(days=6), d2
    if tipo == 'semanal' and desde and not hasta:
        d2 = dt.date.fromisoformat(desde)
        return d2 - dt.timedelta(days=6), d2
    if not (desde and hasta):
        sys.exit('Indicá el período: AAAA-MM, o DESDE HASTA (AAAA-MM-DD), o para el semanal la fecha de cierre.')
    return dt.date.fromisoformat(desde), dt.date.fromisoformat(hasta)


def nombre_archivo(tipo, d1, d2):
    """Mismos nombres que usaban los modelos."""
    import calendar
    mes_completo = d1.day == 1 and d2 == dt.date(d1.year, d1.month, calendar.monthrange(d1.year, d1.month)[1])
    if tipo == 'placa':
        return 'Placa numerica mensual (SAE) ' + (MESES[d1.month] if mes_completo else f'{d1:%d-%m-%y} AL {d2:%d-%m-%y}')
    if tipo == 'mensual' and mes_completo:
        return f'INFORME MENSUAL(SAE) {MESES[d1.month]}'
    return f'INFORME {tipo.upper()}(SAE) {d1.day}-{d1.month} AL {d2.day}-{d2.month}'


def verificar_pdf(pdf_path, tipo):
    """Controla cantidad de páginas y que cada página DJP tenga su mapa."""
    try:
        import pymupdf
    except ImportError:
        return []
    d = pymupdf.open(pdf_path)
    avisos = []
    esperadas = 1 if tipo == 'placa' else 24
    if d.page_count != esperadas:
        avisos.append(f'El PDF tiene {d.page_count} páginas (se esperaban {esperadas}).')
    if tipo != 'placa':
        sin_mapa = [i + 1 for i in range(1, d.page_count) if not any(x['width'] > 2000 for x in d[i].get_image_info())]
        if sin_mapa:
            avisos.append(f'Páginas sin mapa: {sin_mapa}. Volver a generar (puede ser un corte de internet).')
    return avisos


def sin_cuad_dentro(fuera):
    """Sucesos de "Fuera de Cuadrante" que caen dentro de un barrio vigente del programa en su fecha (solo control)."""
    import cobertura
    cob = cobertura.Cobertura()
    return sum(1 for s in fuera if cob.cubierto(s['lat'], s['lon'], s['fecha'].date()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tipo', choices=['mensual', 'semanal', 'placa'])
    ap.add_argument('desde', nargs='?')
    ap.add_argument('hasta', nargs='?')
    ap.add_argument('--csv', help='CSV del SAE (por defecto el más nuevo de fuentes/ o Descargas)')
    ap.add_argument('--no-corregir', action='store_true')
    a = ap.parse_args()
    d1, d2 = resolver_periodo(a.tipo, a.desde, a.hasta)
    csv_path = os.path.abspath(a.csv) if a.csv else csv_mas_nuevo()
    f_min, f_max = sae.rango_fechas(csv_path)
    avisos = []
    if d2 > f_max.date():
        avisos.append(f'El CSV llega hasta el {f_max:%d/%m/%Y %H:%M}: faltan datos para cubrir hasta el {d2:%d/%m/%Y}.')
    if d1 < f_min.date():
        avisos.append(f'El CSV empieza el {f_min:%d/%m/%Y}: faltan datos desde el {d1:%d/%m/%Y}.')

    suc = sae.cargar(csv_path, d1, d2, corregir_texto=not a.no_corregir)
    if not suc:
        sys.exit(f'No hay sucesos entre {d1} y {d2} en {csv_path}.')
    periodo = periodo_looker(d1, d2)
    os.makedirs(SALIDA, exist_ok=True)
    nombre = nombre_archivo(a.tipo, d1, d2)
    grupos = sae.por_djp(suc)
    gen = sae.indicadores(suc, n_tipo_positivos=20)

    if a.tipo == 'placa':
        paginas, tam = [pagina_placa(sae.indicadores(suc), periodo)], (930, 600)
    else:
        resumen = {k: (len(v), sum(s['positivo'] for s in v)) for k, v in grupos.items()}
        paginas = [pagina_portada(a.tipo, d1, d2), pagina_general(gen, resumen, periodo, 'm0')]
        for i, djp in enumerate(sae.DJP_INFORME + [sae.FUERA], 1):
            paginas.append(pagina_djp(djp, sae.indicadores(grupos[djp]), periodo, f'm{i}'))
        tam = (930, 1314.96)

    html_path = os.path.abspath(os.path.join(PLANT, f'_{a.tipo}.html'))
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(armar_html(paginas, nombre))
    pdf_path = os.path.abspath(os.path.join(SALIDA, nombre + '.pdf'))
    a_pdf(html_path, pdf_path, *tam)
    avisos += verificar_pdf(pdf_path, a.tipo)

    # Resumen para revisar antes de entregar
    print(json.dumps({
        'tipo': a.tipo, 'periodo': f'{d1:%d/%m/%Y} al {d2:%d/%m/%Y}', 'csv': csv_path,
        'csv_cubre': f'{f_min:%d/%m/%Y} al {f_max:%d/%m/%Y %H:%M}',
        'alertas': gen['alertas'], 'positivos': gen['positivos'], 'aprehendidos': gen['aprehendidos'],
        'mayores_menores': [gen['mayores'], gen['menores']], 'secuestros': gen['secuestros'],
        'por_djp': {k: [len(v), sum(s['positivo'] for s in v)] for k, v in grupos.items()},
        'djp_sin_alertas': [k for k, v in grupos.items() if not v],
        'sin_cuadricula_dentro_zona': sin_cuad_dentro(grupos[sae.FUERA]),
        'avisos': avisos, 'pdf': pdf_path,
    }, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
