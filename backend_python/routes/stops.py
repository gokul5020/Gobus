from fastapi import APIRouter, HTTPException, Depends, Query
from bson import ObjectId
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import get_db
from middleware.auth import auth_middleware

router = APIRouter(prefix="/api/stops", tags=["stops"])


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    doc["id"]  = doc["_id"]
    return doc


# ── GET /api/stops  (public) ─────────────────────────────────────────────────
@router.get("")
async def get_stops():
    db = get_db()
    cursor = db.busstops.find().sort("name", 1)
    stops  = await cursor.to_list(None)
    return [serialize_doc(s) for s in stops]


# ── GET /api/stops/search?q=  (public) ───────────────────────────────────────
@router.get("/search")
async def search_stops(q: str = Query("")):
    db = get_db()
    cursor = db.busstops.find(
        {"name": {"$regex": q, "$options": "i"}}
    ).sort("name", 1).limit(50)
    stops = await cursor.to_list(None)
    return [serialize_doc(s) for s in stops]


# ── GET /api/stops/:id  (public) ─────────────────────────────────────────────
@router.get("/{stop_id}")
async def get_stop(stop_id: str):
    db = get_db()
    if not ObjectId.is_valid(stop_id):
        raise HTTPException(status_code=400, detail="Invalid stop ID format")
    stop = await db.busstops.find_one({"_id": ObjectId(stop_id)})
    if not stop:
        raise HTTPException(status_code=404, detail="Stop not found")
    return serialize_doc(stop)


# ── POST /api/stops  (admin only) ────────────────────────────────────────────
@router.post("", status_code=201)
async def create_stop(
    body: Dict[str, Any],
    user: dict = Depends(auth_middleware(["admin"]))
):
    db  = get_db()
    name    = body.get("name")
    lat     = body.get("lat")
    lng     = body.get("lng")
    address = body.get("address", "")

    if not name or lat is None or lng is None:
        raise HTTPException(status_code=400, detail="Name, lat, and lng are required")

    existing = await db.busstops.find_one({"name": name})
    if existing:
        raise HTTPException(status_code=400, detail="Stop name already exists")

    new_stop = {
        "name":      name,
        "lat":       float(lat),
        "lng":       float(lng),
        "address":   address,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }

    result = await db.busstops.insert_one(new_stop)
    new_stop["_id"] = result.inserted_id
    return serialize_doc(new_stop)


# ── PUT /api/stops/:id  (admin only) ─────────────────────────────────────────
@router.put("/{stop_id}")
async def update_stop(
    stop_id: str,
    body: Dict[str, Any],
    user: dict = Depends(auth_middleware(["admin"]))
):
    db = get_db()
    if not ObjectId.is_valid(stop_id):
        raise HTTPException(status_code=400, detail="Invalid stop ID format")

    update_data = {k: v for k, v in body.items() if k != "_id"}
    update_data["updatedAt"] = datetime.utcnow()

    result = await db.busstops.find_one_and_update(
        {"_id": ObjectId(stop_id)},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Stop not found")
    return serialize_doc(result)


# ── DELETE /api/stops/:id  (admin only) ──────────────────────────────────────
@router.delete("/{stop_id}")
async def delete_stop(
    stop_id: str,
    user: dict = Depends(auth_middleware(["admin"]))
):
    db = get_db()
    if not ObjectId.is_valid(stop_id):
        raise HTTPException(status_code=400, detail="Invalid stop ID format")

    result = await db.busstops.find_one_and_delete({"_id": ObjectId(stop_id)})
    if not result:
        raise HTTPException(status_code=404, detail="Stop not found")
    return {"message": "Stop deleted successfully"}
