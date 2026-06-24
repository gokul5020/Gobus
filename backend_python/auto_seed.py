"""
auto_seed.py  (CSV-based seeder)
----------------------------------
Reads stopdata.csv and routedata1.csv from the project root (c:\\bus monitor)
and seeds MongoDB on first startup.

CSV formats:
  stopdata.csv   : Stop_id, Stop Name, Lat, Lng
  routedata1.csv : Route_Id, bus_details, route (space-separated Stop_id list), [alternateStops JSON]

Run standalone:
    python auto_seed.py           # skip if data exists
    python auto_seed.py --force   # clear and re-seed
"""

import sys
import io
import csv
import json
import re
import bcrypt
from pathlib import Path
from datetime import datetime

# ── Path resolution ────────────────────────────────────────────────────────
BACKEND_DIR  = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent.parent.parent  # c:\bus monitor

STOP_CSV  = PROJECT_ROOT / "stopdata.csv"
ROUTE_CSV = PROJECT_ROOT / "routedata1.csv"


# ── CSV parsers ─────────────────────────────────────────────────────────────

def parse_stop_csv(filepath: Path) -> dict:
    """
    Returns { stop_id_int -> { stopId, name, lat, lng, address } }
    """
    stops = {}
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items() if k}
            sid_raw = row.get("Stop_id", "").strip()
            name    = row.get("Stop Name", "").strip()
            lat_raw = row.get("Lat", "").strip()
            lng_raw = row.get("Lng", "").strip()
            if not sid_raw or not name:
                continue
            try:
                sid = int(sid_raw)
                lat = float(lat_raw)
                lng = float(lng_raw)
            except ValueError:
                print(f"  ⚠  Skipping invalid stop row: {row}")
                continue
            stops[sid] = {
                "stopId":  sid,
                "name":    name,
                "lat":     lat,
                "lng":     lng,
                "address": f"{name}, Chennai",
            }
    return stops


def _split_csv_line(line: str) -> list:
    """Quoted-field-aware CSV splitter (handles JSON in 4th column)."""
    fields, current, in_quotes = [], "", False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                current += '"'
                i += 1
            else:
                in_quotes = not in_quotes
        elif ch == ',' and not in_quotes:
            fields.append(current)
            current = ""
        else:
            current += ch
        i += 1
    fields.append(current)
    return fields


def parse_route_csv(filepath: Path) -> list:
    """
    Returns list of:
      { routeId:int, busDetails:str, stopIds:[int,...], alternateStops:{} }
    """
    content = filepath.read_text(encoding="utf-8-sig")
    routes = []
    lines = content.splitlines()
    header_skipped = False

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue
        if not header_skipped:
            header_skipped = True
            continue

        parts = _split_csv_line(trimmed)
        # Remove trailing empty fields
        while parts and parts[-1].strip() == "":
            parts.pop()
        if len(parts) < 3:
            continue

        rid_raw     = parts[0].strip()
        bus_details = parts[1].strip()
        stops_raw   = parts[2].strip()
        alt_raw     = parts[3].strip() if len(parts) > 3 else ""

        try:
            route_id = int(rid_raw)
        except ValueError:
            continue

        if not bus_details or not stops_raw:
            continue

        stop_ids = []
        for tok in stops_raw.split():
            try:
                stop_ids.append(int(tok))
            except ValueError:
                pass

        alt_stops = {}
        if alt_raw:
            try:
                alt_stops = json.loads(alt_raw)
            except Exception:
                pass

        routes.append({
            "routeId":        route_id,
            "busDetails":     bus_details,
            "stopIds":        stop_ids,
            "alternateStops": alt_stops,
        })

    return routes


def _derive_route_number(bus_details: str) -> str:
    """Extract short route number from bus_details, e.g. '19B-Towards-X' → '19B'."""
    m = re.match(r'^([A-Z0-9]+(?:[A-Z])?)', bus_details.strip(), re.IGNORECASE)
    return m.group(1).upper() if m else bus_details[:10]


# ── Main seed coroutine ──────────────────────────────────────────────────────

