# Estadísticas Ojos en Alerta / Cordobeses en Alerta

Herramienta de estadísticas sobre los sucesos del SAE para los 234 barrios del programa.

## Carpetas

- `fuentes/`: datos originales, sin modificar. Cuando haya datos nuevos, se agregan acá.
  - `SAE - SAE (1).csv`: sucesos SAE (18/09/2025 – 15/10/2026).
  - `Barrios Ojos 234 (1).xlsx`: barrios con cuadrante y DJP (distrito).
  - `234 barrios LIMITES AMPLIADOS.kml`: polígonos de los barrios del programa y de los cuadrantes.
  - `Barrio_1.kmz`: barrios municipales de Córdoba Capital (2023).
- `catalogo/`: catálogo único de barrios y tabla de equivalencias de nombres.
- `scripts/`: procesos de limpieza y cálculo.
- `informes/`: informes generados.

## Criterios acordados

- **Nombre oficial del barrio:** el de la web del programa (cba.gov.ar/programa/ojos-en-alerta). El DJP sale del Excel.
- **Asignación de barrio a un suceso:** se usa la cuadrícula del sistema, traducida con `equivalencias_barrios.csv`. Si el suceso no tiene cuadrícula, se usa la coordenada (`lat.long`) contra el polígono del KML del programa.
- **Barrios que el sistema no registra por nombre** (2 de Abril, Residencial San Antonio, Quintas de Inaudi, Palmas de Claret, Jardín de Claret, Horizonte): se cuentan por coordenada.
- **Horizonte** = "Capdevila de Horizonte" (Excel) = "YOFRE Horizonte" (KML).
- **Procrear Marqués** = "Procrear" (Excel, DJP 9) = "HOGAR CLASE MEDIA - MARQUES DE SOBREMONTE" (KML) = "MARQUES DE SOBREMONTE II" (sistema). Es un barrio distinto de Marqués de Sobremonte.
- **Ampliación del programa:** se anunció el 22/07/2026 y los 86 barrios nuevos ("Cobertura Proyectada" en el KML) **están vigentes desde el 26/07/2026** (fecha oficial; configurable en `catalogo/criterios.json`). En el SAE sus cuadrículas aparecen recién el 30/07/2026.
  - Hasta el 25/07/2026 la zona del programa son los 138 barrios originales; desde el 26/07/2026, los 234.
  - Un suceso de un barrio nuevo anterior al 26/07 era correctamente "Fuera de Cuadrante".
  - Para comparar períodos, separar barrios originales de incorporados.
- **Sucesos sin cuadrícula:** en los informes van a "Fuera de Cuadrante", como hacían los compañeros (opción A, acordada). Solo se informa como control cuántos caen dentro de un barrio del programa vigente en su fecha (septiembre 2026: 11 de 669; julio 2026: 192, casi todos del 26 al 29/07 en barrios nuevos, cuando el SAE todavía no tenía sus cuadrículas).

## Problemas conocidos del CSV del SAE

- Las columnas Latitud y Longitud están rotas. Usar `lat.long`.
- Hay 491 Suceso ID duplicados.
- La fecha de arribo falta en el 64% de los sucesos.
- La columna BARRIO viene truncada. No usarla; usar Cuadrícula.

## Generar los informes

Desde la carpeta `scripts/`, con las fechas de inicio y fin del período (ambas inclusive):

```
python generar_informe.py mensual 2026-09-01 2026-09-30
python generar_informe.py semanal 2026-09-25 2026-10-01
python generar_informe.py placa   2026-09-01 2026-09-30
```

- Los PDF quedan en `informes/`.
- Por defecto se usa `fuentes/SAE - SAE (1).csv`. Para otro archivo: `--csv "ruta.csv"`.
- El texto con mala codificación del SAE ("RIÃ‘A") se corrige solo. Con `--no-corregir` queda igual que en el CSV.
- Se necesita conexión a internet para el mapa (OpenStreetMap), Chrome o Edge instalado, y Node.js. Las dependencias están en `scripts/node_modules`; si faltan, ejecutar `npm install` en `scripts/`.
- Las plantillas de fondo, los logos y la tapa se sacaron de los modelos y están en `plantillas/`. El detalle de cada indicador está en `modelos/ESPECIFICACION.md`.

## Tablero interactivo (para mostrar en vivo)

Doble clic en **`abrir_tablero.bat`**: actualiza los datos con el CSV más nuevo y abre `tablero/index.html` en el navegador.

- Mismo diseño que los informes: página General, una por DJP (con el selector "DJP") y la Placa numérica.
- El recuadro **Periodo** abre atajos (último mes completo, semana viernes–jueves, últimos 7 o 30 días, etc.) o fechas a elección. Todo se recalcula y se anima al instante.
- Tocando una barra del gráfico por DJP se abre ese DJP. Con el mouse sobre barras y puntos del mapa se ven los detalles. El mapa se puede mover y hacer zoom.
- **Presentación** recorre solo General → cada DJP → Placa (14 s por página). Teclas: F pantalla completa, P presentación, ← → cambiar de DJP, Esc salir.
- Los datos quedan en `tablero/datos.js`, que se genera con `python scripts/preparar_tablero.py` y no se sube a GitHub. El mapa y las tipografías necesitan internet.

## Consultas a pedido

`python scripts/consultas.py --desde AAAA-MM --por barrio [--filtro ...] [--comparar ...] [--tiempos] [--excel archivo.xlsx]`

Saca tablas por DJP, barrio, cuadrante, tipología, mes, semana, día u hora, con todos los criterios aplicados. Puede comparar contra otro período y exportar a Excel. Para ver todas las opciones: `python scripts/consultas.py -h`.

## Controlar un CSV nuevo

Antes de usar un CSV nuevo, desde `scripts/`:

```
python revisar_csv.py
```

Revisa estructura, fechas cubiertas, export cortado, señales de paso por Excel o Sheets, duplicados, datos de ubicación faltantes, sucesos sin cuadrícula dentro de la zona vigente, valores y cuadrículas nuevas y coherencia de aprehendidos. El resultado queda en `informes/controles/`. Con `--crear-referencia` se toma el CSV actual como referencia de "valores conocidos".

## Regenerar el catálogo

Desde la carpeta `scripts/`:

```
sh generar_catalogo.sh
```

## Usar en otra PC (repositorio de GitHub)

El proyecto está en un repositorio **privado** de GitHub. **No incluye** los CSV del SAE, los informes generados ni los PDF modelo, porque tienen datos sensibles (ver `.gitignore`).

1. Instalar Python (marcar "Add python.exe to PATH"), Node.js (versión LTS), Git y Chrome o Edge.
2. Descargar el proyecto: `git clone <dirección del repositorio>`.
3. Hacer doble clic en `instalar.bat`.
4. Abrir Claude Code en esa carpeta. La skill `informes-sae` viene incluida en `.claude/skills/`.
5. Descargar el CSV del SAE y pedir el informe.

Para guardar cambios (criterios, equivalencias, scripts) y llevarlos a otra PC: `git add -A`, `git commit -m "..."`, `git push`. En la otra PC: `git pull`.
