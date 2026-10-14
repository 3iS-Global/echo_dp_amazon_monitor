#!/usr/bin/env python3
"""
fetch_and_publish.py

Corre DENTRO de GitHub Actions (no en Cowork/Claude). Este script es el unico
punto del sistema que escribe en el repositorio de GitHub, y por eso nunca
pasa por la restriccion de acceso a la API de GitHub desde Cowork.

Hace dos cosas, cada una independiente (si una falla, las otras igual se intentan):

  1) FIRMS: llama directamente a la API de NASA FIRMS, agrega/recorta la
     ventana movil de RETENTION_DAYS dias, y actualiza firms_hotspots.json.
     Esta ventana es solo para lo que se muestra en el mapa publico (lo
     operacionalmente accionable); el historico completo de focos de calor
     ya lo mantiene la propia NASA en su herramienta de descarga
     (https://firms.modaps.eosdis.nasa.gov/download/), asi que este script
     no intenta duplicar ese archivo. Los puntos se recortan ademas a la
     forma real de la cuenca (amazon_basin.geojson, capa oficial
     Panamazonia) via load_basin_polygon()/filter_to_basin(): el rectangulo
     AREA_COORDINATES solo se usa para la llamada a la API de FIRMS (que
     exige un rectangulo), nunca como filtro final.

  2) (Eliminado) Ya no se sincroniza nada desde SharePoint: events.json,
     meta.json e index.json los reconstruye rebuild-aggregates.yml a partir
     de Events/<EVENT_ID>.json, que la tarea diaria de Cowork sube por git.

  3) (Retirado 14-10-2026, Progreso 3) Este script ya NO calcula la capa
     ENSO/SST. Antes calculaba la anomalia de temperatura superficial del
     mar via Google Earth Engine y publicaba sst_layer.json; ahora index.html
     dibuja directamente una tesela publica y oficial de NASA GIBS (producto
     GHRSST L4 MUR), con una URL fija que ya resuelve sola a la ultima fecha
     disponible. El codigo anterior se conserva, sin usarse, en
     legacy/enso_gee_pipeline/ (ver su README.md) como registro de lo hecho.

Variables de entorno requeridas (se configuran como GitHub Actions secrets):
  FIRMS_MAP_KEY              -> la MAP_KEY privada de FIRMS

No imprime nunca el contenido completo de estos archivos en los logs -
solo conteos y mensajes de error, para mantener los logs de Actions livianos
y no filtrar datos por accidente.
"""

import csv
import io
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    # shapely -- para recortar los puntos FIRMS a la forma real de la cuenca
    # amazonica (amazon_basin.geojson) en vez de solo al rectangulo
    # AREA_COORDINATES. Opcional: si no esta instalado, se usa solo el
    # rectangulo, igual que antes.
    from shapely.geometry import Point, shape
    from shapely.ops import unary_union
except ImportError:
    Point = None
    shape = None
    unary_union = None

# Algunos runners de GitHub Actions no tienen ruta de red IPv6 utilizable hacia
# ciertos hosts externos (por ejemplo la NASA), aunque el host sí resuelva una
# direccion IPv6 por DNS. Eso produce "Network is unreachable" incluso cuando
# IPv4 funciona perfectamente. Forzamos aqui que TODAS las conexiones salientes
# de este script usen solo IPv4, para no depender de que el runner tenga IPv6.
_original_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    results = _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    if results:
        return results
    # si por lo que sea no hay resultados IPv4, no lo escondemos: se deja que
    # falle con el error real en vez de devolver una lista vacia silenciosa.
    return _original_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_only_getaddrinfo

