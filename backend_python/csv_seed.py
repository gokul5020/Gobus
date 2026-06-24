"""
csv_seed.py
-----------
Imports stop and route data from CSV files into MongoDB.

CSV files expected (relative to project root c:\\bus monitor):
  - stopdata.csv   : Stop_id, Stop Name, Lat, Lng
  - routedata1.csv : Route_Id, bus_details, route (space-separated stop_ids)

Usage (run from backend_python directory):
    python csv_seed.py
    python csv_seed.py --force   # clears existing data before seeding
"""

import asyncio
import csv
import sys
import json
import re
import bcrypt
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent.parent.parent  # c:\bus monitor

STOP_CSV = PROJECT_ROOT / "stopdata.csv"
ROUTE_CSV = PROJECT_ROOT / "routedata1.csv"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
sys.path.insert(0, str(BACKEND_DIR))
from database import connect_db, get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_stop_csv(filepath: Path):
    """
    Returns a dict: { stop_id_int -> { "stopId": int, "name": str, "lat": float, "lng": float } }
    """
    stops = {}
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Strip BOM / whitespace from keys
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
                "stopId": sid,
                "name": name,
                "lat": lat,
                "lng": lng,
                "address": f"{name}, Chennai",
            }
    return stops


def parse_route_csv(filepath: Path):
    """
    Returns a list of dicts:
      { "routeId": int, "busDetails": str, "stopIds": [int, ...], "alternateStops": dict }
    
    The 4th column (if present) encodes alternate/cut-service stop mappings as JSON.
    """
    routes = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        # Read raw text to handle the trailing comma / mixed quoting
        content = f.read()

    # Re-parse via csv reader
    reader = csv.reader(content.splitlines())
    header_skipped = False
    for row in reader:
        if not header_skipped:
            header_skipped = True
            continue  # skip header

        # Clean up empty trailing fields
        row = [c.strip() for c in row]
        while row and row[-1] == "":
            row.pop()

        if len(row) < 3:
            continue

        rid_raw      = row[0].strip()
        bus_details  = row[1].strip()
        stops_raw    = row[2].strip()
        alt_raw      = row[3].strip() if len(row) > 3 else ""

        if not rid_raw or not bus_details or not stops_raw:
            continue

        try:
            route_id = int(rid_raw)
        except ValueError:
            continue

        # Parse stop IDs (space-separated integers)
        stop_ids = []
        for tok in stops_raw.split():
            try:
                stop_ids.append(int(tok))
            except ValueError:
                pass

        # Parse alternate stop JSON if present
        alt_stops = {}
        if alt_raw:
            try:
                alt_stops = json.loads(alt_raw)
            except Exception:
                pass

        routes.append({
            "routeId":       route_id,
            "busDetails":    bus_details,
            "stopIds":       stop_ids,
            "alternateStops": alt_stops,
        })

    return routes


def build_route_number_and_name(bus_details: str):
    """
    'bus_details' format examples:
        "19B-Towards-saidapet"
        "5C -Towards-Broadway"
        "154-Towards-PATTUR"
        "19B Saidapet to Siruseri (cut service)"

    Returns (routeNumber, busName) e.g. ("19B", "19B Towards Saidapet")
    """
    # Extract the route number prefix (letters/digits before first space or hyphen)
    m = re.match(r'^([A-Z0-9]+(?:[A-Z])?)', bus_details.strip(), re.IGNORECASE)
    route_number = m.group(1).upper() if m else bus_details[:10]

    # Humanise bus_details for busName
    bus_name = bus_details.replace("-", " ").replace("_", " ").strip()
    # Normalise multiple spaces
    bus_name = re.sub(r'\s+', ' ', bus_name)

    return route_number, bus_name


# ---------------------------------------------------------------------------
# Main seed coroutine
# ---------------------------------------------------------------------------

