# Registro de progresos — Amazon Basin Monitor

Cada mejora funcional del monitor se registra aquí como un "Progreso" numerado,
con su commit marcado `Progreso N:` y una etiqueta git `progreso-N`.

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
