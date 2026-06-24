"""
build_data_from_pdf.py
======================================================================
Reads "MTC bus routes.pdf" (Chennai MTC route directory) and regenerates
the seed CSVs consumed by auto_seed.py:

    <project_root>/stopdata.csv    -> Stop_id, Stop Name, Lat, Lng
    <project_root>/routedata1.csv  -> Route_Id, bus_details, route, alternateStops

The PDF contains, for every route: bus number, start, destination and the
ordered list of intermediate stops (by name) -- but no coordinates. To keep
the live map / simulator working, each unique stop gets a latitude/longitude
resolved in this priority order:

    1. Reuse real coordinates from the existing stopdata.csv when the stop
       name matches (whitespace/case/suffix-insensitive).
    2. Geocode the name via OpenStreetMap Nominatim ("<name>, Chennai,
       Tamil Nadu, India"), cached on disk so re-runs are instant.
    3. Deterministic synthetic coordinate inside the Chennai metro bounds
       (only used when the two steps above fail).

Usage:
    python build_data_from_pdf.py                # match + geocode + write CSVs
    python build_data_from_pdf.py --no-geocode   # skip network, use CSV+synthetic
    python build_data_from_pdf.py --limit-geocode 50   # cap geocode lookups

After running, re-seed MongoDB:
    python auto_seed.py --force
"""

import sys
import io
import re
import csv
import json
import time
import hashlib
import argparse
import urllib.parse
import urllib.request
from pathlib import Path

import pdfplumber

# Make stdout UTF-8 safe on the Windows console.
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent.parent.parent          # c:\bus monitor

PDF_PATH = BACKEND_DIR / "MTC bus routes.pdf"
STOP_CSV = PROJECT_ROOT / "stopdata.csv"
ROUTE_CSV = PROJECT_ROOT / "routedata1.csv"
GEOCODE_CACHE = BACKEND_DIR / "_geocode_cache.json"

# Chennai metropolitan bounding box (used for the synthetic fallback only).
CHN_LAT_MIN, CHN_LAT_MAX = 12.83, 13.23
CHN_LNG_MIN, CHN_LNG_MAX = 80.10, 80.30

SECTION_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
# Suffix tokens stripped only when matching a PDF name against the CSV.
SUFFIX_RE = re.compile(
    r"\b(b\.?s\.?|bus\s*stand|bus\s*stop|i\.?e\.?|o\.?t\.?|depot|terminus|"
    r"junction|jn|estate|market|signal|terminal|round\s*tana|roundtana)\b",
    re.IGNORECASE,
)


# ── small helpers ────────────────────────────────────────────────────────────
def clean(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s.replace("\n", " ")).strip()


def repair_wrap(name):
    """Re-join words split mid-way by PDF line-wrapping.

    The PDF wraps long stop names across lines, inserting a space inside a
    word: "Agaramthe n", "Kelambakk am", "Chengelpat tu". The continuation
    fragment is always a short (<=3 char) all-lowercase tail glued to a longer
    preceding word, so we can merge those safely while leaving genuine
    multi-word names ("Kannagi Nagar", "Arcot Road") untouched.
    """
    name = clean(name).strip(" .-")
    tokens = name.split(" ")
    out = []
    for tok in tokens:
        if (
            out
            and re.fullmatch(r"[a-z]{1,3}", tok)        # short lowercase tail
            and re.fullmatch(r"[A-Za-z][A-Za-z.]{3,}", out[-1])  # real word before
        ):
            out[-1] = out[-1] + tok
        else:
            out.append(tok)
    return " ".join(out)


