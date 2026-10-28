# Registro de progresos — Amazon Basin Monitor

Cada mejora funcional del monitor se registra aquí como un "Progreso" numerado,
con su commit marcado `Progreso N:` y una etiqueta git `progreso-N`.

## Tareas pendientes

- [ ] **Integrar el Monitoreo climático de forma nativa en el visor** (hoy es
  un tablero de Power BI embebido por iframe, ver Progreso 2): reconstruir sus
  indicadores con los datos/capas del propio visor (mismos filtros de país,
  idioma ES/PT/EN y límite de la cuenca), y retirar la dependencia de Power BI.
- [ ] Población expuesta estimada (WorldPop / zonas de afectación por amenaza)
  y control de solapamiento entre eventos del mismo territorio (seguimiento
  del Progreso 1).

## Progreso 1 — 2026-10-13 · KPI de población afectada reportada

**Qué hace**
- Nuevo panel "Población afectada reportada" en el Monitor con KPIs que suman,
  para los eventos visibles: personas afectadas, familias afectadas, fallecidos,
  heridos, desplazados, evacuados y cobertura ("eventos con cifras: n / N").
- Los KPIs se recalculan en vivo con todos los filtros: país, tipo de evento,
  prioridad (banner de alertas rojas), rango de fechas y el nuevo selector de
  **evento** puntual. El selector se ajusta a los demás filtros (si el evento
  elegido deja de cumplirlos, vuelve a "Todos").
- Tabla "Detalle por evento" con la cifra, fecha de la cifra y fuente enlazada.
- Las cifras aparecen también en la tarjeta de la lista, en el popup del mapa
  y en el CSV exportado.

**Fuente de datos**
- Nueva carpeta `Impacts/<EVENT_ID>.json` (opcional, una por evento). No
  modifica el esquema de 50 columnas de `Events/`.
- Campos: `EVENT_ID, AS_OF_DATE, DEATHS, INJURIES, AFFECTED_PERSONS,
  AFFECTED_FAMILIES, DISPLACED_PERSONS, EVACUATED_PERSONS, SCOPE
  (PARTIAL|CONSOLIDATED), SOURCE, SOURCE_URL, NOTES`.
- Números: entero ≥ 0, o `null` = no reportado (0 = reportado como cero).
- `scripts/rebuild_aggregates.py` valida estos archivos y añade el objeto
  `impact` a cada evento en `events.json`. El workflow se dispara también con
  cambios en `Impacts/**`.

**Reglas de cálculo**
- Solo cifras reportadas por fuentes; nunca proyecciones ni estimaciones.
- Una cifra por evento = la última reportada (se reemplaza, no se suman
  actualizaciones sucesivas).
- Familias y personas se suman por separado (sin conversión).
- `*` en un KPI = incluye cifras parciales (`SCOPE = PARTIAL`).
- Limitación conocida: eventos distintos en el mismo territorio pueden
  solaparse (se resolverá en un progreso posterior).

**Carga inicial**: AMZ-20260902-001 (7.323 personas, parcial — Eirunepé) y
AMZ-20261006-001 (7.442 familias + 517 personas — Porto Velho).

### Corrección 1.1 — 2026-10-13
- El workflow "Reconstruir agregados" también se disparaba al empujar la
  etiqueta `progreso-1` y fallaba ("You are not currently on a branch").
  Ahora solo corre en pushes a `main`, usa un grupo de concurrencia y hace
  `git pull --rebase` antes del push. La reconstrucción del Progreso 1 sí se
  completó en la corrida de la rama (commit 221b797).

## Progreso 2 — 2026-10-13 · Pestaña "Monitoreo climático" (provisional)

- Nueva pestaña **Monitoreo climático** (PT: Monitoramento climático, EN:
  Climate monitoring) junto a Monitor y Pronóstico, con el tablero de Power BI
  publicado en la web embebido en un iframe y un enlace para abrirlo en
  pantalla completa.
- El tablero solo se carga al abrir la pestaña (no ralentiza el Monitor).
  Enlace directo: `index.html#clima`.
- Pestañas más compactas en pantallas angostas para que quepan las tres.
- **Provisional**: queda como tarea pendiente su integración nativa en el visor
  (ver "Tareas pendientes").

