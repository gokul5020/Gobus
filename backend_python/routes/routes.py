from fastapi import APIRouter, HTTPException, Depends, Query
from bson import ObjectId
from typing import Optional, List, Dict, Any
from datetime import datetime
from database import get_db
from middleware.auth import auth_middleware

router = APIRouter(prefix="/api/routes", tags=["routes"])


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    doc["id"]  = doc["_id"]
    if "stops" in doc:
        doc["stops"] = [serialize_stop(s) for s in doc["stops"]]
    return doc


def serialize_stop(stop: Any) -> Any:
    if isinstance(stop, dict) and "_id" in stop:
        stop["_id"] = str(stop["_id"])
        stop["id"]  = stop["_id"]
    return stop


async def populate_routes_stops(routes: List[Dict[str, Any]], db) -> List[Dict[str, Any]]:
    """Resolve stop ObjectIds in each route to full stop documents."""
    stop_ids: set = set()
    for r in routes:
        for s_id in r.get("stops", []):
            stop_ids.add(s_id)

    if not stop_ids:
        return routes

    stops_list = await db.busstops.find({"_id": {"$in": list(stop_ids)}}).to_list(None)
    stops_map  = {s["_id"]: s for s in stops_list}

    for r in routes:
        r["stops"] = [stops_map[s_id] for s_id in r.get("stops", []) if s_id in stops_map]

    return routes


# ── GET /api/routes  (public – active routes) ────────────────────────────────
@router.get("")
async def get_active_routes(stopId: Optional[str] = Query(None)):
    db = get_db()
    cursor = db.busroutes.find({"isActive": True}).sort("routeNumber", 1)
    routes = await cursor.to_list(None)
    routes = await populate_routes_stops(routes, db)

    if stopId:
        # Offer a route only when the selected stop lies on it AND the bus
        # continues onward from there (i.e. the stop is not the terminus).
        # Buses that merely end at the stop are dropped – you can't board them
        # to travel forward.
        filtered = []
        for r in routes:
            sids = [str(s.get("_id", s.get("id"))) for s in r["stops"]]
            if any(sid == stopId and i < len(sids) - 1 for i, sid in enumerate(sids)):
                filtered.append(r)
        routes = filtered

    return [serialize_doc(r) for r in routes]


# ── GET /api/routes/all  (admin – includes inactive) ─────────────────────────
@router.get("/all")
async def get_all_routes(user: dict = Depends(auth_middleware(["admin"]))):
    db = get_db()
    cursor = db.busroutes.find().sort("routeNumber", 1)
    routes = await cursor.to_list(None)
    routes = await populate_routes_stops(routes, db)
    return [serialize_doc(r) for r in routes]


# ── GET /api/routes/search?q=  (public) ──────────────────────────────────────
@router.get("/search")
async def search_routes(q: str = Query("")):
    db = get_db()
    query = {
        "isActive": True,
        "$or": [
            {"routeNumber": {"$regex": q, "$options": "i"}},
            {"busName":     {"$regex": q, "$options": "i"}},
            {"busDetails":  {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    }
    cursor = db.busroutes.find(query)
    routes = await cursor.to_list(None)
    routes = await populate_routes_stops(routes, db)
    return [serialize_doc(r) for r in routes]


# ── GET /api/routes/:id  (public) ────────────────────────────────────────────
@router.get("/{route_id}")
async def get_route(route_id: str):
    db = get_db()
    if not ObjectId.is_valid(route_id):
        raise HTTPException(status_code=400, detail="Invalid route ID format")
    route = await db.busroutes.find_one({"_id": ObjectId(route_id)})
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    routes = await populate_routes_stops([route], db)
    return serialize_doc(routes[0])


# ── POST /api/routes  (admin only) ───────────────────────────────────────────
@router.post("", status_code=201)
async def create_route(
    body: Dict[str, Any],
    user: dict = Depends(auth_middleware(["admin"]))
):
    db = get_db()
    route_number = body.get("routeNumber")
    bus_name     = body.get("busName")
    stops_ids    = body.get("stops", [])
    description  = body.get("description", "")
    bus_details  = body.get("busDetails", "")

    if not route_number or not bus_name:
        raise HTTPException(status_code=400, detail="Route number and bus name are required")

    existing = await db.busroutes.find_one({"routeNumber": route_number})
    if existing:
        raise HTTPException(status_code=400, detail="Route number already exists")

    stop_object_ids = [ObjectId(sid) for sid in stops_ids if ObjectId.is_valid(sid)]

    new_route = {
        "routeNumber":    route_number,
        "busName":        bus_name,
        "busDetails":     bus_details,
        "stops":          stop_object_ids,
        "alternateStops": body.get("alternateStops", {}),
        "description":    description,
        "isActive":       True,
        "createdAt":      datetime.utcnow(),
        "updatedAt":      datetime.utcnow()
    }

    result = await db.busroutes.insert_one(new_route)
    new_route["_id"] = result.inserted_id

    routes = await populate_routes_stops([new_route], db)
    return serialize_doc(routes[0])


# ── PUT /api/routes/:id  (admin only) ────────────────────────────────────────
@router.put("/{route_id}")
async def update_route(
    route_id: str,
    body: Dict[str, Any],
    user: dict = Depends(auth_middleware(["admin"]))
):
    db = get_db()
    if not ObjectId.is_valid(route_id):
        raise HTTPException(status_code=400, detail="Invalid route ID format")

    update_data = {k: v for k, v in body.items() if k != "_id"}
    update_data["updatedAt"] = datetime.utcnow()

    if "stops" in update_data:
        update_data["stops"] = [ObjectId(sid) for sid in update_data["stops"] if ObjectId.is_valid(sid)]

    result = await db.busroutes.find_one_and_update(
        {"_id": ObjectId(route_id)},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Route not found")

    routes = await populate_routes_stops([result], db)
    return serialize_doc(routes[0])


# ── DELETE /api/routes/:id  (admin only) ─────────────────────────────────────
@router.delete("/{route_id}")
async def delete_route(
    route_id: str,
    user: dict = Depends(auth_middleware(["admin"]))
):
    db = get_db()
    if not ObjectId.is_valid(route_id):
        raise HTTPException(status_code=400, detail="Invalid route ID format")

    result = await db.busroutes.find_one_and_delete({"_id": ObjectId(route_id)})
    if not result:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"message": "Route deleted successfully"}
