#!/usr/bin/env python3
"""
scripts/fetch_gdacs_candidates.py

Candidatos de GDACS para el monitor de desastres de la cuenca amazonica.
100% determinista, sin costo de tokens: corre en GitHub Actions (ver
.github/workflows/fetch-gdacs.yml), consulta la API publica y gratuita de
GDACS (gdacs.org, sin API key) y escribe GDACS_Candidates/candidates.json.

DECISION DE ALCANCE (confirmada por el usuario, 22-10-2026):
- Objetivo: detectar CIFRAS DE AFECTACION reportadas por GDACS (indicadores
  tipo Sendai) para que un humano las use para enriquecer Events/ e
  Impacts/, o para detectar un evento nuevo que todavia no esta
  registrado. Un evento de GDACS sin ninguna cifra de afectacion NO se
  incluye -- no aporta nada que el monitor no tenga ya, y genera ruido.
- Incendios forestales (WF) se EXCLUYEN por completo: ya los cubre la capa
  de focos FIRMS del propio monitor (firms_hotspots.json); repetirlos como
  "evento" no aporta valor nuevo.
- Ciclones tropicales (TC) se EXCLUYEN: no hacen landfall en la cuenca.
- Tipos consultados: FL (inundacion), DR (sequia), VO (volcan). EQ (sismo)
  se probo y se descarto (22-10-2026): GDACS no publica indicadores Sendai
  estructurados para sismos en esta API (solo texto libre de magnitud), y
  como geteventlist/SEARCH no filtra por pais en el servidor, cubrir
  sismos exhaustivamente obliga a paginar el listado MUNDIAL de sismos
  (cientos por semana) solo para, al final, no encontrar ninguna cifra de
  afectacion util -- costoso y sin beneficio real dado el criterio de
  "solo eventos con cifra de afectacion" de mas abajo.
- NUNCA escribe en Events/ ni en Impacts/, nunca hace commit de esos
  archivos, nunca inventa coordenadas ni cifras. Solo escribe
  GDACS_Candidates/candidates.json como lista de candidatos VIGENTE (se
  sobrescribe completa cada corrida, sin acumular historial), para
  revision y promocion manual.
- Verificacion geografica: EQ/VO tienen coordenadas puntuales reales
  (epicentro/crater) y se verifican contra amazon_basin_project.geojson.
  FL/DR agregan muchas localidades bajo un solo evento con una geometria
  de pais poco fiable (centroide), asi que cada reporte individual
  ('sendai') se clasifica por el NOMBRE de su departamento/estado contra
  BASIN_ADMIN1 / KNOWN_OUTSIDE_ADMIN1 (mas abajo). Si el nombre no se
  reconoce con confianza, GEO_MATCH=UNCERTAIN y se incluye igual para que
  un humano decida -- nunca se asume inclusion con duda (regla del
  proyecto, sección 14).
"""

import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

try:
    from shapely.geometry import Point, shape
    from shapely.ops import unary_union
except ImportError:
    shape = None
    Point = None
    unary_union = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AMAZON_BASIN_GEOJSON_PATH = os.path.join(REPO_ROOT, "amazon_basin_project.geojson")
EVENTS_DIR = os.path.join(REPO_ROOT, "Events")
OUTPUT_DIR = os.path.join(REPO_ROOT, "GDACS_Candidates")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "candidates.json")

GDACS_EVENTLIST_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GDACS_EVENTDATA_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventdata"
GDACS_REPORT_URL = "https://www.gdacs.org/report.aspx"

EVENT_TYPES = ["FL", "DR", "VO"]  # EQ, WF y TC excluidos a proposito (ver docstring); TS no es un eventtype valido en GDACS
LOOKBACK_DAYS = 90
PAGE_SIZE = 100
MAX_PAGES_PER_TYPE = 8
MATCH_DATE_WINDOW_DAYS = 21
MATCH_DISTANCE_KM = 150
REQUEST_DELAY_SECONDS = 0.4  # pausa entre llamadas a la API publica de GDACS, por cortesia/estabilidad

BASIN_ISO3 = {"BOL", "BRA", "COL", "ECU", "PER", "VEN"}
ISO3_TO_PROJECT_COUNTRY = {
    "BOL": "Bolivia", "BRA": "Brazil", "COL": "Colombia",
    "ECU": "Ecuador", "PER": "Peru", "VEN": "Venezuela",
}
GDACS_TO_HAZARD_KEYWORDS = {
    "FL": ["flood", "inundacion", "inundación"],
    "DR": ["drought", "sequia", "sequía"],
    "VO": ["volcan", "volcano", "eruption", "erupcion", "erupción"],
}