### Documentación — 2026-10-13
- Panel de metodología del visor (botón "i", ES/PT/EN): nuevas secciones
  "Población afectada reportada (Progreso 1)", "Monitoreo climático
  (Progreso 2)" e "Historial de versiones".
- Bitácora agregada a las guías técnica y no técnica (carpeta local
  `Amazon_Monitor/Claude outputs/`).
- Regla: cada nuevo Progreso se registra en este archivo, en el panel "i" del
  visor y en ambas guías.

## Progreso 3 — 2026-10-14 · Capa ENSO/SST: de Google Earth Engine a NASA GIBS

**Qué cambia**
- La capa "Anomalía SST (ENSO)" del Monitor ya no se calcula a diario con
  Google Earth Engine: ahora dibuja directamente la tesela pública y oficial
  de **NASA GIBS** (producto `GHRSST_L4_MUR_Sea_Surface_Temperature_Anomalies`,
  la misma imagen que muestra NASA Worldview), vía una URL REST fija en
  `GoogleMapsCompatible_Level7` (EPSG:3857). Usando `default` en el slot de
  tiempo, la tesela resuelve siempre a la última fecha disponible — sin
  necesidad de ningún cálculo ni publicación propia a diario.
- La capa queda **activada por defecto** (antes estaba apagada por defecto) y
  tiene su propia leyenda de colores (esquina inferior derecha del mapa, con
  la escala oficial SVG de NASA GIBS), visible solo mientras la capa esté
  encendida.
- Verificado en vivo antes de implementar: la URL responde con PNG real
  (256×256), confirmado también el rezago típico de 1-2 días entre la fecha
  de hoy y la última imagen disponible — suficiente para un indicador de
  evolución lenta como ENSO.

**Qué se retira (archivado, no borrado)**
- `scripts/setup_enso_sst_climatology.py` y la función `update_sst_layer()`
  de `scripts/fetch_and_publish.py` (cálculo de la anomalía contra una
  climatología 1991-2020 vía Earth Engine) se movieron, sin cambios, a
  `legacy/enso_gee_pipeline/` (ver su `README.md`), a pedido explícito de
  Jerson, como registro de lo hecho — no porque sigan en uso.
- El workflow `publish.yml` ya no instala `earthengine-api` ni usa los
  secrets `GEE_SERVICE_ACCOUNT_EMAIL`/`GEE_SERVICE_ACCOUNT_KEY` (se dejaron
  configurados en el repositorio, sin usarse). Solo sigue actualizando
  `firms_hotspots.json`.
- `sst_layer.json` (la última salida del pipeline anterior) se archivó como
  `legacy/enso_gee_pipeline/sst_layer_last_generated.json`; ya no se lee
  desde `index.html`.

**Documentación actualizada**: panel de metodología del visor (ES/PT/EN) —
nueva sección "Anomalía SST / ENSO (Progreso 3)" e historial de versiones.


## Progreso 4 — 2026-10-21 · Informe Situacional Regional trimestral (botón + pipeline de datos)

**Qué cambia**
- Nuevo botón **"Informe trimestral"** en la barra de herramientas del visor
  (junto a "Exportar CSV"), que enlaza a una ruta fija
  `Reports/Informe_trimestral_vigente.pdf` — nunca cambia de nombre, así que
  no hay que tocar el visor cada trimestre. Si existe `Reports/latest.json`,
  el botón muestra junto al texto el trimestre del informe vigente (p. ej.
  "Informe trimestral (último: 2026-Q3)"); si no existe todavía (antes de la
  primera publicación aprobada), el botón se ve igual pero no tiene PDF que
  descargar — comportamiento esperado, no es un error.
- Nuevo script **100% determinista** `scripts/build_quarterly_report_data.py`:
  lee `Events/` e `Impacts/` y genera `Reports/<AAAA-QN>/data.json` con los
  conteos de prioridad, la tabla de eventos del periodo, las cifras de
  impacto reportadas y una clasificación preliminar de nivel de fuente (1-4)
  por palabra clave (deja sin clasificar — nunca adivina — lo que no
  reconoce). Alcance: los 6 países del proyecto (Bolivia, Brasil, Colombia,
  Ecuador, Perú, Venezuela), informe regional único, no por país.
