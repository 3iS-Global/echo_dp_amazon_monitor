#!/usr/bin/env python3
"""
Construye el insumo de DATOS (100% determinista, sin LLM ni API externa)
para el Informe Situacional Regional trimestral del Monitor de la Cuenca
Amazonica.

Lee Events/<EVENT_ID>.json e Impacts/<EVENT_ID>.json (las mismas fuentes de
verdad que usa scripts/rebuild_aggregates.py) y escribe un unico JSON con
todo lo que las secciones 1, 2, 4 y 7 de la plantilla "Informe Situacional
Pais" necesitan y que SI se puede derivar de datos ya existentes:

  - Seccion 1: conteos de eventos activos por prioridad (rojo/naranja/verde)
    y total, para el periodo y el alcance regional (los 6 paises del
    proyecto).
  - Seccion 2: tabla de eventos nuevos y actualizados durante el periodo.
  - Seccion 4: cifras de poblacion/impacto reportadas (Impacts/) para esos
    mismos eventos.
  - Seccion 7: fuentes citadas en el periodo con una clasificacion de Nivel
    (1-4) PRELIMINAR por coincidencia de palabras clave contra los nombres
    de organismos que ya aparecen en el proyecto (ver TIER_KEYWORDS). Esta
    clasificacion es una ayuda para el revisor humano, NO una verificacion
    editorial: un PRIMARY_SOURCE real suele venir mezclado como
    "<medio>, citando <organismo oficial>" o "<organismo> (via <medio>)", y
    la regla aqui es simple (si aparece una palabra clave de Nivel 1, se
    asigna Nivel 1, sin distinguir si el organismo fue la fuente directa o
    solo fue citado por el medio). Toda fuente sin ninguna coincidencia
    queda con nivel=null y debe clasificarla el revisor.

Este script NO redacta nada (no genera resumen ejecutivo, relevancia AA por
sector ni recomendaciones) -- esas secciones no son datos existentes, las
redacta por separado el Project de Cowork dedicado a la narrativa AA, a
partir del JSON que este script produce.

Uso:
    python scripts/build_quarterly_report_data.py --quarter 2026-Q4
    python scripts/build_quarterly_report_data.py            # trimestre actual (UTC)

Escribe Reports/<AAAA-QN>/data.json (crea la carpeta si no existe).
"""

import argparse
import glob
import json
import os
import sys
from datetime import date, datetime, timezone

EVENTS_DIR = "Events"
IMPACTS_DIR = "Impacts"
REPORTS_DIR = "Reports"

# Alcance regional confirmado 21-10-2026: 6 paises, excluye Guyana, Surinam
# y Guayana Francesa (ver nota en la memoria/contexto del proyecto).
REGION_COUNTRIES = ["Bolivia", "Brasil", "Colombia", "Ecuador", "Peru", "Venezuela"]
# COUNTRY en Events/*.json puede venir con o sin tilde/variantes de idioma;
# se compara en mayusculas y sin tilde para no excluir eventos por un detalle
# de escritura.
import unicodedata


def _norm(s):
    s = (s or "").strip().upper()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


REGION_COUNTRIES_NORM = {_norm(c) for c in REGION_COUNTRIES}

IMPACT_KEYS = [
    "EVENT_ID", "AS_OF_DATE", "DEATHS", "INJURIES", "AFFECTED_PERSONS",
    "AFFECTED_FAMILIES", "DISPLACED_PERSONS", "EVACUATED_PERSONS", "SCOPE",
    "SOURCE", "SOURCE_URL", "NOTES",
]

# Palabras clave -> Nivel, en orden de prioridad (la primera que coincida en
# el texto de la fuente gana). Tomadas de: (a) las listas de Nivel 1/2 de las
# instrucciones del proyecto, y (b) los nombres de organismos que YA
# aparecen realmente en PRIMARY_SOURCE/SECONDARY_SOURCE de los eventos
# existentes del repo (no son organismos supuestos/inventados).
TIER_KEYWORDS = [
    (1, ["GDACS", "USGS", "WMO", "NOAA", "NASA", "COPERNICUS", "FAO", "OCHA",
         "RELIEFWEB", "IDEAM", "UNGRD", "SGC ", "SERVICO GEOLOGICO",
         "SERVIÇO GEOLÓGICO", "SGB", "INAMHI", "SNGR", "SENAMHI", "INDECI",
         "IGP", "INPE", "INAMEH", "DEFESA CIVIL", "CEMADEN", "INMET",
         "FUNVISIS", "ECU 911"]),
    (2, ["WFP", "IFRC", "CRUZ ROJA", "RED CROSS", "WORLD VISION",
         "SAVE THE CHILDREN", "CARE "]),
    (3, []),  # medios acreditados: se asigna por defecto si no hay match de
              # nivel 1/2 y el texto no esta vacio (ver clasificar_fuente)
]