async def seed(force: bool = False):
    await connect_db()
    db = get_db()

    if db is None:
        print("❌ No database connection. Aborting.")
        return

    # ------------------------------------------------------------------
    # Guard – skip if data already exists (unless --force)
    # ------------------------------------------------------------------
    if not force:
        existing_stops  = await db.busstops.count_documents({})
        existing_routes = await db.busroutes.count_documents({})
        if existing_stops > 0 or existing_routes > 0:
            print(
                f"ℹ️  Database already has {existing_stops} stops and "
                f"{existing_routes} routes.\n"
                "    Run with --force to clear and re-seed."
            )
            return

    # ------------------------------------------------------------------
    # Validate CSV files exist
    # ------------------------------------------------------------------
    for path, label in [(STOP_CSV, "stopdata.csv"), (ROUTE_CSV, "routedata1.csv")]:
        if not path.exists():
            print(f"❌ Cannot find {label} at: {path}")
            return

    # ------------------------------------------------------------------
    # Clear collections if --force
    # ------------------------------------------------------------------
    if force:
        print("🗑️  Clearing existing data...")
        await db.busstops.delete_many({})
        await db.busroutes.delete_many({})
        await db.admins.delete_many({})

    # ------------------------------------------------------------------
    # Default admin accounts
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Import Stops from stopdata.csv
    # ------------------------------------------------------------------
    print(f"\n📄 Reading stops from: {STOP_CSV}")
    stops_data = parse_stop_csv(STOP_CSV)
    print(f"   Found {len(stops_data)} stops in CSV.")

    now = datetime.utcnow()
    stop_docs = []
    for sid, s in stops_data.items():
        stop_docs.append({
            "stopId":     s["stopId"],
            "name":       s["name"],
            "lat":        s["lat"],
            "lng":        s["lng"],
            "address":    s["address"],
            "createdAt":  now,
            "updatedAt":  now,
        })

    if stop_docs:
        result = await db.busstops.insert_many(stop_docs)
        print(f"✅ Inserted {len(result.inserted_ids)} stops into MongoDB.")

    # Build stopId → MongoDB _id map
    stop_oid_map = {}  # int stopId -> ObjectId
    async for s in db.busstops.find({}, {"stopId": 1, "_id": 1}):
        stop_oid_map[s["stopId"]] = s["_id"]

    # ------------------------------------------------------------------
    # Import Routes from routedata1.csv
    # ------------------------------------------------------------------
    print(f"\n📄 Reading routes from: {ROUTE_CSV}")
    routes_data = parse_route_csv(ROUTE_CSV)
    print(f"   Found {len(routes_data)} routes in CSV.")

    route_docs = []
    skipped = 0
    for r in routes_data:
        route_number, bus_name = build_route_number_and_name(r["busDetails"])

        # Map integer stop IDs to ObjectIds
        stop_oids = []
        missing = []
        for sid in r["stopIds"]:
            oid = stop_oid_map.get(sid)
            if oid:
                stop_oids.append(oid)
            else:
                missing.append(sid)

        if missing:
            print(f"  ⚠  Route {r['routeId']} ({r['busDetails']}): "
                  f"{len(missing)} stop IDs not found in stopdata.csv → {missing[:5]}{'...' if len(missing)>5 else ''}")

        route_docs.append({
            "routeId":        r["routeId"],
            "routeNumber":    route_number,
            "busName":        bus_name,
            "busDetails":     r["busDetails"],
            "stops":          stop_oids,
            "alternateStops": r["alternateStops"],
            "isActive":       True,
            "createdAt":      now,
            "updatedAt":      now,
        })

    if route_docs:
        result = await db.busroutes.insert_many(route_docs)
        print(f"✅ Inserted {len(result.inserted_ids)} routes into MongoDB.")

    print(
        f"\n🎉 CSV seed complete!\n"
        f"   Stops:  {len(stop_docs)}\n"
        f"   Routes: {len(route_docs)}\n"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    force = "--force" in sys.argv
    asyncio.run(seed(force=force))