# BASIN_ADMIN1: departamentos/estados/provincias (en texto, como suelen
# aparecer en los campos 'region'/'description' de GDACS) que caen, en
# todo o en parte, dentro de la cuenca amazonica del proyecto. Lista de
# apoyo para el emparejamiento por NOMBRE cuando GDACS no da coordenadas
# puntuales fiables -- no sustituye la verificacion geografica real del
# revisor humano (reglas 11-14 del proyecto).
BASIN_ADMIN1 = {
    "BRA": {"acre", "amapa", "amazonas", "para", "rondonia", "roraima",
            "maranhao", "mato grosso", "tocantins"},
    "PER": {"loreto", "ucayali", "madre de dios", "san martin", "amazonas",
            "huanuco", "pasco", "junin", "cusco", "cuzco"},
    "COL": {"amazonas", "caqueta", "guainia", "guaviare", "putumayo",
            "vaupes", "meta", "cauca", "narino"},
    "BOL": {"pando", "beni", "la paz", "cochabamba", "santa cruz"},
    "ECU": {"napo", "orellana", "pastaza", "morona santiago", "sucumbios",
            "zamora chinchipe"},
    "VEN": {"amazonas", "bolivar", "delta amacuro"},
}
# Regiones claramente FUERA de la cuenca, para no marcar UNCERTAIN lo que
# ya se puede descartar con confianza (lista no exhaustiva).
KNOWN_OUTSIDE_ADMIN1 = {
    "BRA": {"rio de janeiro", "sao paulo", "santa catarina",
            "rio grande do sul", "parana", "minas gerais",
            "espirito santo", "bahia", "pernambuco", "ceara",
            "distrito federal", "goias", "rio grande do norte", "paraiba",
            "alagoas", "sergipe", "piaui",
            # "mato grosso do sul" se verifica ANTES que "mato grosso" (ver
            # classify_admin1): sin esto, "do sul" quedaba enmascarado por
            # el match parcial de "mato grosso" (que si es amazonico) y el
            # estado -- no amazonico, es Pantanal/Cerrado -- salia mal
            # clasificado como LIKELY_INSIDE. Confirmado con datos reales de
            # GDACS el 22-10-2026 (eventos FL 1104216 / 1104148).
            "mato grosso do sul"},
    "PER": {"lima", "arequipa", "tacna", "moquegua", "ica", "piura",
            "lambayeque", "la libertad", "ancash", "tumbes", "callao"},
    "COL": {"bogota", "antioquia", "valle del cauca", "atlantico",
            "cundinamarca", "santander", "norte de santander", "boyaca",
            "cesar", "magdalena", "la guajira", "cordoba", "risaralda",
            "quindio", "caldas", "tolima", "huila", "sucre"},
    "BOL": {"tarija", "potosi", "oruro", "chuquisaca"},
    "ECU": {"guayas", "pichincha", "manabi", "azuay", "el oro",
            "los rios", "esmeraldas", "loja", "imbabura", "carchi",
            "cotopaxi", "tungurahua", "bolivar", "canar", "santa elena"},
    "VEN": {"distrito capital", "miranda", "zulia", "carabobo", "aragua",
            "lara", "tachira", "merida", "anzoategui", "sucre", "falcon",
            "trujillo", "yaracuy", "cojedes", "portuguesa", "guarico",
            "vargas", "nueva esparta", "monagas"},
}

_basin_geometry_cache = {"loaded": False, "geometry": None}


def log(msg):
    print(f"[fetch_gdacs_candidates] {msg}", file=sys.stderr)


def strip_accents(text):
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def norm(text):
    return strip_accents(text).lower().strip()