def clasificar_fuente(texto):
    """Devuelve (nivel|None, motivo) para un PRIMARY_SOURCE/SECONDARY_SOURCE
    real (string libre, a veces compuesto como '<medio>, citando <organismo>').
    nivel=None significa 'no se encontro ninguna palabra clave conocida -
    requiere clasificacion manual del revisor', nunca se inventa un nivel."""
    if not texto or texto == "UNAVAILABLE" or texto == "NOT_REPORTED":
        return None, "sin fuente"
    t = _norm(texto)
    for nivel, keywords in TIER_KEYWORDS:
        for kw in keywords:
            if _norm(kw) in t:
                return nivel, f"coincide con palabra clave de Nivel {nivel}: '{kw.strip()}'"
    # Sin ninguna coincidencia de Nivel 1/2 conocida: se deja sin clasificar
    # en vez de asumir Nivel 3 por defecto, porque varias fuentes nacionales
    # reales (ver el propio listado de PRIMARY_SOURCE del repo) no llevan
    # ningun acronimo reconocible y podrian ser oficiales igual.
    return None, "ninguna palabra clave de Nivel 1/2 conocida encontrada; revisar manualmente"


def parse_quarter_arg(s):
    y, q = s.split("-Q")
    return int(y), int(q)


def quarter_bounds(year, q):
    start_month = (q - 1) * 3 + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2
    if end_month == 12:
        end = date(year, 12, 31)
    else:
        # primer dia del mes siguiente al ultimo mes del trimestre, menos 1 dia
        next_month_first = date(year + (1 if end_month + 1 > 12 else 0), (end_month + 1) if end_month + 1 <= 12 else 1, 1)
        from datetime import timedelta
        end = next_month_first - timedelta(days=1)
    return start, end


def current_quarter_utc():
    today = datetime.now(timezone.utc).date()
    q = (today.month - 1) // 3 + 1
    return today.year, q


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_events():
    events = []
    for p in sorted(glob.glob(os.path.join(EVENTS_DIR, "AMZ-*.json"))):
        events.append(load_json(p))
    return events


def load_impacts():
    impacts = {}
    for p in sorted(glob.glob(os.path.join(IMPACTS_DIR, "AMZ-*.json"))):
        d = load_json(p)
        if set(d.keys()) >= set(IMPACT_KEYS):
            impacts[d["EVENT_ID"]] = d
    return impacts


def in_region(event):
    return _norm(event.get("COUNTRY")) in REGION_COUNTRIES_NORM


def in_period(event, start, end):
    """Seccion 2 de la plantilla pide 'eventos nuevos y actualizados...
    durante el periodo' -> se incluye si FIRST_DETECTED_DATE o
    LAST_UPDATED_DATE cae dentro del rango del trimestre."""
    def _d(key):
        v = event.get(key)
        try:
            return date.fromisoformat(v) if v else None
        except ValueError:
            return None

    fd = _d("FIRST_DETECTED_DATE")
    lu = _d("LAST_UPDATED_DATE")
    return (fd and start <= fd <= end) or (lu and start <= lu <= end)


