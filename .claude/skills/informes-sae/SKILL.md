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

## Mensajes de WhatsApp del 101 (hechos ingresados a través del 911)

Pedido diario de la usuaria: un mensaje para la jefa con los hechos que cargaron ciertos operadores, a partir de la **"Tabla de Incidentes"**
(CSV con `;` que exporta el SAE; es otro formato que el "SAE - SAE (n).csv": fechas `26-10-26 17:47:45`, columna `Detenidos Totales`).
Usá **`scripts/mensaje_whatsapp.py`** (no generes los textos a mano):
```
python mensaje_whatsapp.py --operadores luca.bustamante,martina.ariza                 # CSV más nuevo de Descargas, los dos modelos
python mensaje_whatsapp.py --csv "C:/ruta/Tabla de Incidentes (1).csv" --operadores ... --desde 07:00 --hasta 19:00 --modelo corto
```
- **Operadores:** cambian cada día. `--operadores` acepta usuarios (`luca.bustamante`) o los nombres que pase la usuaria (`"Bustamante Luca David,Ariza Martina"`; el usuario es `nombre.apellido`). Preguntá cuáles entran hoy; si un usuario no aparece en la tabla, decilo (no lo inventes ni uses uno parecido: `martina.torres` es otra persona que `martina.ariza`).
- **Horario:** por defecto 07:00 a 19:00; se cuentan los hechos por hora de creación. Si el CSV se exportó antes del cierre del horario, avisá que pueden faltar hechos.
- **Modelo `corto`** (el de la jefa, solo números): título "HECHOS INGRESADOS A TRAVÉS DEL 911", fecha, horario, Cantidad de Hechos, Positivos, subtítulo ZONA y por zona "N hechos · N positivos". Sin aprehendidos ni tipificaciones.
- **Modelo `detallado`:** igual + aprehendidos (total y por zona) y, por zona, cada tipificación con su cantidad, y al final la lista de aprehendidos con la zona.
- **Modelo `positivos`:** igual que el detallado, pero por zona solo lista la tipificación de los hechos **positivos** (`--modelo positivos`; `ambos` = corto + detallado).
- **101 y Base Olimpo por separado:** el mensaje del 101 son los hechos de los operadores del día (`--operadores`). El de **Base Olimpo** son todos los demás hechos de la tabla: mismos operadores con `--resto` (título "HECHOS INGRESADOS A TRAVÉS DE BASE OLIMPO", archivos `Mensaje WhatsApp Base Olimpo ...`). Base Olimpo carga las 24 Hs: avisá cuántos hechos quedan fuera del horario elegido.
- **Zonas** (`catalogo/zonas_mensaje.json`, DJP → zona): NORTE 15, 24, 14, 23 · ESTE 9, 6, 13, 8, 17, 7 · SUR 4, 11, 12, 16, 21, 5 · CENTRO/OESTE 10, 19, 18, 20, 22, 1, 2, 3 (el "24 BIS" de la usuaria es el DJP 24). Los hechos sin Cuadricula van aparte en **FUERA DE CUADRANTE**. Si tienen Cuadricula pero la **Comuna viene vacía** (pasa en la Tabla de Incidentes: el cuadrante queda en Comisaria; el 27/10 fueron 12 de 170, casi todos Norte), el DJP sale del barrio (`catalogo/equivalencias_barrios.csv`) y el script lo avisa; acordado con la usuaria el 27/10/2026 (coincide con la Comuna del SAE en 144 de 148 casos, y las diferencias no cambian de zona). Y si **no tienen Cuadricula pero la coordenada cae dentro de la cobertura**, en los mensajes se cuentan en la zona de ese cuadrante. Desde el 29/10/2026 la cobertura sale de `fuentes/SECTORES OJOS EN ALERTA.kml` (KML actualizado de la usuaria: carpetas CUADRANTE 1..8 = perímetros de cobertura, 111,8 km², ~3 km² más que los 234 barrios, incluye Kennedy/Ampliación Kennedy/Ejército Argentino; carpeta Barrios = 830 barrios de la ciudad con su comisaría; SEMC = zonas de salud, no se usa). Zona por cuadrante: C2 Norte · C1, C7 Centro/Oeste · C3, C4, C8 Este · C5, C6 Sur (coincide con la zona por DJP en los 234). Antes se usaba el polígono de los 234 barrios (27/10: 2 hechos en Empalme Obreros y Empleados que el SAE dejó sin barrio; "tenemos cobertura en Empalme"). Esto es solo para los mensajes de WhatsApp; en los informes sigue "sin cuadrícula → Fuera de Cuadrante". Sin barrio ni coordenada: Fuera de Cuadrante, aunque el relato nombre el móvil (QUEBRADA11, etc.) — "sin ubicación no se asigna" (usuaria, 27/10/2026).
  Reglas agregadas el 28/10/2026 (decididas por la usuaria): **con barrio, manda el barrio** aunque la Comuna del SAE sea de otra zona (112184 Providencia venía con DISTRITO 2); sin barrio, la coordenada a **10 m o menos** del borde de un barrio cuenta como dentro (`BORDE_M`, calle límite); una Cuadricula que no es barrio (ej. "COMISARIA 23B (EX 25 (SALDAN))") se trata como sin barrio; hechos que la usuaria ubica a mano van en `catalogo/ubicaciones_manuales.json` (Suceso ID → barrio, DJP).
