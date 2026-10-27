#!/usr/bin/env python3
"""
Monitor de la Cuenca Amazonica -- Alertas tempranas de IDEAM (Colombia)

Descarga 3 capas publicas y gratuitas de IDEAM (bart.ideam.gov.co), filtra
cada una a la porcion colombiana de la Cuenca Amazonica, y escribe GeoJSON
listos para el visor. Es 100% determinista -- no llama a ningun modelo de
IA, por lo que no tiene costo de tokens.

IMPORTANTE: estas 3 capas son INDICES DE AMENAZA/ALERTA (no eventos
confirmados). Nunca escriben en Events/ ni en Impacts/, y nunca crean ni
actualizan un Event_ID. Son una capa de alerta temprana aparte, que se
reescribe completa cada corrida (no se acumula historial).

Capas:
  1. Hidrologia  -- shapefile de subzonas hidrograficas con alerta vigente
                    (solo aparecen las que tienen alerta activa hoy).
                    Se filtra a NOMAH == "Amazonas" (el area hidrografica
                    oficial del Amazonas en Colombia).
  2. Deslizamientos -- CSV diario de amenaza por lluvia acumulada, por
                    municipio. Se filtra a los 40 municipios de Amazonas,
                    Caqueta y Putumayo.
  3. Incendios    -- CSV diario de amenaza de incendio de la cobertura
                    vegetal, por municipio. Mismo filtro que deslizamientos.

Para deslizamientos/incendios (que no traen geometria, solo
MUNICIPIO/COD_DANE) se cruza por COD_DANE contra
IDEAM_Alerts/municipios_cuenca_amazonica.geojson -- un archivo de
referencia estatico (limites oficiales de Amazonas/Caqueta/Putumayo,
IGAC/MinAmbiente, generado una sola vez, no se vuelve a descargar aqui).

Salidas (en IDEAM_Alerts/, se sobreescriben completas cada corrida):
  - hidrologia.geojson
  - deslizamientos.geojson
  - incendios.geojson
  - meta.json  (hora de corrida, conteos, URLs fuente)
"""
import csv
import io
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE = "https://bart.ideam.gov.co/ospa/Alertas/modelos"
REPO_ROOT = "."
OUT_DIR = f"{REPO_ROOT}/IDEAM_Alerts"
MUNICIPIOS_REF = f"{OUT_DIR}/municipios_cuenca_amazonica.geojson"

DEPARTAMENTOS_CUENCA = {"AMAZONAS", "CAQUETÁ", "CAQUETA", "PUTUMAYO"}

HEADERS = {"User-Agent": "amazon-basin-monitor/1.0 (+https://github.com/jachicanoy/amazon-basin-monitor)"}


def http_get(url, retries=3, timeout=30):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  [aviso] intento {attempt}/{retries} fallo para {url}: {e}", file=sys.stderr)
    raise RuntimeError(f"No se pudo descargar {url}: {last_err}")