- El resumen ejecutivo, la relevancia AA por sector y las recomendaciones
  sectoriales (secciones 1, 5 y 6 de la plantilla de informe) NO se generan
  con este script — no son datos existentes, son contenido analítico. Se
  redactarán en un Project de Cowork separado, dedicado a esto, con
  **revisión y aprobación humana obligatoria antes de publicarse** (ver
  `claude/propuesta-proyecto-narrativa-informe-trimestral.md` en el Project
  de Claude). Pendiente: crear ese Project y la tarea programada trimestral.

**Documentación actualizada**: panel de metodología del visor (ES/PT/EN) —
nueva sección "Informe situacional regional (Progreso 4)" e historial de
versiones.

## Progreso 5 — 2026-10-22 · Menú de descargas + corrección del selector de idioma

**Qué cambia**
- Los botones separados **"Exportar CSV"** e **"Informe trimestral"** se
  unificaron en un único menú desplegable **"Descargar"** (icono de
  descarga), con tres opciones: "Datos de eventos (CSV)" (el CSV de eventos
  filtrados, ya existente, solo renombrado para describir mejor su
  contenido), "Informe trimestral" (igual que antes) y nuevo
  **"Informe mensual por país"**, que despliega un submenú para elegir uno
  de los 6 países del proyecto.
- Los enlaces de informe mensual apuntan a una ruta fija por país
  (`Reports/Informe_mensual_<pais>_vigente.pdf`, p. ej.
  `Reports/Informe_mensual_bolivia_vigente.pdf`), siguiendo la misma
  convención de nombre fijo ("vigente") usada para el informe trimestral
  (Progreso 4). Esa ruta **todavía no existe** — los enlaces descargan error
  404 hasta que exista un pipeline que genere y publique el informe mensual
  por país; comportamiento esperado, igual que pasó con el informe
  trimestral antes de su primera publicación. Pendiente: definir y construir
  ese pipeline (plantilla ya generada en sesiones previas, ver bitácora del
  Project de Claude).
- **Corrección de bug visual**: en anchos intermedios (banner angosto, pero
  por encima del punto de quiebre móvil de 760px), el selector de idioma
  (`<select>`) quedaba posicionado en absoluto de forma independiente del
  bloque de título/subtítulo, y en ciertos anchos se superponía
  visualmente al subtítulo del banner. Se reemplazó el `<select>` por un
  **botón/ícono de idioma** (globo + código de 2 letras: ES/PT/EN) con su
  propio menú desplegable, y el título/subtítulo dejó de posicionarse en
  absoluto — ahora título y botón de idioma fluyen en una columna dentro
  del layout flex del banner, lo que elimina la superposición en cualquier
  ancho de pantalla (verificado en ~1100px, ~1400px y 375px/móvil).

**Documentación actualizada**: panel de metodología del visor (ES/PT/EN) —
nueva sección "Menú de descargas e informe mensual por país (Progreso 5)" e
historial de versiones.

## Publicación — 2026-10-26 · Primer Informe Situacional Regional (2026-Q3)

**Qué cambia**
- Primera publicación real a través del pipeline del Progreso 4: se subió
  `Reports/Informe_trimestral_vigente.pdf` (Informe Situacional Regional
  2026-Q3, 1 agosto – 30 septiembre de 2026, 8 páginas, con revisión humana
  antes de publicarse) y se creó `Reports/latest.json`
  (`{"label": "2026-Q3", "period": {...}, "publishedAt": "2026-10-26"}`),
  que el visor lee para mostrar el trimestre vigente junto al botón
  "Informe trimestral" (p. ej. "Informe trimestral (último: 2026-Q3)").
- Se subió también `Reports/2026-Q3/data.json`, el insumo de datos
  determinista generado por `scripts/build_quarterly_report_data.py` para
  ese trimestre (24 eventos, 2 rojos / 11 naranja / 11 verde en los 6
  países del proyecto).
- Se corrigió `scripts/build_quarterly_report_data.py` (necesario para
  generar este informe correctamente): reconoce variantes de nombre de país
  en inglés (`Brazil`/`Peru`, como vienen en `Events/`) además de las
  variantes en español ya soportadas, y excluye explícitamente los eventos
  con `AMAZON_BASIN_STATUS: OUTSIDE` del alcance regional del informe.

