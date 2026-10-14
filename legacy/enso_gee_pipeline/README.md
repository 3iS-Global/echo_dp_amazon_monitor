# Pipeline anterior de la capa ENSO/SST (vía Google Earth Engine) — archivado el 14-10-2026

Esta carpeta conserva, sin usarse, el código que calculaba la capa "Anomalía SST (ENSO)"
diariamente con Google Earth Engine (NOAA OISST contra una climatología 1991-2020
precalculada). Se reemplazó por una tesela pública y oficial de **NASA GIBS** (producto
GHRSST L4 MUR, la misma imagen que muestra NASA Worldview), con URL fija que siempre
resuelve a la última fecha disponible — sin necesidad de ningún cálculo ni publicación
diaria propia. Ver Progreso 3 en `PROGRESOS.md` y en el panel "i" del visor.

Se conserva este código (en vez de borrarlo) solo como registro de lo que se hizo, a
pedido explícito de Jerson, no porque siga en uso.

## Archivos

- `setup_enso_sst_climatology.py` — script de una sola corrida que generó el Earth
  Engine Asset de climatología diaria 1991-2020 (`projects/ee-jersoncatalyst/assets/enso_sst_climatology_1991_2020`).
- `fetch_and_publish_with_gee_sst.py` — copia completa de `scripts/fetch_and_publish.py`
  tal como estaba el 14-10-2026, con la función `update_sst_layer()` y la inicialización
  de Earth Engine (`_gee_initialize()`) todavía incluidas. El `scripts/fetch_and_publish.py`
  vigente ya no tiene esta parte — solo conserva la actualización de FIRMS.
- `sst_layer_last_generated.json` — la última salida real que generó este pipeline
  (imagen del 2026-10-10), tal como quedó en la raíz del repo antes del cambio.

## Qué se dejó de necesitar

- El Earth Engine Asset `projects/ee-jersoncatalyst/assets/enso_sst_climatology_1991_2020`
  (no se borró del lado de Google Cloud/Earth Engine; solo dejó de consultarse).
- Los secrets de GitHub Actions `GEE_SERVICE_ACCOUNT_EMAIL` y `GEE_SERVICE_ACCOUNT_KEY`
  (se dejaron configurados en el repositorio por si se necesitan de nuevo; `publish.yml`
  ya no los usa).
- El paquete `earthengine-api` en el workflow `publish.yml` (ya no se instala).