async def auto_seed(force: bool = False):
    from database import get_db

    db = get_db()
    if db is None:
        print("⚠️  No database connection, skipping auto-seed.")
        return

    # Guard – skip if already seeded
    if not force:
        route_count = await db.busroutes.count_documents({})
        stop_count  = await db.busstops.count_documents({})
        if route_count > 0 or stop_count > 0:
            print(f"ℹ️  Database already has {stop_count} stops and {route_count} routes. Skipping auto-seed.")
            return

    # Validate CSV files
    for path, label in [(STOP_CSV, "stopdata.csv"), (ROUTE_CSV, "routedata1.csv")]:
        if not path.exists():
            print(f"❌ Cannot find {label} at: {path}")
            return

    if force:
        print("🗑️  Clearing existing data...")
        await db.busstops.delete_many({})
        await db.busroutes.delete_many({})
        await db.admins.delete_many({})
        await db.requests.delete_many({})
        await db.passengers.delete_many({})

    # ── Default admin accounts ──────────────────────────────────────────────
    admin_count = await db.admins.count_documents({})
    if admin_count == 0:
        admin_pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt(10)).decode("utf-8")
        depot_pw = bcrypt.hashpw(b"depot123", bcrypt.gensalt(10)).decode("utf-8")
        await db.admins.insert_many([
            {
                "name": "System Admin", "username": "admin",
                "password": admin_pw, "role": "admin",
                "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()
            },
            {
                "name": "Depot Operator", "username": "depot",
                "password": depot_pw, "role": "depot",
                "createdAt": datetime.utcnow(), "updatedAt": datetime.utcnow()
            }
        ])
        print("👤 Default accounts created: admin/admin123 and depot/depot123")

    # ── Import Stops ─────────────────────────────────────────────────────────
    print(f"\n📄 Reading stops from: {STOP_CSV}")
    stops_data = parse_stop_csv(STOP_CSV)
    print(f"   Found {len(stops_data)} stops in CSV.")

    # Deduplicate by name (stopdata.csv has stops with duplicate names)
    # Keep all stopIds → same MongoDB doc via name->stopIds mapping
    name_to_stop_ids: dict[str, list] = {}   # name → [stopId, ...]
    name_to_first:    dict[str, dict] = {}   # name → first-seen stop dict

    for sid, s in stops_data.items():
        if s["name"] not in name_to_stop_ids:
            name_to_stop_ids[s["name"]] = []
            name_to_first[s["name"]] = s
        name_to_stop_ids[s["name"]].append(sid)

    print(f"   Unique stop names: {len(name_to_first)} ({len(stops_data) - len(name_to_first)} duplicates merged).")

    now = datetime.utcnow()
    stop_docs = [
        {
            "stopId":    s["stopId"],
            "name":      s["name"],
            "lat":       s["lat"],
            "lng":       s["lng"],
            "address":   s["address"],
            "createdAt": now,
            "updatedAt": now,
        }
        for s in name_to_first.values()
    ]

    if stop_docs:
        await db.busstops.insert_many(stop_docs, ordered=False)
        print(f"✅ Inserted {len(stop_docs)} stops into MongoDB.")

    # Build stopId (int) → MongoDB ObjectId
    stop_oid_map: dict[int, object] = {}   # int stopId → ObjectId
    name_to_oid:  dict[str, object] = {}   # name → ObjectId

    async for s in db.busstops.find({}, {"stopId": 1, "name": 1, "_id": 1}):
        name_to_oid[s["name"]] = s["_id"]

    # Map every original stopId (including merged duplicates) → ObjectId
    for name, ids in name_to_stop_ids.items():
        oid = name_to_oid.get(name)
        if oid:
            for sid in ids:
                stop_oid_map[sid] = oid

    # ── Import Routes ─────────────────────────────────────────────────────────
    print(f"\n📄 Reading routes from: {ROUTE_CSV}")
    routes_data = parse_route_csv(ROUTE_CSV)
    print(f"   Found {len(routes_data)} routes in CSV.")

    route_docs = []
    missing_total = 0

    for r in routes_data:
        # Use the numeric routeId as the unique routeNumber to avoid conflicts
        # between route directions (e.g. 19B Saidapet and 19B Kelambakkam both
        # have routeNumber "19B" but different routeIds 1101 and 1102).
        route_number = str(r["routeId"])
        bus_name     = re.sub(r'[-_]+', ' ', r["busDetails"]).strip()

        stop_oids = []
        missing   = []
        for sid in r["stopIds"]:
            oid = stop_oid_map.get(sid)
            if oid:
                stop_oids.append(oid)
            else:
                missing.append(sid)

        if missing:
            missing_total += len(missing)
            m_preview = missing[:5]
            print(f"  ⚠  Route {r['routeId']} ({r['busDetails']}): "
                  f"{len(missing)} stop IDs not in stopdata.csv → {m_preview}{'...' if len(missing)>5 else ''}")

        route_docs.append({
            "routeId":        r["routeId"],
            "routeNumber":    route_number,
            "busName":        bus_name,
            "busDetails":     r["busDetails"],
            "stops":          stop_oids,
            "alternateStops": r["alternateStops"],
            "description":    f"Chennai Bus Route – {r['busDetails']}",
            "isActive":       True,
            "createdAt":      now,
            "updatedAt":      now,
        })

    if route_docs:
        await db.busroutes.insert_many(route_docs)
        print(f"✅ Inserted {len(route_docs)} routes into MongoDB.")

    if missing_total:
        print(f"\n⚠️  Total unresolved stop IDs across all routes: {missing_total}")

    print(f"\n✨ Auto-seed done! Imported {len(stop_docs)} stops and {len(route_docs)} routes.")


# ── Standalone runner ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import asyncio

    # Fix UTF-8 console output only when run as a standalone script (not imported)
    if sys.platform.startswith("win"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    force = "--force" in sys.argv

    async def _run():
        from database import connect_db
        await connect_db()
        await auto_seed(force=force)

    asyncio.run(_run())