def norm(s):
    """Aggressive key: lowercase, alphanumerics only (collapses spacing/typos)."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def norm_loose(s):
    """Like norm() but also drops common stop-type suffixes for fuzzy matching."""
    return norm(SUFFIX_RE.sub(" ", s))


# ── PDF parsing ──────────────────────────────────────────────────────────────
def split_stops(route_text):
    """Commas/slashes separate stops; newlines are cosmetic word-wrap -> space."""
    parts = re.split(r"[,/]", route_text.replace("\n", " "))
    out = []
    for p in parts:
        p = repair_wrap(p)
        if p and p.lower() != "route":
            out.append(p)
    return out


def parse_pdf(pdf_path):
    """Return list of {busNo, start, dest, section, stops:[ordered names]}."""
    routes = []
    with pdfplumber.open(pdf_path) as pdf:
        current_section = None
        for page in pdf.pages:
            for table in page.extract_tables():
                col_start = col_dest = col_route = None
                for row in table:
                    cells = [clean(c) for c in row]
                    for c in cells:
                        m = SECTION_RE.match(c)
                        if m:
                            current_section = m.group(1).strip()
                    if "Start" in cells and "Destination" in cells:
                        col_start = cells.index("Start")
                        col_dest = cells.index("Destination")
                        col_route = cells.index("Route") if "Route" in cells else None
                        continue
                    if col_start is None:
                        continue
                    busno_cells = [c for c in cells[:col_start] if c]
                    busno = busno_cells[0] if busno_cells else ""
                    start = repair_wrap(cells[col_start]) if col_start < len(cells) else ""
                    dest = repair_wrap(cells[col_dest]) if col_dest < len(cells) else ""
                    route_cell = (
                        cells[col_route]
                        if col_route is not None and col_route < len(cells)
                        else ""
                    )
                    if busno.lower() in ("bus", "no") or start.lower() == "start":
                        continue
                    if not busno or not start or not dest:
                        continue
                    stops = [start] + split_stops(route_cell) + [dest]
                    # de-dupe consecutive identical stops
                    deduped = []
                    for s in stops:
                        if not deduped or norm(deduped[-1]) != norm(s):
                            deduped.append(s)
                    routes.append(
                        {
                            "busNo": busno,
                            "start": start,
                            "dest": dest,
                            "section": current_section,
                            "stops": deduped,
                        }
                    )
    return routes


# ── coordinate resolution ────────────────────────────────────────────────────
def load_csv_coords(path):
    """Existing stopdata.csv -> {norm_key: (clean_name, lat, lng)} (two keymaps)."""
    exact, loose = {}, {}
    if not path.exists():
        return exact, loose
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("Stop Name") or "").strip()
            try:
                lat = float(row["Lat"])
                lng = float(row["Lng"])
            except (TypeError, ValueError, KeyError):
                continue
            if not name:
                continue
            # space-out the squashed CSV names a little for nicer display
            exact.setdefault(norm(name), (name, lat, lng))
            loose.setdefault(norm_loose(name), (name, lat, lng))
    return exact, loose


def synthetic_coord(name):
    """Deterministic point inside the Chennai box derived from the stop name."""
    h = hashlib.md5(name.encode("utf-8")).digest()
    f1 = int.from_bytes(h[0:4], "big") / 0xFFFFFFFF
    f2 = int.from_bytes(h[4:8], "big") / 0xFFFFFFFF
    lat = round(CHN_LAT_MIN + f1 * (CHN_LAT_MAX - CHN_LAT_MIN), 6)
    lng = round(CHN_LNG_MIN + f2 * (CHN_LNG_MAX - CHN_LNG_MIN), 6)
    return lat, lng


def load_cache():
    if GEOCODE_CACHE.exists():
        try:
            return json.loads(GEOCODE_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache):
    GEOCODE_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0),
                             encoding="utf-8")


def geocode(name, cache):
    """Nominatim lookup -> (lat,lng) or None. Cached (None stored as 'null')."""
    key = norm(name)
    if key in cache:
        v = cache[key]
        return tuple(v) if v else None
    q = urllib.parse.quote(f"{name}, Chennai, Tamil Nadu, India")
    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "smartbus-seed/1.0"})
    result = None
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                lat, lng = float(data[0]["lat"]), float(data[0]["lon"])
                # keep only results that land near Chennai
                if 12.4 <= lat <= 13.6 and 79.8 <= lng <= 80.6:
                    result = (lat, lng)
    except Exception as e:
        print(f"   ! geocode failed for {name!r}: {e}")
    cache[key] = list(result) if result else None
    save_cache(cache)
    time.sleep(1.1)  # respect Nominatim 1 req/sec policy
    return result


# ── main build ───────────────────────────────────────────────────────────────
def build(do_geocode=True, geocode_limit=None):
    print(f"📄 Parsing {PDF_PATH.name} ...")
    routes = parse_pdf(PDF_PATH)
    print(f"   Parsed {len(routes)} routes.")

    # Collect unique stops (first-seen display name per normalized key).
    stop_display = {}        # norm_key -> display name
    for r in routes:
        for s in r["stops"]:
            stop_display.setdefault(norm(s), s)
    print(f"   {len(stop_display)} unique stops.")

    # Always read coordinate references from the pristine original (the .bak,
    # if a previous run already created it) so re-runs never feed on their own
    # synthetic output.
    coord_source = STOP_CSV.with_suffix(STOP_CSV.suffix + ".bak")
    if not coord_source.exists():
        coord_source = STOP_CSV
    exact, loose = load_csv_coords(coord_source)
    print(f"   Loaded {len(exact)} coordinate references from {coord_source.name}.")

    cache = load_cache()
    coords = {}              # norm_key -> (display, lat, lng)
    n_csv = n_geo = n_syn = 0
    geocoded = 0

    for key, name in stop_display.items():
        # 1. real coords from CSV
        if key in exact:
            cn, lat, lng = exact[key]
            coords[key] = (cn, lat, lng)
            n_csv += 1
            continue
        lkey = norm_loose(name)
        if lkey in loose:
            cn, lat, lng = loose[lkey]
            coords[key] = (name, lat, lng)
            n_csv += 1
            continue
        # 2. geocode
        if do_geocode and (geocode_limit is None or geocoded < geocode_limit):
            cached_before = norm(name) in cache
            g = geocode(name, cache)
            if not cached_before:
                geocoded += 1
            if g:
                coords[key] = (name, round(g[0], 6), round(g[1], 6))
                n_geo += 1
                continue
        # 3. synthetic fallback
        lat, lng = synthetic_coord(name)
        coords[key] = (name, lat, lng)
        n_syn += 1

    print(f"   Coordinates -> CSV match: {n_csv}, geocoded: {n_geo}, synthetic: {n_syn}")

    # Assign stable integer Stop_ids (sorted by name for determinism).
    ordered_keys = sorted(coords, key=lambda k: coords[k][0].lower())
    key_to_id = {k: i + 1 for i, k in enumerate(ordered_keys)}

    # ── write stopdata.csv ────────────────────────────────────────────────
    backup(STOP_CSV)
    with open(STOP_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Stop_id", "Stop Name", "Lat", "Lng"])
        for k in ordered_keys:
            name, lat, lng = coords[k]
            w.writerow([key_to_id[k], name, lat, lng])
    print(f"✅ Wrote {len(ordered_keys)} stops -> {STOP_CSV}")

    # ── write routedata1.csv ──────────────────────────────────────────────
    backup(ROUTE_CSV)
    with open(ROUTE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Route_Id", "bus_details", "route", "alternateStops"])
        for i, r in enumerate(routes):
            route_id = 10001 + i
            bus_details = f"{r['busNo']} : {r['start']} to {r['dest']}"
            stop_ids = [str(key_to_id[norm(s)]) for s in r["stops"] if norm(s) in key_to_id]
            w.writerow([route_id, bus_details, " ".join(stop_ids), ""])
    print(f"✅ Wrote {len(routes)} routes -> {ROUTE_CSV}")
    print("\n✨ Done. Re-seed with:  python auto_seed.py --force")


def backup(path):
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
            print(f"   (backed up original -> {bak.name})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-geocode", action="store_true", help="skip network geocoding")
    ap.add_argument("--limit-geocode", type=int, default=None,
                    help="max number of new geocode lookups this run")
    args = ap.parse_args()
    build(do_geocode=not args.no_geocode, geocode_limit=args.limit_geocode)