- **Controlá los operadores:** si uno de los que pasa la usuaria tiene muy pocos hechos o no tiene relatos tipo 101 ("Ingresa llamado al 911", "SR CCA..."), buscá otro usuario con el mismo nombre y preguntá antes de armar el mensaje (28/10: pasó "erika.aguirre", con 2 reportes de móvil; la del 101 era erika.gutierrez, con 21).
- **Antes de entregar,** corré el control independiente (cada hecho contra Comuna, barrio, cuadrante y KML) y revisá uno por uno los Fuera de Cuadrante: distancia al barrio más cercano y relato. No agrupar por DJP en el mensaje.
- **Modelo `numerica`** (pedido de la jefa del 27/10/2026, palabra clave de la usuaria: "Numérica 101"): **un solo mensaje** con dos bloques. "SUCESOS INGRESADOS A TRAVÉS DEL 911" = hechos de `--operadores` (los del 101), con FECHA, HORARIO, 📋 CANTIDAD DE SUCESOS y `*Z. NORTE:* 01` (dos cifras, también `*FUERA DE CUADRANTE:* 01`). "SUCESOS INGRESADOS A TRAVÉS DEL PROGRAMA CORDOBESES EN ALERTA" = el resto (Base Olimpo), solo cantidad y `*Z. NORTE:* 27` (sin cero adelante). Los dos puntos van igual en todas las líneas, dentro de la negrita como en "CANTIDAD DE SUCESOS:" (la usuaria lo pidió el 28/10; el modelo de la jefa los tenía desparejos). Sin positivos. No lleva `--resto`. Turno noche: `--desde 19:00 --hasta 07:00` (cruza la medianoche; la FECHA es el día en que empieza, `--fecha` si hace falta). Guarda `informes/Mensaje WhatsApp numerica DD-MM-AAAA HHMM-HHMM.txt`. **Fuente del bloque 911 (desde 28/10/2026):** la usuaria exporta del SAE una segunda Tabla de Incidentes filtrada por origen 911; pasala con `--csv911` (manda sobre `--operadores`; si se pasan los dos, el script avisa los hechos del 911 de otros operadores y los de los operadores que no son de origen 911). El 28/10 fueron 54: los 53 de las dos operadoras + 1 de leandro.iglesias. El **resumen del 911** (modelo `detallado`) también sale así: `--csv <tabla completa más nueva> --csv911 <exportación 911> --modelo detallado` (usa los datos de la tabla completa, que trae las tipificaciones corregidas por Auditoría). No deduzcas el origen del relato: "Ingresa alerta del Nº de línea (351…)" aparece también en hechos de origen 911.
- Formato WhatsApp (`*negrita*`), "Hs" con mayúscula, "Z." no se usa (salvo en `numerica`, que copia el modelo de la jefa). El script imprime los textos y los guarda en `informes/Mensaje WhatsApp 911 {corto|detallado} DD-MM-AAAA.txt`: pegalos en el chat tal cual.
- Antes de entregar leé los AVISOS que imprime: hechos sin finalizar (sin resultado), hechos fuera de horario, DJP fuera de las zonas, exportación anterior al cierre del horario. Mencionalos en una línea (ej. "1 hecho sin finalizar: 111140").
- **Revisión de Fuera de Cuadrante (29-31/10/2026):** cada hecho fuera, con calle más cercana (`fuentes/calles_osm_cordoba.json`, OpenStreetMap, fuera del repo), cuadrante más cercano y distancia, barrio municipal del KML y relato. Criterios de la usuaria: si lo trabajó un móvil del programa, cuenta en la zona del cuadrante aunque esté lejos (el móvil decide si lo labra); si el relato dice "FUERA DEL CUADRANTE (UT n)", "no forma parte del cuadrante" o "se deriva a distrito/Base de Coordinación", o lo atendió personal ajeno (CAP), queda fuera; encabezado "CUADRANTE <barrio> (UT n) - CORDOBESES EN ALERTA" = dentro (UT = DJP); "Cuadricula: X (CRIA n)" en el relato = barrio X. La coordenada del SAE puede venir corrida (114025: 4,5 km). **Los dudosos se preguntan en bloque** (a la usuaria le gusta definir el criterio) y se guardan en `ubicaciones_manuales.json`. Si el barrio es de otra zona pero Comuna, Comisaria y coordenada coinciden entre sí, manda la Comuna (`comuna_confirmada`: el SAE tiene dos "LAS FLORES", C6/DJP 4 y C7/DJP 20).
- **Mensaje "SUCESOS FUERA DE CUADRANTE"** (a mano, tras la numérica): FECHA, HORARIO, `📋 *CANTIDAD:* N` y por hecho `*SAE N:* Tipo. La coordenada del hecho se ubica en B° X (calle y calle), fuera del área de cobertura del programa (DJP N).` + lo que diga el relato ("Además, el relato indica…"). Marcar "(positivo)" si corresponde.
- Los archivos del detallado llevan el horario en el nombre (`... 911 detallado DD-MM-AAAA HHMM-HHMM.txt`) para que el turno noche no pise al de día.
- Placa/informe por DJP de esos mismos hechos: convertí la tabla al formato SAE y usá `generar_informe.py --csv` (el informe por zona excluye "Fuera de Cuadrante", la placa no).

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