def http_get_json(url, retries=3, timeout=25):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            time.sleep(REQUEST_DELAY_SECONDS)
            req = urllib.request.Request(url, headers={"User-Agent": "amazon-basin-monitor/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as e:  # noqa: BLE001 - nunca tumbar la corrida por un fallo de red puntual
            last_err = e
            time.sleep(1.5 * attempt)
    log(f"ADVERTENCIA: fallo GET {url} tras {retries} intentos ({last_err})")
    return None


def load_basin_polygon():
    if _basin_geometry_cache["loaded"]:
        return _basin_geometry_cache["geometry"]
    _basin_geometry_cache["loaded"] = True
    if shape is None:
        log("shapely no esta instalado - se omite la verificacion geografica puntual (EQ/VO)")
        return None
    if not os.path.exists(AMAZON_BASIN_GEOJSON_PATH):
        log("no se encontro amazon_basin_project.geojson - se omite la verificacion geografica puntual")
        return None
    try:
        with open(AMAZON_BASIN_GEOJSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        geoms = [shape(feat["geometry"]) for feat in data["features"]]
        geometry = geoms[0] if len(geoms) == 1 else unary_union(geoms)
        _basin_geometry_cache["geometry"] = geometry
        return geometry
    except Exception as e:  # noqa: BLE001
        log(f"no se pudo leer amazon_basin_project.geojson ({e})")
        return None


def point_in_basin(lon, lat):
    """True/False si hay geometria cargada; None si no se pudo verificar."""
    geom = load_basin_polygon()
    if geom is None or lon is None or lat is None:
        return None
    try:
        return geom.contains(Point(lon, lat))
    except Exception:  # noqa: BLE001
        return None


def haversine_km(lon1, lat1, lon2, lat2):
    from math import radians, sin, cos, sqrt, atan2
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return r * 2 * atan2(sqrt(a), sqrt(1 - a))


def classify_admin1(iso3, *texts):
    """Clasifica un conjunto de fragmentos de texto (region/description de
    un reporte 'sendai') como LIKELY_INSIDE / LIKELY_OUTSIDE / UNCERTAIN
    respecto a la cuenca amazonica, por coincidencia de nombre de
    departamento/estado."""
    basin_names = BASIN_ADMIN1.get(iso3, set())
    outside_names = KNOWN_OUTSIDE_ADMIN1.get(iso3, set())
    found_inside = False
    found_outside = False
    for raw in texts:
        if not raw:
            continue
        # separa por comas y tambien evalua el texto completo
        fragments = [norm(x) for x in re.split(r"[,/]", raw)] + [norm(raw)]
        for frag in fragments:
            frag = frag.strip()
            if not frag:
                continue
            for name in basin_names:
                if name in frag or frag in name:
                    found_inside = True
            for name in outside_names:
                if name in frag or frag in name:
                    found_outside = True
    if found_inside and not found_outside:
        return "LIKELY_INSIDE"
    if found_outside and not found_inside:
        return "LIKELY_OUTSIDE"
    if found_inside and found_outside:
        return "UNCERTAIN"  # el mismo texto toco un nombre de cada lista: mejor no asumir
    return "UNCERTAIN"


def guess_impact_field(sendainame, description):
    text = norm(f"{sendainame} {description}")
    if any(k in text for k in ["death", "fatal", "muert", "falleci"]):
        return "DEATHS"
    if any(k in text for k in ["injur", "herid"]):
        return "INJURIES"
    if "evacuat" in text or "evacuad" in text:
        return "EVACUATED_PERSONS"
    if "displac" in text or "desplaz" in text:
        return "DISPLACED_PERSONS"
    if "famil" in text or "household" in text or "hogar" in text:
        return "AFFECTED_FAMILIES"
    if "affected" in text or "afectad" in text:
        return "AFFECTED_PERSONS"
    return "NOTES_ONLY"  # p.ej. viviendas/infraestructura danada: no hay campo numerico en Impacts/


def fetch_eventlist_for_type(evtype, fromdate, todate):
    """Pagina geteventlist/SEARCH para un tipo y filtra a paises de la cuenca."""
    hits = []
    page = 1
    while page <= MAX_PAGES_PER_TYPE:
        params = {
            "eventlist": evtype,
            "alertlevel": "red;orange;green",
            "fromdate": fromdate,
            "todate": todate,
            "pagesize": PAGE_SIZE,
            "pagenumber": page,
        }
        qs = urllib.parse.urlencode(params, safe=";")
        data = http_get_json(f"{GDACS_EVENTLIST_URL}?{qs}")
        if not data:
            break
        feats = data.get("features", [])
        if not feats:
            break
        for f in feats:
            p = f.get("properties", {})
            iso3s = {p.get("iso3", "")} | {c.get("iso3", "") for c in p.get("affectedcountries", [])}
            iso3s.discard("")
            basin_iso3s = iso3s & BASIN_ISO3
            if basin_iso3s:
                hits.append((f, sorted(basin_iso3s)))
        if len(feats) < PAGE_SIZE:
            break
        page += 1
    return hits


def fetch_eventdata(evtype, eventid):
    return http_get_json(f"{GDACS_EVENTDATA_URL}?eventtype={evtype}&eventid={eventid}")


def load_existing_events():
    events = []
    if not os.path.isdir(EVENTS_DIR):
        return events
    for name in sorted(os.listdir(EVENTS_DIR)):
        if not name.startswith("AMZ-") or not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(EVENTS_DIR, name), "r", encoding="utf-8") as f:
                events.append(json.load(f))
        except Exception as e:  # noqa: BLE001
            log(f"ADVERTENCIA: no se pudo leer {name} ({e})")
    return events


def event_date_range(ev):
    def parse(d):
        if not d or d in ("NOT_REPORTED", "UNAVAILABLE", ""):
            return None
        try:
            return datetime.strptime(d[:10], "%Y-%m-%d")
        except ValueError:
            return None

    start = parse(ev.get("EVENT_START_DATE")) or parse(ev.get("EVENT_DATE")) or parse(ev.get("FIRST_DETECTED_DATE"))
    end = parse(ev.get("EVENT_END_DATE"))
    if end is None:
        # evento abierto/en curso: se extiende hasta la ultima actualizacion conocida
        end = parse(ev.get("LAST_UPDATED_DATE")) or start
    return start, end


def dates_overlap(a_start, a_end, b_start, b_end, slack_days):
    if a_start is None or b_start is None:
        return False
    slack = timedelta(days=slack_days)
    a_end = a_end or a_start
    b_end = b_end or b_start
    return (a_start - slack) <= (b_end + slack) and (b_start - slack) <= (a_end + slack)


def find_possible_matches(iso3, gdacs_type, onset_dt, admin1_text, lon, lat, existing_events):
    country = ISO3_TO_PROJECT_COUNTRY.get(iso3, "")
    hazard_keywords = GDACS_TO_HAZARD_KEYWORDS.get(gdacs_type, [])
    admin1_norm = norm(admin1_text or "")
    matches = []
    for ev in existing_events:
        if norm(ev.get("COUNTRY", "")) != norm(country):
            continue
        hazard_text = norm(f"{ev.get('HAZARD_TYPE','')} {ev.get('HAZARD_SUBTYPE','')}")
        if not any(k in hazard_text for k in hazard_keywords):
            continue
        ev_start, ev_end = event_date_range(ev)
        if onset_dt and not dates_overlap(onset_dt, onset_dt, ev_start, ev_end, MATCH_DATE_WINDOW_DAYS):
            continue
        location_match = False
        if admin1_norm:
            loc_fields = norm(" ".join([
                ev.get("ADMINISTRATIVE_LEVEL_1", ""), ev.get("ADMINISTRATIVE_LEVEL_2", ""),
                ev.get("MUNICIPALITY", ""), ev.get("LOCALITY", ""),
            ]))
            if admin1_norm in loc_fields or any(tok in loc_fields for tok in admin1_norm.split() if len(tok) > 3):
                location_match = True
        distance_km = None
        if lon is not None and lat is not None:
            try:
                ev_lat = float(ev.get("LATITUDE"))
                ev_lon = float(ev.get("LONGITUDE"))
                distance_km = haversine_km(lon, lat, ev_lon, ev_lat)
                if distance_km <= MATCH_DISTANCE_KM:
                    location_match = True
            except (TypeError, ValueError):
                pass
        if location_match:
            matches.append({
                "event_id": ev.get("EVENT_ID"),
                "distance_km": round(distance_km, 1) if distance_km is not None else None,
                "event_status": ev.get("EVENT_STATUS"),
            })
    return matches


def build_candidates():
    today = datetime.now(timezone.utc).date()
    fromdate = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    todate = today.isoformat()
    existing_events = load_existing_events()
    log(f"{len(existing_events)} eventos existentes cargados desde Events/ para el cruce")

    candidates = []
    seen_eventids = set()

    for evtype in EVENT_TYPES:
        hits = fetch_eventlist_for_type(evtype, fromdate, todate)
        log(f"{evtype}: {len(hits)} eventos en paises de la cuenca (ventana {fromdate}..{todate})")
        for feature, basin_iso3s in hits:
            props = feature.get("properties", {})
            eventid = props.get("eventid")
            key = (evtype, eventid)
            if key in seen_eventids:
                continue
            seen_eventids.add(key)

            detail = fetch_eventdata(evtype, eventid)
            if not detail:
                continue
            dprops = detail.get("properties", {})
            sendai = dprops.get("sendai") or []
            numeric_sendai = []
            for s in sendai:
                try:
                    value = int(str(s.get("sendaivalue", "")).replace(",", "").strip())
                except (TypeError, ValueError):
                    continue
                numeric_sendai.append((s, value))

            if not numeric_sendai:
                continue  # regla del usuario: sin cifra de afectacion -> no se incluye

            geom = detail.get("geometry") or {}
            coords = geom.get("coordinates") if geom.get("type") == "Point" else None
            lon, lat = (coords[0], coords[1]) if coords else (None, None)

            # Para VO (coordenada puntual real, el crater), verifica directamente contra la cuenca.
            point_geo_match = None
            if evtype == "VO" and lon is not None:
                inside = point_in_basin(lon, lat)
                if inside is True:
                    point_geo_match = "LIKELY_INSIDE"
                elif inside is False:
                    point_geo_match = "LIKELY_OUTSIDE"
                else:
                    point_geo_match = "UNCERTAIN"

            report_url = f"{GDACS_REPORT_URL}?eventid={eventid}&eventtype={evtype}"
            url_block = props.get("url") or {}
            if url_block.get("report"):
                report_url = url_block["report"]

            for sendai_entry, value in numeric_sendai:
                iso3 = None
                # el iso3 de nivel evento puede faltar (EQ); usa el primer pais de la cuenca detectado
                iso3 = (dprops.get("iso3") or "").strip() or (basin_iso3s[0] if basin_iso3s else "")
                if iso3 not in BASIN_ISO3:
                    continue
                region_text = sendai_entry.get("region", "")
                description = sendai_entry.get("description", "")

                if evtype == "VO" and point_geo_match is not None:
                    geo_match = point_geo_match
                else:
                    geo_match = classify_admin1(iso3, region_text, description)

                if geo_match == "LIKELY_OUTSIDE":
                    continue  # fuera de la cuenca, descartado con confianza

                onset_raw = sendai_entry.get("onset_date") or dprops.get("fromdate")
                try:
                    onset_dt = datetime.strptime(onset_raw[:10], "%Y-%m-%d") if onset_raw else None
                except ValueError:
                    onset_dt = None

                matches = find_possible_matches(
                    iso3, evtype, onset_dt, f"{region_text} {description}", lon, lat, existing_events
                )

                candidates.append({
                    "gdacs_eventtype": evtype,
                    "gdacs_eventid": eventid,
                    "gdacs_episodeid": dprops.get("episodeid"),
                    "country": ISO3_TO_PROJECT_COUNTRY.get(iso3, iso3),
                    "iso3": iso3,
                    "hazard_type_guess": {"FL": "Flood", "DR": "Drought", "VO": "Other (volcanic eruption)"}.get(evtype, evtype),
                    "region_reported": region_text,
                    "geo_basin_match": geo_match,
                    "event_name": dprops.get("name"),
                    "gdacs_alertlevel": dprops.get("alertlevel"),
                    "gdacs_fromdate": dprops.get("fromdate"),
                    "gdacs_todate": dprops.get("todate"),
                    "coordinates": {"lon": lon, "lat": lat} if lon is not None else None,
                    "impact_report": {
                        "sendaitype": sendai_entry.get("sendaitype"),
                        "sendainame": sendai_entry.get("sendainame"),
                        "value": value,
                        "description": description,
                        "onset_date": sendai_entry.get("onset_date"),
                        "expires_date": sendai_entry.get("expires_date"),
                        "suggested_impacts_field": guess_impact_field(sendai_entry.get("sendainame", ""), description),
                    },
                    "possible_matches": matches,
                    "match_type": "POSSIBLE_UPDATE" if matches else "POSSIBLE_NEW_EVENT",
                    "source_url": report_url,
                    "notes": (
                        "Cifra de GDACS/Sendai sin verificar. Nunca escribir directamente en "
                        "Events/ o Impacts/ sin confirmar la fuente primaria y, si es posible, "
                        "una segunda fuente independiente (ver reglas de verificacion del proyecto)."
                    ),
                })

    candidates.sort(key=lambda c: (c["match_type"], c["country"], c["gdacs_eventtype"], c["gdacs_eventid"]))
    return candidates


def main():
    candidates = build_candidates()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "GDACS (gdacs.org), API publica",
        "lookback_days": LOOKBACK_DAYS,
        "event_types_queried": EVENT_TYPES,
        "readme": (
            "Lista de candidatos NO verificados generada automaticamente. Nunca se "
            "escribe directamente en Events/ ni en Impacts/ desde este archivo: cada "
            "entrada requiere revision humana antes de usarse (confirmar fuente, "
            "ubicacion real y evitar duplicados), tal como exige el monitor. "
            "match_type=POSSIBLE_UPDATE sugiere enriquecer un EVENT_ID existente; "
            "POSSIBLE_NEW_EVENT sugiere evaluar si amerita un AMZ-ID nuevo. "
            "geo_basin_match=UNCERTAIN significa que no se pudo confirmar la ubicacion "
            "por nombre de region -- verificar manualmente antes de usar."
        ),
        "count": len(candidates),
        "candidates": candidates,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log(f"{len(candidates)} candidatos escritos en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