**Documentación actualizada**: panel de metodología del visor (ES/PT/EN) —
se actualizó la sección "Informe situacional regional (Progreso 4)" para
reflejar que ya hay un informe publicado (antes decía que el botón no
tendría informe disponible hasta la primera publicación aprobada) — y este
archivo.


## Progreso 6 — 2026-10-27 · Alertas IDEAM (hidrología, deslizamientos, incendios)

**Qué cambia**
- Nueva pestaña **"Alertas IDEAM"** en el visor, con su propio mapa
  (independiente del mapa del Monitor), que muestra 3 capas publicas y
  gratuitas de IDEAM (`bart.ideam.gov.co`), filtradas a la porcion
  colombiana de la cuenca (Amazonas, Caqueta, Putumayo):
  1. **Hidrología** — subzonas hidrográficas con alerta vigente hoy
     (amarilla/naranja/roja), filtradas al área hidrográfica oficial
     "Amazonas" de IDEAM. El archivo de origen solo lista subzonas con
     alerta activa, así que en muchos días esta capa estará vacía — eso
     es el comportamiento esperado, no un error.
  2. **Deslizamientos** — índice diario de amenaza por lluvia acumulada
     (alta/moderada/baja), por municipio.
  3. **Incendios** — índice diario de amenaza de incendio de la
     cobertura vegetal (alta/moderada/baja), por municipio.
- Estas 3 capas son **índices de amenaza/alerta**, no eventos confirmados:
  nunca escriben en `Events/` ni en `Impacts/`, nunca crean ni actualizan
  un `Event_ID`, y se reescriben completas cada corrida (sin acumular
  historial). Viven deliberadamente separadas de la base de eventos.
- Nuevo script determinista `scripts/fetch_ideam_alerts.py` (sin IA, sin
  costo de tokens) y workflow `.github/workflows/fetch-ideam.yml` (cron
  diario, 06:00 hora Bogotá) que descargan las 3 capas, cruzan
  deslizamientos/incendios por código DANE contra
  `IDEAM_Alerts/municipios_cuenca_amazonica.geojson` (límites oficiales de
  los 40 municipios de Amazonas/Caquetá/Putumayo — IGAC / Ministerio de
  Ambiente, generado una sola vez, no se vuelve a descargar a diario), y
  escriben `IDEAM_Alerts/{hidrologia,deslizamientos,incendios,meta}.json`.
- La leyenda de la nueva pestaña usa la escala propia de IDEAM
  (amarilla/naranja/roja para hidrología; alta/moderada/baja para
  deslizamientos e incendios), deliberadamente distinta de los colores
  🔴🟠🟢 de `ALERT_PRIORITY` del monitor, para no confundir ambas escalas.

**Correcciones (27-10-2026, mismo día)**
- **Visibilidad por país**: la pestaña "Alertas IDEAM" solo cubre Colombia,
  así que ahora solo aparece (botón y contenido) cuando el filtro de país
  del Monitor está en **Colombia** — no se muestra con "Todos" ni con
  ningún otro país. Si la pestaña estaba abierta y el filtro cambia, se
  regresa automáticamente a Monitor.
- **Bug de idioma corregido**: la etiqueta "Actualizado:"/"Updated:" no se
  traducía al cambiar de idioma después de cargar la pestaña (se quedaba
  en el idioma con el que se inicializó el mapa). Ya se recompone en cada
  cambio de idioma, igual que el resto del texto de la pestaña.