## Trabajos y preguntas a pedido (sin PDF)

Para cualquier pedido distinto de los informes fijos ("robos por barrio en agosto", "comparar septiembre con agosto",
"tiempos de respuesta por DJP", "ranking de tipologías del DJP 15", "pasame esto en Excel") usá **`scripts/consultas.py`**,
que ya aplica todos los criterios: DJP, barrio oficial, cuadrante, zona vigente por fecha, etc. Ejemplos:
```
python consultas.py --desde 2026-09 --por barrio --filtro "categoria=ROBO" --top 15
python consultas.py --desde 2026-09 --por djp --comparar 2026-08 --tiempos
python consultas.py --desde 2026-09-01 --hasta 2026-09-30 --por barrio --por tipo --excel ../informes/NOMBRE.xlsx
```
- Dimensiones (`--por`, hasta dos): djp, barrio, cuadrante, tipo, categoria (lo anterior al paréntesis: ROBO, SOSPECHOSO…),
  mes, semana (viernes a jueves), dia, dia_semana, hora, resultado, barrio_nuevo, en_zona.
- Filtros: `campo=valor` (exacto) o `campo~texto` (contiene), por ejemplo `positivo=1`, `djp=15`, `barrio=San Vicente`.
- `--comparar` agrega el período anterior y la variación %. `--tiempos` agrega las medianas de despacho y arribo.
  Avisá que el arribo solo está cargado en ~1/3 de los sucesos.
- `--excel` deja una hoja Resumen y una hoja Sucesos (sin teléfonos, nombres ni relatos). Entregalo con SendUserFile.
- Los totales coinciden con los informes porque usa el mismo filtro de DJP. Si hace falta algo que no cubre, importá `consultas.cargar()` en un script corto.
- Si el pedido es para mostrar, ofrecé también el tablero (`tablero/index.html`) con el período elegido.
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
