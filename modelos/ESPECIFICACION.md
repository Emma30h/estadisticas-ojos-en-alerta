# Especificación de informes (relevada de los modelos)

Modelos de referencia, en esta carpeta:
- `INFORME MENSUAL(SAE) SEPTIEMBRE.pdf`: 24 páginas, período 01/09/26 al 30/09/26.
- `INFORME SEMANAL(SAE) 25-9 AL 1-10.pdf`: 24 páginas, período 25/09/26 al 01/10/26.
- `Placa numerica mensual (SAE) SEPTIEMBRE.pdf`: 1 página, apaisada.

Los modelos son tableros de Looker Studio exportados a PDF. Hoja A4 vertical, 930 × 1315 pt. Fondo oscuro azul/gris. Marca de agua "D.M.C.A." en los paneles. Pie en todas las páginas: "* FUENTE DE INFORMACIÓN: SAE".

## Informe mensual y semanal: misma plantilla, solo cambia el período

**Orden de páginas**

| Pág. | Contenido |
|---|---|
| 1 | Tapa |
| 2 | General |
| 3–23 | DJP 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 19, 20, 21, 22, 23, 24 (21 páginas) |
| 24 | Fuera de Cuadrante |

### Tapa
- Fondo con foto de la sala de monitoreo, oscurecida.
- Logo de la Policía arriba a la derecha.
- Texto "DIRECCION MONITOREO CORDOBESES EN ALERTA".
- Logo del ojo en el centro.
- "INFORME MENSUAL" o "INFORME SEMANAL", y debajo "(dd/mm/aa al dd/mm/aa)".

### Página General
1. **Encabezado:** ojo, "DIRECCIÓN MONITOREO CORDOBESES EN ALERTA", subtítulo "GENERAL", escudo de la Policía. A la derecha "Periodo:" con el rango, por ejemplo "1 sept 2026 - 30 sept 2026".
2. **RESUMEN DE SECUESTROS:** Armas de Fuego, Armas Blancas, Estupefacientes, Vehículos, Otros.
3. **Alertas y positivos:** barra vertical que muestra la proporción de positivos (azul con franja verde), "ALERTAS TOTALES" y "POSITIVOS".
4. **APREHENDIDOS:** tarjeta con ícono de esposas.
5. **ALERTA POR DJP / POSITIVO POR DJP:** columnas agrupadas, azul y verde, con etiqueta de valor. Las columnas van en orden alfabético de texto: 10, 11, 12, 13, 14, 15, 17, 19, 2, 20, 21, 22, 23, 24, 3, 4, 5, 6, 7, 8, 9, Fuera de Cuadrante.
6. **DÍA CRÍTICO:** barras horizontales de alertas y positivos, de domingo a sábado.
7. **HORA CRÍTICA:** columnas de alertas y positivos, de 0 a 23.
8. **TIPOLOGÍA DE POSITIVOS:** las 20 primeras, de mayor a menor, con barra verde.
9. **CONCENTRACIÓN DE POSITIVOS:** mapa oscuro de Google con un punto verde por positivo. Leyenda "Resultado ● Positivo".

### Páginas por DJP y Fuera de Cuadrante
1. **Encabezado:** igual al General, más el recuadro "DJP" con el número o con "FUERA DE CUADRANTE".
2. **RESUMEN DE SECUESTROS:** en estas páginas dice "Armas de Blanca" (sic).
3. **Alertas y positivos:** barra vertical, "ALERTAS TOTALES" y "POSITIVOS".
4. **DIAS CRÍTICOS:** barras horizontales, de domingo a sábado.
5. **APREHENDIDOS:** tarjeta.
6. **HORA CRÍTICA:** barras horizontales, de 0 a 23.
7. **TIPOLOGÍA:** dos listas, "ALERTAS" (las 15 primeras, barra azul) y "POSITIVOS" (las 15 primeras, barra verde).
8. **CONCENTRACIÓN DE POSITIVOS:** mapa con zoom en el DJP.