def build(year, q):
    start, end = quarter_bounds(year, q)
    all_events = load_events()
    impacts = load_impacts()

    scoped = [e for e in all_events if in_region(e) and in_period(e, start, end)]

    counts = {"RED": 0, "ORANGE": 0, "GREEN": 0}
    for e in scoped:
        p = (e.get("ALERT_PRIORITY") or "").upper()
        if p in counts:
            counts[p] += 1
    counts_out = {
        "red": counts["RED"],
        "orange": counts["ORANGE"],
        "green": counts["GREEN"],
        "total": counts["RED"] + counts["ORANGE"] + counts["GREEN"],
    }

    events_rows = []
    sources_rows = []
    impact_rows = []
    for e in sorted(scoped, key=lambda x: x["EVENT_ID"]):
        events_rows.append({
            "eventId": e["EVENT_ID"],
            "country": e["COUNTRY"],
            "adminLevel1": e.get("ADMINISTRATIVE_LEVEL_1"),
            "municipality": e.get("MUNICIPALITY"),
            "hazardType": e.get("HAZARD_TYPE"),
            "hazardSubtype": e.get("HAZARD_SUBTYPE"),
            "eventDate": e.get("EVENT_DATE"),
            "status": e.get("EVENT_STATUS"),
            "priority": e.get("ALERT_PRIORITY"),
            "primarySource": e.get("PRIMARY_SOURCE"),
            "primarySourceUrl": e.get("PRIMARY_SOURCE_URL"),
            "firstDetected": e.get("FIRST_DETECTED_DATE"),
            "lastUpdated": e.get("LAST_UPDATED_DATE"),
            "updateCount": e.get("UPDATE_COUNT"),
        })

        for role, name_key, url_key, verif in (
            ("primary", "PRIMARY_SOURCE", "PRIMARY_SOURCE_URL", e.get("VERIFICATION_STATUS")),
            ("secondary", "SECONDARY_SOURCE", "SECONDARY_SOURCE_URL", e.get("VERIFICATION_STATUS")),
        ):
            name = e.get(name_key)
            if not name or name in ("UNAVAILABLE", "NOT_REPORTED"):
                continue
            nivel, motivo = clasificar_fuente(name)
            sources_rows.append({
                "eventId": e["EVENT_ID"],
                "role": role,
                "source": name,
                "url": e.get(url_key),
                "verificationStatus": verif,
                "tierPreliminar": nivel,
                "tierMotivo": motivo,
            })

        imp = impacts.get(e["EVENT_ID"])
        if imp:
            impact_rows.append({
                "eventId": e["EVENT_ID"],
                "asOf": imp["AS_OF_DATE"],
                "deaths": imp["DEATHS"],
                "injuries": imp["INJURIES"],
                "affectedPersons": imp["AFFECTED_PERSONS"],
                "affectedFamilies": imp["AFFECTED_FAMILIES"],
                "displaced": imp["DISPLACED_PERSONS"],
                "evacuated": imp["EVACUATED_PERSONS"],
                "scope": imp["SCOPE"],
                "source": imp["SOURCE"],
                "sourceUrl": imp["SOURCE_URL"],
                "notes": imp.get("NOTES"),
            })

    out = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period": {
            "year": year,
            "quarter": q,
            "label": f"{year}-Q{q}",
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "scopeCountries": REGION_COUNTRIES,
        "counts": counts_out,
        "events": events_rows,
        "impact": impact_rows,
        "sources": sources_rows,
        "notaMetodologica": (
            "Este archivo es 100% derivado de Events/ e Impacts/, sin ningun "
            "paso de LLM. El campo tierPreliminar de 'sources' es una ayuda "
            "heuristica por palabra clave para el revisor humano (ver "
            "docstring del script), no una clasificacion editorial definitiva."
        ),
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarter", help="Formato AAAA-QN, ej. 2026-Q4. Por defecto: trimestre actual (UTC).")
    ap.add_argument("--out", help="Ruta de salida. Por defecto: Reports/<AAAA-QN>/data.json")
    args = ap.parse_args()

    if args.quarter:
        year, q = parse_quarter_arg(args.quarter)
    else:
        year, q = current_quarter_utc()

    data = build(year, q)
    out_path = args.out or os.path.join(REPORTS_DIR, data["period"]["label"], "data.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    print(f"OK: {out_path}")
    print(f"  Periodo: {data['period']['label']} ({data['period']['start']} a {data['period']['end']})")
    print(f"  Eventos en el periodo (region, 6 paises): {len(data['events'])}")
    print(f"  Conteos: rojo={data['counts']['red']} naranja={data['counts']['orange']} verde={data['counts']['green']} total={data['counts']['total']}")
    print(f"  Con cifras de impacto reportadas: {len(data['impact'])}")
    sin_clasificar = sum(1 for s in data["sources"] if s["tierPreliminar"] is None)
    print(f"  Fuentes citadas: {len(data['sources'])} ({sin_clasificar} sin clasificacion preliminar de Nivel)")


if __name__ == "__main__":
    main()