# --- Configuracion (ver seccion 9 de las instrucciones originales del proyecto) ---
AREA_COORDINATES = "-79,-21,-40,11"  # min_lon,min_lat,max_lon,max_lat (Pan-Amazonia)
# AREA_COORDINATES es solo el rectangulo que se le pasa a la API de FIRMS
# (FIRMS exige un rectangulo, no acepta poligonos). La forma real de la
# cuenca -- la "zona de verdad" del proyecto -- vive en amazon_basin.geojson
# (capa oficial Panamazonia, incluye el estuario) y se usa mas abajo para
# recortar cualquier punto que caiga dentro del rectangulo pero fuera de la
# cuenca real. Ver AMAZON_BASIN_GEOJSON_PATH y load_basin_polygon().
SOURCES = ["VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
DAY_RANGE = 1
RETENTION_DAYS = 7  # ventana del mapa publico; el historico completo vive en NASA FIRMS
GRID_SIZE_DEG = 0.25
GRID_AGGREGATION_TRIGGER = 1500  # solo agrega si un solo dia supera este umbral

REPO_ROOT = os.environ.get("GITHUB_WORKSPACE", ".")
FIRMS_JSON_PATH = os.path.join(REPO_ROOT, "firms_hotspots.json")
# Cuenca oficial SIN Guyana, Surinam ni Guayana Francesa (fuera del proyecto).
# El original completo sigue en amazon_basin.geojson como referencia.
AMAZON_BASIN_GEOJSON_PATH = os.path.join(REPO_ROOT, "amazon_basin_project.geojson")

# Capa SST/ENSO: retirada de este script el 14-10-2026 (Progreso 3). Ver
# legacy/enso_gee_pipeline/ para la configuracion anterior (ROI, paleta,
# climatologia de Earth Engine).


CONFIDENCE_CODES = {"l": "low", "n": "nominal", "h": "high"}


def satellite_name(source: str) -> str:
    return "NOAA-20" if "NOAA20" in source else "NOAA-21"


def fetch_firms_points(map_key: str):
    """Llama la API de FIRMS para cada satelite y devuelve la lista de puntos crudos."""
    points = []
    for source in SOURCES:
        url = (
            f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
            f"{map_key}/{source}/{AREA_COORDINATES}/{DAY_RANGE}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "amazon-basin-monitor/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8", errors="replace")

        if not text.strip():
            continue

        reader = csv.DictReader(io.StringIO(text))
        sat = satellite_name(source)
        for row in reader:
            try:
                # VIIRS entrega la confianza como l/n/h; se normaliza a low/nominal/high
                conf_raw = (row.get("confidence") or "nominal").strip().lower()
                point = {
                    "lat": round(float(row["latitude"]), 4),
                    "lon": round(float(row["longitude"]), 4),
                    "date": row.get("acq_date", "").strip(),
                    # hora de adquisicion HHMM (UTC): el mapa la usa para la ventana de 24 h
                    "time": (row.get("acq_time") or "").strip().zfill(4) if (row.get("acq_time") or "").strip() else "",
                    "confidence": CONFIDENCE_CODES.get(conf_raw, conf_raw),
                    "satellite": sat,
                }
                # FRP = potencia radiativa del fuego (MW): la medida de intensidad
                # que usa el mapa para el tamano y el tono de gris de cada punto.
                frp_raw = (row.get("frp") or "").strip()
                if frp_raw:
                    point["frp"] = round(float(frp_raw), 1)
                points.append(point)
            except (KeyError, ValueError):
                # fila con formato inesperado -> se ignora, no se inventa nada
                continue
    return points


def aggregate_if_needed(points):
    """Si un solo dia trae mas puntos que el umbral, agrega por celda de rejilla."""
    if len(points) <= GRID_AGGREGATION_TRIGGER:
        return points

    cells = {}
    for p in points:
        key = (
            round(p["lat"] / GRID_SIZE_DEG) * GRID_SIZE_DEG,
            round(p["lon"] / GRID_SIZE_DEG) * GRID_SIZE_DEG,
            p["date"],
            p["satellite"],
        )
        cells.setdefault(key, []).append(p)

    aggregated = []
    confidence_rank = {"low": 0, "l": 0, "nominal": 1, "n": 1, "high": 2, "h": 2}
    for (lat, lon, date, sat), group in cells.items():
        best_confidence = max(group, key=lambda g: confidence_rank.get(g["confidence"], 0))["confidence"]
        cell = {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "date": date,
            "confidence": best_confidence,
            "satellite": sat,
            "count": len(group),
        }
        times = [g["time"] for g in group if g.get("time")]
        if times:
            cell["time"] = max(times)  # la observacion mas reciente de la celda
        # FRP total y maxima de la celda: el mapa usa frp_sum como intensidad
        frps = [g["frp"] for g in group if g.get("frp") is not None]
        if frps:
            cell["frp_sum"] = round(sum(frps), 1)
            cell["frp_max"] = round(max(frps), 1)
        aggregated.append(cell)
    return aggregated


def load_json_array(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def trim_to_window(points, days=RETENTION_DAYS):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    return [p for p in points if p.get("date", "") >= cutoff]


def dedupe(points):
    """Evita duplicados exactos si el Action corre mas de una vez en el mismo dia."""
    seen = set()
    unique = []
    for p in points:
        key = (p["lat"], p["lon"], p["date"], p["satellite"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


_basin_geometry_cache = {"loaded": False, "geometry": None}


def load_basin_polygon():
    """Carga la forma real de la cuenca amazonica (amazon_basin.geojson) como
    geometria de shapely, para recortar puntos que caigan dentro del
    rectangulo AREA_COORDINATES pero fuera de la cuenca real (por ejemplo, el
    Caribe, los Andes o el Pacifico, que entran en el rectangulo pero no en
    la cuenca).

    Si shapely no esta instalado o el archivo no existe/esta corrupto, se
    devuelve None y quien llame sigue usando solo el rectangulo -- igual que
    antes de este cambio. Nunca se bloquea FIRMS por esto; se hace lo mismo
    que con Earth Engine: si algo opcional falla, se avisa y se
    sigue con lo que si funciona.
    """
    if _basin_geometry_cache["loaded"]:
        return _basin_geometry_cache["geometry"]
    _basin_geometry_cache["loaded"] = True

    if shape is None:
        print("FIRMS: shapely no esta instalado - se usa solo el rectangulo AREA_COORDINATES, sin recorte a la forma real de la cuenca")
        return None
    if not os.path.exists(AMAZON_BASIN_GEOJSON_PATH):
        print("FIRMS: no se encontro amazon_basin.geojson - se usa solo el rectangulo AREA_COORDINATES, sin recorte a la forma real de la cuenca")
        return None

    try:
        with open(AMAZON_BASIN_GEOJSON_PATH, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
        geometries = [shape(feat["geometry"]) for feat in geojson_data["features"]]
        geometry = geometries[0] if len(geometries) == 1 else unary_union(geometries)
        _basin_geometry_cache["geometry"] = geometry
        return geometry
    except Exception as e:
        print(f"FIRMS: no se pudo leer amazon_basin.geojson ({e}) - se usa solo el rectangulo AREA_COORDINATES")
        return None


def filter_to_basin(points):
    """Descarta los puntos [lat, lon] que caigan fuera de la forma real de la
    cuenca. Si no hay geometria cargada (shapely ausente o archivo faltante),
    devuelve los puntos sin cambios -- el rectangulo AREA_COORDINATES sigue
    siendo el unico filtro, tal como funcionaba antes."""
    basin_geometry = load_basin_polygon()
    if basin_geometry is None:
        return points
    kept = [p for p in points if basin_geometry.contains(Point(p["lon"], p["lat"]))]
    removed = len(points) - len(kept)
    if removed:
        print(f"FIRMS: {removed} puntos descartados por caer fuera de la forma real de la cuenca (dentro del rectangulo, pero fuera del limite oficial)")
    return kept


def update_firms():
    map_key = os.environ.get("FIRMS_MAP_KEY", "")
    if not map_key:
        print("FIRMS: BLOQUEADO - falta la variable de entorno FIRMS_MAP_KEY")
        return

    try:
        new_points = fetch_firms_points(map_key)
    except urllib.error.URLError as e:
        print(f"FIRMS: BLOQUEADO - error de red al llamar la API ({e})")
        return
    except Exception as e:
        print(f"FIRMS: BLOQUEADO - {e}")
        return

    # Se recortan los puntos crudos a la forma real de la cuenca ANTES de
    # agregarlos por rejilla, para que ninguna celda sume focos de fuera.
    new_points = aggregate_if_needed(filter_to_basin(new_points))
    existing = load_json_array(FIRMS_JSON_PATH)
    # Los puntos nuevos van primero: si el Action corre dos veces el mismo dia,
    # dedupe() conserva la version mas reciente (con FRP) y no la anterior.
    combined = dedupe(trim_to_window(new_points + existing))
    combined = filter_to_basin(combined)

    with open(FIRMS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, separators=(",", ":"))

    print(f"FIRMS: {len(new_points)} puntos nuevos de hoy, {len(combined)} puntos totales en la ventana de {RETENTION_DAYS} dias (ya recortados a la forma real de la cuenca)")


def main():
    update_firms()


if __name__ == "__main__":
    sys.exit(main())