- **Verificación de datos contra el servidor de IDEAM**: se confirmaron
  en vivo las 3 fuentes usadas por `fetch_ideam_alerts.py` contra todo el
  contenedor `bart.ideam.gov.co/ospa/` (no solo `Alertas/modelos/`):
  - `deslizamientos/ultimo/amenaza_idd.csv` (la que usa el script) y
    `deslizamientos/ultimo/2026_amenaza_idd_vidhag.csv` contienen **los
    mismos 471 registros**, solo con nombres de columna distintos
    (`DEPARTAMENTO`/`MUNICIPIO` vs `DEPTO`/`GEOGRAPHIC`) y una columna
    numérica adicional (`nivel_numero`) en la versión "vidhag" — ambas
    son válidas, no hay discrepancia de datos.
  - `incendios/ultimo/amenaza_icv.csv` (la que usa el script) se actualiza
    a diario (confirmado hoy, 27-10-2026); en cambio
    `incendios/ultimo/2026_amenaza_icv_vidhag.csv` **no se actualiza desde
    el 16-06-2026** (archivo abandonado/obsoleto, esquema distinto con
    columna `PROBABILIDAD` 1-5 en vez de `TEXTO_AMENAZA`) — confirma que
    el script ya usa la fuente correcta y vigente, no la obsoleta.
  - `hidrologia/` (shapefile `Alertas_vigentes.*`) coincide exactamente
    con lo que usa el script, actualizado hoy.
  - No se encontró ninguna nota metodológica oficial dentro de
    `bart.ideam.gov.co/ospa/` (se revisó todo el contenedor, incluyendo
    `DatosAbiertos/` y `varios/`, que tienen series históricas completas
    por subzona/municipio — útiles para un futuro análisis de tendencias,
    pero no para el mapa de "alerta vigente" actual). La semántica de los
    niveles (Roja = "para tomar acción", Naranja = "para prepararse",
    Amarilla = informativa) y la paleta oficial de colores
    (Alta/Roja=#FF0000, Moderada/Naranja=#FFAA00, Baja/Amarilla=#FFFF00,
    según el renderizador del propio visualizador de IDEAM) se confirmaron
    por fuera del servidor de datos. Los colores usados en nuestra pestaña
    (`#d62828`/`#f08c00`/`#f1c40f`) son una versión más suave de esa misma
    escala roja/naranja/amarilla — coherentes con el estándar de IDEAM.

**Correcciones (27-10-2026, misma tarde — segunda ronda, feedback de UX)**
- **Popups sin identificar la capa**: al hacer clic en un municipio/subzona
  resaltado, el popup no decía si era hidrología, deslizamientos o
  incendios (deslizamientos e incendios comparten la misma función de
  popup). Se agregó una etiqueta de capa en la parte superior de cada
  popup ("Hidrología" / "Deslizamientos" / "Incendios").
- **Nomenclatura distinta para el mismo color**: hidrología usa su propia
  escala (Alerta Roja/Naranja/Amarilla) y deslizamientos/incendios usan la
  suya (Amenaza Alta/Moderada/Baja) — ambas con los mismos 3 colores, pero
  nombres distintos, lo que generaba confusión. Se armonizó así: cada
  popup y la leyenda ahora muestran primero un nivel común (Alto/Medio/
  Bajo, mismo color en las 3 capas) y, debajo, el término nativo de IDEAM
  entre paréntesis (p. ej. "Alto (IDEAM: Roja)" en hidrología y "Alto
  (IDEAM: Alta)" en deslizamientos/incendios). La leyenda del mapa se
  unificó en una sola lista de 3 niveles, con ambas nomenclaturas visibles
  lado a lado bajo cada color, en vez de dos listas separadas sin
  relación explícita entre sí.
- **Nota de fuente simplificada**: se quitó la mención a "sin
  autenticación" (dato técnico irrelevante para el usuario) del pie de la
  pestaña IDEAM en los 3 idiomas; ahora dice simplemente "datos públicos".

**Documentación actualizada**: panel de metodología del visor (ES/PT/EN) —
nueva sección "Alertas IDEAM (Progreso 6)" e historial de versiones — y
este archivo.

## Actualización — 2026-10-28 · Informe Situacional Regional 2026-Q3

**Qué cambia**
- Se reemplazó `Reports/Informe_trimestral_vigente.pdf` por la versión
  revisada del informe 2026-Q3 (mismo periodo y mismos datos: 24 eventos,
  2 rojos / 11 naranja / 11 verde):
  - el mapa coroplético por admin 1 muestra los nombres de los
    departamentos/estados con eventos (en lugar del número de eventos) y
    tiene título propio; el color sigue indicando el número de eventos;
  - las fuentes dejan de ir como notas al pie y se citan al final del
    documento, en la sección "7. Fuentes" (30 fuentes numeradas, con
    referencias en superíndice enlazadas desde el texto).
- `Reports/latest.json`: `publishedAt` pasa a `2026-10-28`.

**Documentación actualizada**: panel de metodología del visor (ES/PT/EN) —
la sección "Informe situacional regional (Progreso 4)" indica la fecha de
última actualización — y este archivo.