## Placa numérica mensual (1 página apaisada)
- **Encabezado:** "DIRECCIÓN MONITOREO CORDOBESES EN ALERTA", "Periodo:", "Resumen Numérico", ojo y escudo.
- **ALERTAS** (recuadro celeste) y **POSITIVOS** (recuadro verde).
- **APREHENDIDOS:** anillo MASCULINO (azul) / FEMENINO (rosa) en %, con TOTAL en el centro. Debajo, MAYORES y MENORES.
- **POSITIVOS:** las 15 primeras tipologías, con barra verde. **Ojo:** esta lista NO cuenta los positivos, sino los sucesos **con aprehendidos > 0**. Verificado: 32, 14, 13, 12, 8, 5 coinciden exacto.
- **RESUMEN DE SECUESTROS:** Armas de Fuego, Armas Blancas, Vehículos, Estupefacientes, Otros. El orden es distinto al del informe.

## Reglas de cálculo (verificadas contra el CSV, septiembre 2026)

| Indicador | Regla | Informe | CSV |
|---|---|---|---|
| Alertas | Sucesos con Fecha Creación dentro del período | 9.828 | 9.849 |
| Positivos | `Resultado = "Positivo"` | 348 | 352 |
| Aprehendidos | Suma de `aprehendidos totales` | 193 | 193 ✓ |
| Mayores / menores | Suma de `mayores` / `menores aprehendidos` | 163 / 30 | 163 / 30 ✓ |
| Armas de fuego, estupefacientes | Suma de cada columna | 7 / 11 | 7 / 11 ✓ |
| Armas blancas, vehículos, otros | Suma de cada columna | 30 / 79 / 438 | 31 / 80 / 439 |
| **DJP** | **Columna `Comuna` del SAE** (no el barrio). Sin `Cuadricula` → "Fuera de Cuadrante". Comuna 1, 16 y 18 no se muestran | ver pág. 2 | positivos por DJP **idénticos**; alertas ±0–3 |
| Día y hora | Desde Fecha Creación | 540, 498, 419… | 540, 500, 420… |

Las diferencias chicas son esperables: el CSV se exportó después del informe y algunos sucesos se editaron o se cargaron más tarde.

## Dudas abiertas (consultar)
- Anillo de género de la placa: el modelo dice 89,2% / 10,8%, pero la suma de masculinos y femeninas da 178 / 16 (91,8%). **Decisión de la usuaria: usar los datos del CSV** (suma de columnas).
- Semanal: va siempre de viernes a jueves (confirmado por la usuaria el 20/10/2026).
- Errores que tiene el modelo: "RIÃ‘A" en vez de "RIÑA" (mala codificación) y "Armas de Blanca". ¿Se copian tal cual o se corrigen?
- ¿Las alertas totales excluyen las Comunas 1, 16 y 18? La suma de las columnas por DJP da exactamente el total del informe (9.828).

## Implementación (generar_informe.py)
- Se usan como fondo las plantillas originales extraídas de los modelos (`plantillas/`). Encima van los números, las barras y el mapa, en las mismas coordenadas (en pt) que el modelo.
- Escalas de los ejes, como en Looker:
  - Días y horas: escala lineal con el máximo "redondo" (equivalente a d3.nice con 4 marcas).
  - Gráfico por DJP: escala logarítmica, altura = K·log10(v+1); la barra más alta usa la altura completa.
- Etiquetas del gráfico por DJP:
  - Alertas: arriba de la barra; si no entra, adentro.
  - Positivos: adentro si el valor tiene un solo dígito; si no, arriba.
- Tipologías:
  - Empates ordenados alfabéticamente. Looker no sigue un orden fijo, así que con empates el orden puede variar.
  - Los textos largos se cortan con "…".
- Mapa: vectorial (MapLibre + OpenFreeMap/OpenStreetMap) con un estilo copiado del tema "Dark" de Google que usa Looker. Se dibuja a resolución triple y se inserta como imagen. El General muestra la ciudad completa. Cada DJP se encuadra según sus positivos; si no tiene, según sus alertas.
- Con pocos datos, igual que Looker:
  - "Días críticos" y "Hora crítica" muestran solo los días u horas con alertas, repartidos en todo el alto del gráfico.
  - Una tipología vacía muestra "No hay datos".
- Anillo de género de la placa: suma de masculinos y femeninas aprehendidos (decisión de la usuaria).
