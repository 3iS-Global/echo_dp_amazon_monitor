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

## 2026-10-29 — Se quitan referencias a "Progreso N" de la UI; se corrige "Última actualización" congelada

**Feedback del usuario**: (1) pidió quitar cualquier referencia a la
numeración interna "Progreso N" de los textos visibles del visor (footnote
bajo el panel de población afectada, encabezados e historial de versiones
del botón "Acerca de"); (2) reportó que, aunque el día anterior se había
hecho una actualización, el panel seguía mostrando una fecha congelada en
"Última actualización" (20 de octubre).

**Causa raíz de la fecha congelada**: `meta.json` solo lo regenera
`rebuild-aggregates.yml`, disparado por `push` sobre `Events/**`/`Impacts/**`
— no corre a diario. Entre el 20-10-2026 y el 28-10-2026 no se tocó ningún
evento, así que `meta.json.lastUpdated` quedó fijo en `2026-10-20 18:02 UTC`
durante más de una semana, aunque `firms_hotspots.json` (vía `publish.yml`,
cron diario) y `IDEAM_Alerts/meta.json` (vía `fetch-ideam.yml`, cron diario)
sí se refrescaron cada día mientras tanto. El panel solo leía `meta.json`,
así que mostraba una fecha que no reflejaba la frescura real del sitio.

**Correcciones aplicadas**:
- Se quitó "Progreso N" del footnote `progressTag` y de los 6 encabezados
  y el historial de versiones del panel "i" (ES/PT/EN) — queda solo la
  descripción y la fecha. Los comentarios de código internos
  (`<!-- Progreso N: ... -->`, `// Progreso N: ...`) no se tocaron: no son
  visibles para el usuario y siguen la convención de seguimiento interna ya
  documentada en este mismo archivo.
- "Última actualización" ahora se calcula como la más reciente entre 3
  fuentes: `meta.json.lastUpdated` (eventos), la cabecera HTTP
  `Last-Modified` de `firms_hotspots.json` (leída del lado del cliente, sin
  tocar el pipeline de Python) y `IDEAM_Alerts/meta.json.last_run_utc`
  (`computeLastUpdated()` en `index.html`). No requirió cambios en ningún
  script de Python ni en los workflows — es puramente una ampliación de la
  carga de datos del lado del cliente (`Promise.all` en `index.html`).
- Verificado en vivo contra `https://3is-global.github.io/echo_dp_amazon_monitor/`
  (confirmada como la URL pública de referencia del proyecto): "Última
  actualización: 2026-10-29 21:10 UTC" (coincide con la hora de la última
  corrida de FIRMS); footnote sin "Progreso 1"; panel "i" sin ningún
  "(Progreso N)" en encabezados ni en el historial de versiones.

**Documentación actualizada**: panel de metodología del visor (ES/PT/EN) —
footnote y panel "i" sin "Progreso N" — y este archivo.

## 2026-11-01 — publish.yml y fetch-ideam.yml ahora corren también con cada push a main

**Contexto**: el fix del 29-10-2026 (ver sección anterior) solo corrigió lo
que el visor *muestra* como "Última actualización" — combinando del lado
del cliente la fecha más reciente entre las 3 fuentes de datos. Pero los
datos subyacentes de FIRMS e IDEAM seguían dependiendo exclusivamente de
sus cron diarios (`publish.yml` a las 15:00 UTC, `fetch-ideam.yml` a las
11:00 UTC): un push desde Cowork/Claude no los refrescaba, así que podían
seguir desactualizados hasta 24h frente al momento real del push.

**Corrección**: `publish.yml` y `fetch-ideam.yml` ahora también escuchan
`on: push: branches: [main]`, además de su `schedule` de siempre. Como los
tres workflows que hacen commit/push a `main` (los dos anteriores más
`rebuild-aggregates.yml`) podían terminar corriendo a la vez por el mismo
push, se les puso un único grupo de concurrencia compartido
(`amazon-monitor-main-writes`, antes cada uno tenía el suyo) para que
GitHub los encole en vez de dejarlos competir por el push a `main`.
`publish.yml` también gana el `git pull --rebase origin main` antes de su
push que ya tenían los otros dos (antes hacía un `git push` directo, que sí
podía fallar por "fetch first" si otro workflow empujaba un commit
primero).