def load_municipios_ref():
    with open(MUNICIPIOS_REF, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_code = {}
    for feat in data["features"]:
        code = feat["properties"]["mpcodigo"]
        by_code[code] = feat
    return by_code


# ---------------------------------------------------------------------------
# 1. Hidrologia (shapefile completo, se reescribe cada dia en el origen)
# ---------------------------------------------------------------------------

def fetch_hidrologia():
    import shapefile  # pyshp

    parts = {}
    for ext in ("shp", "shx", "dbf", "prj"):
        url = f"{BASE}/hidrologia/Alertas_vigentes.{ext}"
        parts[ext] = http_get(url)

    sf = shapefile.Reader(
        shp=io.BytesIO(parts["shp"]),
        shx=io.BytesIO(parts["shx"]),
        dbf=io.BytesIO(parts["dbf"]),
        encoding="latin1",
    )

    features = []
    for sr in sf.shapeRecords():
        rec = sr.record.as_dict()
        nomah = (rec.get("NOMAH") or "").strip()
        if nomah.lower() != "amazonas":
            continue
        geom = sr.shape.__geo_interface__
        props = {
            "NIVEL_A": (rec.get("NIVEL_A") or "").strip(),
            "ALERTA": rec.get("ALERTA"),
            "NOMAH": nomah,
            "NOMZH": (rec.get("NOMZH") or "").strip(),
            "NOMSZH": (rec.get("NOMSZH") or "").strip(),
            "DEP": (rec.get("DEP") or "").strip(),
            "DEP_1": (rec.get("DEP_1") or "").strip(),
            "DEP_2": (rec.get("DEP_2") or "").strip(),
            "FUENTE": "IDEAM - Alertas hidrologicas vigentes",
            "FUENTE_URL": f"{BASE}/hidrologia/",
        }
        features.append({"type": "Feature", "properties": props, "geometry": geom})

    return {"type": "FeatureCollection", "features": features}


# ---------------------------------------------------------------------------
# 2 y 3. Deslizamientos / Incendios (CSV diario por municipio, sin geometria)
# ---------------------------------------------------------------------------

def fetch_municipio_csv(path, municipios_ref, extra_fields):
    raw = http_get(f"{BASE}/{path}")
    text = raw.decode("latin1")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")

    features = []
    sin_geometria = []
    for row in reader:
        depto = (row.get("DEPARTAMENTO") or "").strip().upper()
        if depto not in DEPARTAMENTOS_CUENCA:
            continue
        cod_dane = (row.get("COD_DANE") or "").strip()
        ref = municipios_ref.get(cod_dane)
        if ref is None:
            sin_geometria.append(f"{row.get('MUNICIPIO')} ({cod_dane})")
            continue
        props = {
            "MUNICIPIO": (row.get("MUNICIPIO") or "").strip(),
            "DEPARTAMENTO": depto,
            "COD_DANE": cod_dane,
            "TEXTO_AMENAZA": (row.get("TEXTO_AMENAZA") or "").strip(),
            "FECHA_EJECUCION": (row.get("FECHA_EJECUCION") or "").strip(),
            "FUENTE": "IDEAM",
            "FUENTE_URL": f"{BASE}/{path.rsplit('/', 1)[0]}/",
        }
        for f in extra_fields:
            props[f] = (row.get(f) or "").strip()
        features.append({"type": "Feature", "properties": props, "geometry": ref["geometry"]})

    if sin_geometria:
        print(f"  [aviso] {len(sin_geometria)} municipio(s) sin geometria de referencia: {sin_geometria}", file=sys.stderr)

    return {"type": "FeatureCollection", "features": features}


def fetch_deslizamientos(municipios_ref):
    return fetch_municipio_csv(
        "deslizamientos/ultimo/amenaza_idd.csv",
        municipios_ref,
        extra_fields=["ACUMULADO_TRES", "ACUMULADO_DIEZ", "DIAS_LLUVIA"],
    )


def fetch_incendios(municipios_ref):
    return fetch_municipio_csv(
        "incendios/ultimo/amenaza_icv.csv",
        municipios_ref,
        extra_fields=[],
    )


# ---------------------------------------------------------------------------

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def main():
    municipios_ref = load_municipios_ref()
    print(f"Referencia de municipios cargada: {len(municipios_ref)} municipios")

    print("Descargando hidrologia...")
    hidro = fetch_hidrologia()
    print(f"  -> {len(hidro['features'])} subzona(s) con alerta vigente en el area hidrografica Amazonas")
    write_json(f"{OUT_DIR}/hidrologia.geojson", hidro)

    print("Descargando deslizamientos...")
    desliz = fetch_deslizamientos(municipios_ref)
    print(f"  -> {len(desliz['features'])} municipio(s) en la cuenca")
    write_json(f"{OUT_DIR}/deslizamientos.geojson", desliz)

    print("Descargando incendios...")
    incendios = fetch_incendios(municipios_ref)
    print(f"  -> {len(incendios['features'])} municipio(s) en la cuenca")
    write_json(f"{OUT_DIR}/incendios.geojson", incendios)

    meta = {
        "last_run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "IDEAM (bart.ideam.gov.co/ospa/Alertas/modelos)",
        "note": "Capa de alerta temprana / indice de amenaza. No son eventos confirmados del monitor.",
        "counts": {
            "hidrologia": len(hidro["features"]),
            "deslizamientos": len(desliz["features"]),
            "incendios": len(incendios["features"]),
        },
    }
    write_json(f"{OUT_DIR}/meta.json", meta)
    print("Listo.")


if __name__ == "__main__":
    main()
