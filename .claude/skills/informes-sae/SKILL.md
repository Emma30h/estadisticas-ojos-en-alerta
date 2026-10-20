---
name: informes-sae
description: >-
  Genera los informes estadísticos del SAE de la Dirección Monitoreo Cordobeses en Alerta (Policía de Córdoba):
  INFORME MENSUAL, INFORME SEMANAL y PLACA NUMÉRICA mensual, en PDF, idénticos a los modelos institucionales
  (General + una página por DJP + Fuera de Cuadrante). Usar SIEMPRE que se pida un informe, parte, placa o
  resumen estadístico del SAE, de alertas, positivos, aprehendidos o secuestros de Cordobeses en Alerta /
  Ojos en Alerta para un mes, una semana o un rango de fechas, aunque no se nombre la palabra "informe"
  (ej. "haceme el de octubre", "la placa del mes", "el semanal de esta semana", "cuántos positivos hubo en el DJP 15").
  También para preguntas de estadísticas sobre esos datos, barrios del programa, cuadrantes o DJP.
---

# Informes SAE — Cordobeses en Alerta

La herramienta es la carpeta del proyecto que contiene este `.claude/` (la llamamos BASE). En la PC original es
`C:\Users\bacic\Desktop\Proyectos\Estadisticas Ojos en Alerta\`; en otra PC puede estar en otro lado.
Si falta `scripts/node_modules`, es una PC nueva: corré `instalar.bat` desde BASE (o `pip install -r requirements.txt` y `npm install` en `scripts/`).
El repositorio no trae los CSV del SAE ni los informes ni los modelos en PDF, porque tienen datos sensibles: el CSV se descarga del SAE en cada PC.
Se construyó con la usuaria replicando los informes que hacían sus compañeros en Looker Studio; ella pidió
expresamente que el resultado sea **tal cual el modelo**, así que no cambies diseño, textos ni orden de páginas
por iniciativa propia: si algo parece mejorable, proponelo y esperá su respuesta.

Archivos de referencia (leelos solo si hace falta):
- `BASE/LEEME.md` — criterios acordados y uso general.
- `BASE/modelos/ESPECIFICACION.md` — cómo se calcula cada indicador y cada detalle visual, con dudas abiertas.
- `BASE/modelos/*.pdf` — los informes modelo originales.
- `BASE/catalogo/catalogo_barrios.csv` y `equivalencias_barrios.csv` — los 234 barrios del programa con sus nombres en cada fuente.

## Flujo para pedir un informe

1. **Entender qué y qué período.**
   - Mensual / placa: un mes calendario → `AAAA-MM`.
   - Semanal: va siempre de **viernes a jueves** (confirmado por la usuaria). Si dice "el semanal" o "la semana pasada"
     sin fechas, corré `semanal` sin fechas (toma la última semana viernes→jueves ya cerrada) y decí las fechas usadas. Si da fechas, usalas tal cual.
   - Un rango cualquiera también se puede (`DESDE HASTA`), con la plantilla del mensual o semanal según lo pida.
   - Si pide "todo" (mensual + placa), generá ambos.

2. **Conseguir los datos.** El generador toma solo el CSV más nuevo entre `BASE/fuentes/*.csv` y `Descargas/SAE*.csv`
   (el SAE exporta archivos llamados "SAE - SAE (n).csv"). Si la usuaria adjunta o nombra otro CSV, pasalo con `--csv`.
   **Cada vez que haya un CSV nuevo, primero corré `python revisar_csv.py`** (3 segundos) y contale en pocas líneas lo relevante:
   - Si dice ✗, no generes: explicá qué columna falta o cambió.
   - Los ⚠ habituales del CSV de referencia (los que también tenía el de octubre 2026): Excel/Sheets, 1 coordenada fuera de Córdoba, aprehendidos inconsistentes. Mencionalos en una sola línea, o no los repitas si ya los sabe.
   - Lo nuevo sí, en detalle: export cortado, días sin datos, valores o cuadrículas nuevas, suba de sucesos sin cuadrícula dentro de la zona.
   - Para cuadrículas nuevas, proponé a qué barrio oficial corresponden (el control sugiere uno por coordenada). Agregalas a `catalogo/equivalencias_barrios.csv` solo con su confirmación.

3. **Generar** (desde `BASE/scripts`, tarda ~1–1,5 min por informe por los mapas; la placa unos segundos):
   ```
   python generar_informe.py mensual 2026-10
   python generar_informe.py placa   2026-10
   python generar_informe.py semanal 2026-10-08              # 7 días que terminan ese día
   python generar_informe.py semanal 2026-10-02 2026-10-08   # fechas exactas, inclusive
   ```
   Usá `PYTHONIOENCODING=utf-8` y un timeout amplio (≥ 10 min). Si `node_modules` no existe, correr `npm install` en `scripts/`.

4. **Revisar el resumen JSON que imprime antes de entregar.** Contiene `csv_cubre`, totales, `por_djp`, `djp_sin_alertas` y `avisos`.
   - Si hay avisos de que el CSV **no cubre el período** (p. ej. el mes aún no terminó o el export es viejo), decíselo claro:
     el informe saldría incompleto. Preguntá si quiere que lo genere igual o si baja un CSV nuevo.
   - Si hay **páginas sin mapa**, volvé a generar (suele ser un corte de internet).
   - Mirá si algo llama la atención (un DJP en 0, un salto grande respecto del período anterior) y mencionalo en una línea;
     no lo "corrijas" en los datos.

5. **Entregar**: mandá el PDF con la herramienta de envío de archivos (SendUserFile) y respondé corto, en español:
   período, CSV usado, alertas / positivos / aprehendidos, y cualquier aviso. Los PDF quedan en `BASE/informes/`
   con los mismos nombres que usaban los compañeros (ej. `INFORME MENSUAL(SAE) OCTUBRE.pdf`, `INFORME SEMANAL(SAE) 2-10 AL 8-10.pdf`,
   `Placa numerica mensual (SAE) OCTUBRE.pdf`).

## Tablero interactivo

`BASE/tablero/index.html` replica los informes en el navegador con filtros de fecha y DJP. Si la usuaria pide "actualizá el tablero"
o va a mostrarlo con un CSV nuevo: corré `python preparar_tablero.py` desde `scripts/` (unos segundos) y decile que abra
`abrir_tablero.bat` o `tablero/index.html`. Usa las mismas reglas de cálculo que el PDF (portadas a JavaScript en el propio HTML):
si cambiás una regla en `sae.py` o `generar_informe.py`, replicala también en el tablero.

## Reglas de cálculo (ya implementadas en `scripts/sae.py`; no las cambies sin consultar)

- Alertas = sucesos con **Fecha Creacion** dentro del período; se descartan Suceso ID repetidos.
- Positivos = `Resultado == "Positivo"`.
- **DJP = columna `Comuna` del SAE** (no el barrio del catálogo). Sin `Cuadricula` → "FUERA DE CUADRANTE".
  Los DJP del informe son 2–15, 17, 19–24; las Comunas 1, 16 y 18 no se muestran ni suman en los totales (así lo hacía Looker).
- Aprehendidos, mayores/menores y secuestros = sumas de sus columnas.
- Placa: la lista "POSITIVOS" son las tipologías de los sucesos **con aprehendidos > 0** (no de los positivos).
- El texto mal codificado del SAE ("RIÃ‘A") se corrige a "RIÑA"; `--no-corregir` lo deja como el modelo.
- Diferencias de pocas unidades con un informe viejo son normales si el CSV se exportó otro día (el SAE se sigue editando).

## Decisiones ya tomadas (no volver a preguntar)
- Anillo de género de la placa (APREHENDIDOS masculino/femenino): se calcula con la suma de `masculinos aprehendidos` y
  `femeninas aprehendidas` del CSV. El modelo de septiembre daba otra cifra (89,2/10,8 % contra 91,8/8,2 %) y no se sabe por qué;
  la usuaria decidió guiarse por los datos del CSV.
- Semanal: siempre de viernes a jueves.

## Preguntas de estadística sueltas (sin PDF)

Para preguntas como "¿cuántos robos hubo en Alta Córdoba en agosto?" usá las funciones de `scripts/sae.py`
(`cargar`, `indicadores`, `por_djp`) en un script corto, con el mismo CSV y las mismas reglas.
Para responder por **barrio**, el criterio acordado es:
- Barrio = nombre de la `Cuadricula` del sistema traducido con `catalogo/equivalencias_barrios.csv`; si no hay cuadrícula, por coordenada (`lat.long`) contra el polígono del KML del programa.
- Nombres oficiales = los de la web del programa (columna 1 del catálogo); el DJP de un barrio sale del Excel oficial.
- Equivalencias especiales: "Horizonte" = Capdevila de Horizonte = "YOFRE Horizonte" (KML); "Procrear Marqués" = "Procrear" DJP 9 = "MARQUES DE SOBREMONTE II" (sistema), distinto de Marqués de Sobremonte.
- Seis barrios no existen como cuadrícula en el sistema y se cuentan por coordenada (2 de Abril, Residencial San Antonio, Quintas de Inaudi, Palmas de Claret, Jardín de Claret, Horizonte).
- Los 86 barrios nuevos ("Cobertura Proyectada" en el KML) están vigentes desde el **26/07/2026** (fecha oficial que dio la usuaria, en `catalogo/criterios.json`; en el SAE sus cuadrículas aparecen recién el 30/07). La zona del programa depende de la fecha: hasta el 25/07/2026, los 138 originales; desde el 26/07, los 234. Un suceso en un barrio nuevo antes del 26/07 era correctamente "Fuera de Cuadrante". Para comparar períodos, separá barrios originales e incorporados.
- En los informes, sin cuadrícula → "Fuera de Cuadrante" (acordado: no completar). Como control, informá cuántos de esos caen dentro de un barrio vigente en su fecha (el resumen del generador lo trae como `sin_cuadricula_dentro_zona`; sept. 2026: 11 de 669).
No hace falta aclarar estos criterios en los informes.

## Si algo falla
- "No se encontró Chrome ni Edge": hace falta uno de los dos instalado.
- Error de puppeteer / WebGL: verificar que `scripts/imprimir.js` lance Chrome con `--use-angle=swiftshader --enable-unsafe-swiftshader`.
- Sin internet no se dibujan los mapas (usan OpenFreeMap / OpenStreetMap) ni las tipografías de Google Fonts.
- Si el SAE cambia el nombre de alguna columna del CSV, `sae.cargar` va a fallar con KeyError: avisá cuál cambió y ajustá el mapeo.