**Verificado en vivo**: el push de este mismo cambio (commit `4cdcc5e` en
`origin`) disparó ambos workflows en segundos (confirmado vía la API de
GitHub Actions: `event: push`, `conclusion: success` para los dos), y cada
uno encontró datos nuevos y los publicó sin colisión — `79995c8`
("Actualizacion automatica de datos") y `51f597e` ("Actualizacion
automatica de alertas IDEAM"), ambos corridos y empujados en el mismo
minuto (17:53 UTC) sin fallo de push.

**Documentación actualizada**: `.github/workflows/publish.yml`,
`.github/workflows/fetch-ideam.yml`, `.github/workflows/rebuild-aggregates.yml`
(comentarios inline) y este archivo.

## 2026-11-01 (tarde) — Hallazgo: origin y 3iS-Global desincronizados en Events/Impacts

Al revisar la pregunta del usuario sobre el solapamiento de workflows, se
comparó `origin/main` contra `3is/main` directamente (`git diff --stat`,
conteo de eventos en `index.json`, `git log -- Events/` en cada remoto).
Resultado: `3is/main` le faltaban 3 commits de `Events/`/`Impacts/` que sí
estaban en `origin/main` (incl. la actualización del 28-10 de
AMZ-20260902-001). FIRMS e IDEAM sí estaban al día en ambos, porque corren
con cron propio en cada repo — pero los eventos, que son lo que de verdad
importa para el mapa, solo llegaban a `3iS-Global` cuando alguien los
replicaba a mano.

**Causa**: la tarea diaria programada (cuenta `jachicanoy@3is.org`) solo
hacía `git push` a `origin`; nunca tocaba el remoto `3is`.

**Decisión (Jerson, 01-11-2026)**: actualizar el prompt de la tarea diaria
para que haga push a los dos remotos cada corrida, igual que ya se hacía
manualmente en sesiones puntuales. El texto corregido del prompt (paso 6,
con el mismo patrón de rama temporal desde `FETCH_HEAD` + PAT que se usa en
este repositorio) queda documentado en el Project de Cowork
(`claude/contexto-migracion-github-2026-10.md`, sección 7). **Pendiente**:
esta cuenta (`jersoncatalyst@gmail.com`) no tiene acceso a esa tarea
programada — debe aplicarse desde la cuenta `jachicanoy@3is.org`.

## 2026-11-01 (noche) — Decisión: dos tareas diarias activas en paralelo

A raíz del hallazgo anterior (origin y 3iS-Global desincronizados), Jerson
creó la misma tarea diaria también en la cuenta `jersoncatalyst@gmail.com`
(08:43 Bogotá, trigger `trig_0136rVLAjj2UwZoUYX4RqDHL`), con el paso 6 ya
corregido para hacer push a los dos remotos. Al preguntársele si debía
desactivarse la tarea original de `jachicanoy@3is.org` (09:00 Bogotá, sigue
sin el fix, solo push a `origin`) para evitar duplicados, decidió **dejar
las dos activas por ahora**.

Riesgo aceptado conscientemente: gasto duplicado de búsquedas/tokens cada
día, y una probabilidad baja pero real de choque de `git` si ambas tareas
tocan el mismo `Events/<ID>.json` el mismo día. Importante: no hay
sincronización cruzada entre lo que una tarea escribe y lo que la otra ve
— cada una hace su propia búsqueda web y su propia deduplicación contra
`index.json` en el momento en que corre, cada una con su propio `git pull`
al inicio.

Pendiente: aplicar en `jachicanoy@3is.org` el mismo paso 6 corregido (texto
listo en el Project de Cowork, `claude/contexto-migracion-github-2026-10.md`
sección 7) — ninguna de las dos cuentas puede desactivar o editar la tarea
de la otra.

## 2026-11-06 — ALERT_PRIORITY a 4 niveles (WMO-1150/CAP), cierre de eventos vencidos por cronología, heartbeat real

A raíz de que el usuario notó que (a) "Última actualización" podía congelarse días sin que nadie lo notara, y (b) varias alertas activas llevaban semanas/meses sin re-verificarse (ej. un incendio `ONGOING` desde agosto, última confirmación 21 días atrás), y tras corregir una confusión sobre el marco de referencia (no es el Marco de Sendai — es el estándar técnico WMO-1150, que UNDRR promueve vía *Early Warnings for All*/CAP), se implementaron cuatro cambios:

**1. Heartbeat real de "Última actualización".** `rebuild-aggregates.yml` ahora corre también con `schedule` propio (20:17 UTC diario), no solo por push a `Events/**`/`Impacts/**`. `meta.json["lastUpdated"]` ya escribía la hora real de cada corrida; el bug era que el workflow simplemente no corría en días sin eventos nuevos.

**2. `ALERT_PRIORITY` migrado de 3 a 4 niveles** (WMO Guidelines on Multi-hazard Impact-based Forecast and Warning Services, WMO-No. 1150, 2015 — matriz Likelihood × Impact). RED="Take action", ORANGE="Be prepared", **YELLOW (nuevo)="Be aware"**, GREEN="No severe hazard expected". Regla aplicada a los 30 eventos existentes sin inventar datos nuevos (solo con EVENT_STATUS + si el registro ya tenía impacto real reportado en algún campo de impacto):

| EVENT_ID | Peligro | País | Status antes→después | Prioridad antes→después | Motivo |
|---|---|---|---|---|---|
| AMZ-20260801-001 | Wildfire | Bolivia | ONGOING | RED→RED | impacto real, sin cambio |
| AMZ-20260902-001 | Drought | Brasil | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260907-001 | Flood | Perú | OBSERVED | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260908-001 | Drought | Perú | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260909-001 | Wildfire | Brasil | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260910-001 | Earthquake | Perú | OBSERVED→**ENDED** | GREEN→GREEN | sismo puntual sin riesgo secundario, cerrado |
| AMZ-20260910-002 | Wildfire | Brasil | ONGOING | RED→RED | impacto real, sin cambio |
| AMZ-20260911-001 | Drought | Colombia | ONGOING | GREEN→**YELLOW** | activo, sin impacto real reportado |
| AMZ-20260911-002 | Extreme Rain | Ecuador | ONGOING | GREEN→**YELLOW** | activo, sin impacto real reportado |
| AMZ-20260911-003 | Drought | Brasil | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260911-004 | Landslide | Perú | FORECAST→**ENDED** | ORANGE→**GREEN** | ventana de pronóstico vencida, sin impacto confirmado |
| AMZ-20260912-001 | Drought | Venezuela | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260912-002 | Flood | Bolivia | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260914-001 | Landslide | Ecuador | OBSERVED | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260914-002 | Extreme Rain | Venezuela | OBSERVED | GREEN→**YELLOW** | activo, sin impacto real reportado |
| AMZ-20260914-003 | Deforestation | Brasil | OBSERVED | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260914-004 | Earthquake | Ecuador | OBSERVED→**ENDED** | GREEN→GREEN | sismo puntual sin riesgo secundario, cerrado |
| AMZ-20260916-001 | Earthquake | Perú | OBSERVED→**ENDED** | GREEN→GREEN | sismo puntual sin riesgo secundario, cerrado |
| AMZ-20260916-002 | Earthquake | Ecuador | OBSERVED→**ENDED** | GREEN→GREEN | sismo puntual sin riesgo secundario, cerrado |
| AMZ-20260916-003 | Extreme Rain | Colombia | FORECAST→**ENDED** | GREEN→GREEN | ventana de pronóstico vencida, sin impacto confirmado |
| AMZ-20260917-001 | Earthquake | Perú | OBSERVED→**ENDED** | GREEN→GREEN | sismo puntual sin riesgo secundario, cerrado |
| AMZ-20260923-001 | Extreme Rain | Ecuador | FORECAST→**ENDED** | GREEN→GREEN | ventana de pronóstico vencida, sin impacto confirmado |
| AMZ-20260923-002 | Drought | Brasil | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260925-001 | Wildfire | Brasil | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20260929-001 | Earthquake | Perú | OBSERVED→**ENDED** | GREEN→GREEN | sismo puntual sin riesgo secundario, cerrado |
| AMZ-20261001-001 | Wildfire | Brasil | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20261002-001 | Extreme Rain | Ecuador | ONGOING | GREEN→**YELLOW** | activo, sin impacto real reportado |
| AMZ-20261006-001 | Drought | Brasil | ONGOING | ORANGE→ORANGE | impacto real, sin cambio |
| AMZ-20261008-001 | Extreme Heat | Perú | FORECAST→**ENDED** | GREEN→GREEN | ventana de pronóstico vencida, sin impacto confirmado |
| AMZ-20261016-001 | Flood | Ecuador | OBSERVED | GREEN→**YELLOW** | activo, sin impacto real reportado |

Resumen: 10 eventos cerrados a `ENDED` (6 sismos OBSERVED sin riesgo secundario mencionado en su propio registro; 4 FORECAST cuya ventana de días específicos ya pasó hace 40-90+ días sin confirmación posterior), 6 eventos GREEN→YELLOW (activos, sin impacto real reportado), 14 sin cambio de prioridad (RED/ORANGE con impacto real ya confirmado). Los 10 cierres actualizaron LAST_UPDATED_DATE/UPDATE_COUNT (cambio real de estado); los 20 restantes NO se tocaron sin verificación real — quedan en una cola de re-verificación explícita (ver abajo), nunca se cerró nada por adivinar.

**3. Regla de re-verificación por tipo de peligro** (ver prompt completo en `claude/contexto-migracion-github-2026-10.md` sección 7 del Project): sismo → cierre casi inmediato sin necesidad de fuente nueva (salvo riesgo secundario mencionado); pronóstico → 3-7 días de vigencia; lluvia extrema/tormenta severa → 7 días (flag a 14); inundación/deslizamiento → 14 días (flag a 30); incendio forestal → 7-10 días, cruzando con FIRMS; sequía → 30 días; deforestación → 30-60 días (condición estructural, no evento que "termine"). Nunca se cierra sin evidencia — si no se encuentra nada tras buscar, el evento simplemente no se toca esa corrida.

Cola de re-verificación real pendiente tras esta migración (20 eventos activos, ninguno cerrado sin evidencia):

```
 59d  AMZ-20260907-001   Flood         Peru       OBSERVED  ORANGE
 51d  AMZ-20260911-001   Drought       Colombia   ONGOING   YELLOW
 51d  AMZ-20260912-001   Drought       Venezuela  ONGOING   ORANGE
 51d  AMZ-20260914-001   Landslide     Ecuador    OBSERVED  ORANGE
 51d  AMZ-20260914-002   Extreme Rain  Venezuela  OBSERVED  YELLOW
 51d  AMZ-20260914-003   Deforestation Brazil     OBSERVED  ORANGE
 50d  AMZ-20260909-001   Wildfire      Brazil     ONGOING   ORANGE
 49d  AMZ-20260911-002   Extreme Rain  Ecuador    ONGOING   YELLOW
 38d  AMZ-20260912-002   Flood         Bolivia    ONGOING   ORANGE
 35d  AMZ-20260923-002   Drought       Brazil     ONGOING   ORANGE
 34d  AMZ-20261002-001   Extreme Rain  Ecuador    ONGOING   YELLOW
 24d  AMZ-20260911-003   Drought       Brazil     ONGOING   ORANGE
 22d  AMZ-20260908-001   Drought       Peru       ONGOING   ORANGE
 21d  AMZ-20260801-001   Wildfire      Bolivia    ONGOING   RED
 21d  AMZ-20260925-001   Wildfire      Brazil     ONGOING   ORANGE
 21d  AMZ-20261016-001   Flood         Ecuador    OBSERVED  YELLOW
 17d  AMZ-20261006-001   Drought       Brazil     ONGOING   ORANGE
  9d  AMZ-20260910-002   Wildfire      Brazil     ONGOING   RED
  9d  AMZ-20261001-001   Wildfire      Brazil     ONGOING   ORANGE
  8d  AMZ-20260902-001   Drought       Brazil     ONGOING   ORANGE
```
(días desde LAST_UPDATED_DATE al 06-11-2026). La tarea diaria actualizada ya prioriza esta cola antes de buscar eventos nuevos.

**4. Ventana de visualización del visor — confirmado, sin cambio de lógica.** Se mantiene "GitHub = historial completo para siempre, visor = solo lo vigente", filtrando por `EVENT_STATUS` (no-`ENDED` sin límite de días; `ENDED` retenido 90 días, regla ya existente en `rebuild_aggregates.py`). Se descartó un corte fijo de antigüedad (7/30 días): no distingue un peligro que sigue genuinamente activo de uno que simplemente nadie ha vuelto a verificar — ese es justamente el problema que ataca el punto 3.

**Cambios de código:**
- `.github/workflows/rebuild-aggregates.yml`: + `schedule: cron "17 20 * * *"` (heartbeat diario).
- `index.html`: `PRIORITY_COLOR`, traducciones ES/PT/EN y leyenda de colores ahora incluyen YELLOW (antes el fallback los habría pintado como GREEN sin aviso).
- `scripts/build_quarterly_report_data.py`: conteo de prioridades del reporte trimestral incluye YELLOW (antes se perdía silenciosamente del total).
- `Events/*.json` (20 de 30 archivos), `index.json`, `events.json`, `meta.json`, ambos CSV trimestrales: reconstruidos con `scripts/rebuild_aggregates.py` tras la migración.

**Documentación actualizada:** este archivo y `claude/contexto-migracion-github-2026-10.md` (Project de Cowork) — secciones 2 (esquema de prioridad), 3 (tarea diaria), 4 (changelog del visor), 5 (decisiones), 6 (pendientes 0b/0c, cola de re-verificación), 7 (prompt completo actualizado) y 8 (commits).

**Pendiente:** aplicar en `jachicanoy@3is.org` el mismo esquema de 4 colores y la regla de re-verificación (texto ya listo) — esa cuenta sigue con el esquema viejo de 3 colores hasta que alguien lo actualice ahí. Sección 19 de las instrucciones del Project de Cowork (fuera del alcance de las herramientas de esta sesión — solo se puede editar desde la configuración del Project en claude.ai) también necesita el texto de reemplazo con el esquema de 4 colores; texto entregado directamente a Jerson en el chat.

Commits: `4762ca3` (origin) / `743d7b5` (3is).

## 2026-11-06 (tarde) — Rediseño del visor (Observatorio de Riesgos) y regla de "silencio prolongado"

**Contexto:** Jerson notó que el visor seguía mostrando dos incendios en RED (AMZ-20260801-001, Bolivia, sin actualizar desde 16-oct; AMZ-20260910-002, Brasil, sin actualizar desde 28-oct) pese a la migración de la tarde anterior. Investigación: ambos son eventos ONGOING con impacto real reportado (RED es correcto según WMO-1150), pero llevaban 21 y 9 días sin re-verificar porque la corrida diaria de hoy (15:18-18:07 UTC) ocurrió ANTES de que se actualizara el prompt de la tarea (19:46 UTC) con la regla de re-verificación del día anterior.

**Cambios en el visor (`index.html`), ya en vivo en ambos sitios:**
- Panel "Acerca de": niveles de alerta actualizados a 4 (Rojo/Naranja/Amarillo/Verde, WMO-1150) + nota de la cadencia de re-verificación y el principio de ventana de visualización. Commits `0af3f12` (origin) / `29ad325` (3is).
- Logos 3iS/ECHO subidos 10px (`position:relative;top:-10px`). Mismo commit.
- Título del visor cambiado de "Mapa de riesgos" a **"Observatorio de Riesgos — Cuenca Amazónica"** (ES/PT/EN), porque el visor va más allá de un mapa (eventos + pronóstico + análisis climático + alertas IDEAM). Decisión de Jerson tras proponer 4 opciones.
- Pestañas renombradas: Monitor → **Monitor de eventos**; Monitoreo climático → **Análisis climático**. Pronóstico y Alertas IDEAM sin cambio.
- Subtítulo del banner ahora es **dinámico por pestaña** (antes era fijo: "Eventos activos por amenaza y prioridad" siempre). Nueva función `updateSubtitle()` + diccionario `SUBTITLE_KEY`, llamada desde `showTab()` y `applyI18nText()`. Textos por pestaña (ES/PT/EN) en las 3 entradas del diccionario `DICT`. El subtítulo de Pronóstico se ajustó para reflejar las capas reales de Windy (Precipitación, Temperatura, Radar, Tormentas eléctricas) en vez de un texto genérico.
- Commits: `4203a36`→`b3a964b` (origin, tras rebase), `1ea444c` (3is).

**Intento de re-verificación inmediata (sin éxito):** se disparó la tarea diaria manualmente dos veces vía `fire_trigger` para forzar la re-verificación de los dos incendios ya mismo. Ambos intentos devolvieron `no_signed_approval`: un disparo manual de una tarea que `requires_local_device` corre en la nube sin acceso al computador, aunque el computador esté conectado en esa misma sesión de Cowork — la aprobación firmada del dispositivo solo se obtiene en la corrida programada normal o si Jerson la dispara él mismo desde la app de Claude en su equipo. No se reintentó una tercera vez. Quedó para la corrida programada de mañana (09:00 Bogotá).

**Regla nueva — SILENCIO PROLONGADO (paso 5 de la tarea diaria):** Jerson señaló un vacío real en la regla de re-verificación: un evento ONGOING sin fuente oficial que lo confirme NUNCA se cierra (correcto, evita adivinar), pero tampoco queda registro de que se intentó verificarlo — así, un incendio puede quedar indefinidamente en RED, sin actualizar, sin que nada en el dato refleje que su falta de cobertura mediática durante semanas es en sí misma información relevante. Solución (sin verificación manual, sin cerrar a ENDED):
- Si un evento activo lleva más del DOBLE del umbral normal de re-verificación de su peligro sin actualización real, Y la búsqueda del día no encontró nada nuevo, Y `NOTES_ES` todavía NO contiene la frase "SIN RESPALDO TRAS MÚLTIPLES INTENTOS": se agrega esa nota (en ES/PT/EN) documentando la ausencia de fuente pese a búsquedas repetidas, sin cambiar `EVENT_STATUS` ni `ALERT_PRIORITY`. Esta nota SÍ cuenta como actualización legítima (bump de `LAST_UPDATED_DATE`/`UPDATE_COUNT`) porque documenta el estado real de la verificación, no un hecho inventado.
- Si la frase YA está en las notas, no se repite ni se vuelve a tocar el evento esa corrida (evita bucles de auto-actualización que reiniciarían el conteo de "vencido" cada día). El evento sigue envejeciendo según el umbral normal hasta que aparezca una fuente real (confirmando que sigue activo o que terminó).
- Aplicado al prompt de `trig_0136rVLAjj2UwZoUYX4RqDHL` vía `update_trigger` (re-firmado por Jerson). **Pendiente:** aplicar el mismo texto a la tarea de `jachicanoy@3is.org`.

**Documentación actualizada:** este archivo. Pendiente aplicar el mismo resumen a `claude/contexto-migracion-github-2026-10.md` (Project de Cowork) y `claude/bitacora-reuniones-equipo.md`.

## 2026-11-13 — Rediseño del banner: logo de CUENCA, fondo blanco y nuevo nombre "PRISMA Amazonía"

**Pedido de Jerson:** organizar los 3 logos del banner (CUENCA primero a la izquierda, 3iS segundo, ECHO tercero en su versión de letras azules), cambiar el fondo del banner principal de degradado navy/teal/cyan a blanco, mantener el tamaño del banner (sin ensancharlo) y la altura visual de los logos, mover la barra de pestañas para que quede debajo de los logos (no al lado), y renombrar el visor de "Observatorio de Riesgos" a **"PRISMA Amazonía"** ("Plataforma Regional de Inteligencia y Seguimiento Multiamenaza Amazónica").

**Logos nuevos añadidos al repositorio:** `logo_cuenca.png` (logo del proyecto CUENCA, circular + texto), `3is_logo.png` (logo principal de 3iS con eslogan "information · innovation · impact", reemplaza el SVG en blanco embebido que solo se veía sobre fondo oscuro), `echo_logo.png` (reemplazado por la versión horizontal "Financiado por la Unión Europea — Ayuda Humanitaria" con texto en azul, antes era un recorte pequeño en blanco). Los tres se muestran a `height:38px;width:auto` (se preserva la proporción real de cada archivo en vez de forzar un ancho fijo), con una clase `.banner-logo` que se reduce a 26px en pantallas angostas (antes `≤760px`) para que los 3 quepan sin desbordarse.

**Banner (`#banner`):**
- Fondo: de `linear-gradient(135deg, navy, teal-deep, cyan)` a `#ffffff` sólido. Se quitó la textura decorativa de puntos blancos (`.dot-field`), invisible sobre fondo blanco.
- Título y subtítulo: colores invertidos de blanco/aqua-tint a `var(--3is-navy)`/`var(--3is-teal-deep)` para mantener contraste sobre el nuevo fondo claro.
- Botón de idioma (`.toolbar-btn-ghost`) e ícono de globo: mismo cambio, de blancos translúcidos (pensados para fondo oscuro) a borde/relleno/texto en la paleta cian/teal-deep habitual del resto del visor.
- Pestañas inactivas (`.tab-btn`): de `rgba(255,255,255,.14)`/texto blanco a `var(--3is-gray)`/texto navy — la pestaña activa sigue en blanco con texto navy, igual que antes.

**Barra de pestañas — ahora en su propia fila:** antes `.tabs-bar` se posicionaba con un offset calculado (`left:calc(1.5rem + 207px + 1cm)`) para quedar a la derecha de los logos, a la altura del borde inferior del banner. Con 3 logos el ancho de esa fila ya no era constante ni predecible, así que se simplificó: `.tabs-bar` pasa a `left:1.5rem;right:1.5rem` (ocupa todo el ancho, como ya hacía solo en móvil) y el padding inferior extra que antes solo se aplicaba en pantallas `≤760px` (`padding-bottom:3.4rem`) ahora es permanente en `#banner`, dejando sitio para que la fila de pestañas quede siempre debajo de logos+título, nunca a un lado.

**Nombre del visor → "PRISMA Amazonía":** se preguntó a Jerson dónde debía ir el nombre completo del acrónimo ("Plataforma Regional de Inteligencia y Seguimiento Multiamenaza Amazónica"), dado que el subtítulo del banner ya tenía un uso (texto dinámico distinto por pestaña, añadido el 06-11-2026). Decisión: el nombre completo **reemplaza** el subtítulo dinámico — el banner ahora siempre muestra "PRISMA Amazonía" + el nombre completo debajo, igual en las 3 pestañas. El texto que antes variaba por pestaña (qué muestra cada una) se trasladó al panel "Acerca de"/"Sobre"/"About", como primer párrafo nuevo bajo el título "PRISMA Amazonía", en ES/PT/EN. La función `updateSubtitle()` y el diccionario `SUBTITLE_KEY` (que eran por pestaña) se reemplazaron por una sola clave fija `subtitleFull` por idioma; las claves antiguas `subtitleMonitor/Forecast/Climate/Ideam` se conservan en el diccionario (ya no se usan en el banner, mantenidas por si se necesitan más adelante). `<title>` de la pestaña del navegador actualizado a "PRISMA Amazonía". Historial de versiones del panel "Acerca de" actualizado con una entrada para el 06-11-2026 (que no se había registrado ahí) y una para hoy.

**Verificación antes de publicar:** se montó una vista previa local (servidor HTTP + Playwright, sin tocar el repositorio en producción) con los 3 logos reales, en 3 anchos (1400px, 900px, 375px) y en los 3 idiomas, confirmando: los 3 logos se ven completos y sin recortes en escritorio y en móvil, el título/subtítulo cambian de idioma correctamente, el panel "Acerca de" muestra la nueva sección "PRISMA Amazonía" con el contenido por pestaña, y no hay errores de JavaScript nuevos en consola (los únicos 404 son los de datos — `events.json`, etc. — esperados en una vista previa sin servidor real).

**Commits:** pendientes de registrar aquí tras el push (ver `git log` — `index.html`, `logo_cuenca.png`, `3is_logo.png`, `echo_logo.png`).

**Documentación:** este archivo.

## 2026-11-13 (ajustes) — Logos arriba, subtítulo de una línea con iniciales PRISMA resaltadas, pestaña activa en teal

**Feedback de Jerson tras ver el rediseño anterior:** le gustó el resultado, con 4 ajustes puntuales:

1. **Logos más arriba:** antes quedaban a ~71px del borde superior del banner (centrados verticalmente junto al título, que es más alto). Se cambió `.banner-logos-row` para que ya no herede la alineación inferior de la fila (se le dio `align-self:flex-start`, independiente de la altura del bloque de título) y se ajustó el offset vertical para que queden a exactamente **5px** del borde superior del banner, medido con Playwright (`getBoundingClientRect()`), en vez de calcularlo a ojo.
2. **Subtítulo en una sola línea, resaltando las iniciales de PRISMA:** se quitó el `max-width:300px` que forzaba el salto a 2 líneas. El texto completo del acrónimo ya formaba PRISMA con sus iniciales (Plataforma-Regional-de-Inteligencia-y-Seguimiento-Multiamenaza-Amazónica → P-R-I-S-M-A); se resaltan esas 6 letras en negrita y en el color aqua de 3iS (`var(--3is-aqua)`) dentro del subtítulo, vía `innerHTML` en vez de `textContent` (`updateSubtitle()` actualizado).
3. **Traducción al inglés fijada por Jerson:** "Platform for Regional Intelligence and Surveillance of Multi-hazards in the Amazon" (también forma P-R-I-S-M-A). Reemplaza la traducción provisional de la sesión anterior.
4. **Portugués reordenado para que también deletree PRISMA:** la traducción provisional anterior no conservaba el orden de iniciales. Nueva versión: "Plataforma Regional de Inteligência e Supervisão de Multiameaças da Amazônia" (P-R-I-S-M-A). El panel "Acerca de"/"Sobre"/"About" se actualizó con la misma redacción en los 3 idiomas (sin negrita ahí, solo en el banner).
5. **Pestaña activa ahora en teal (`var(--3is-teal)`), no blanco:** con el banner ya blanco, la pestaña seleccionada en blanco se fundía con el fondo. Se cambió el color de fondo de `.tab-btn.active` y el de los dos pseudo-elementos que generan el efecto de "pestaña de carpeta" (`::before`/`::after`, antes `#fff`, ahora `var(--3is-teal)`) para que el recorte curvo siga coincidiendo con el nuevo color de la pestaña activa. Es el mismo verde-azulado que ya se usa para los chips de filtro activos ("Todos", etc.), para mantener consistencia visual.

**Verificación:** vista previa local (Playwright) en 3 idiomas, confirmando medición exacta de 5px para los logos, el subtítulo en una línea con las iniciales resaltadas, y la pestaña activa visible en teal en las 4 pestañas.

**Documentación:** este archivo.
