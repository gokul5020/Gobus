from fastapi import APIRouter, HTTPException, Depends, Query, Request as FastAPIRequest, status
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from typing import Optional, List, Dict, Any
from datetime import datetime
from database import get_db
from middleware.auth import auth_middleware
from models import BusRequestCreate
from bus_simulator import dispatch_bus_to_stop

router = APIRouter(prefix="/api/requests", tags=["requests"])

THRESHOLD = 5

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    doc["id"] = doc["_id"]
    
    # Serialize nested documents
    for field in ["passenger", "route", "stop"]:
        if field in doc and doc[field]:
            if "_id" in doc[field]:
                doc[field]["_id"] = str(doc[field]["_id"])
                doc[field]["id"] = doc[field]["_id"]
            if "stops" in doc[field]:
                # Exclude full stops nesting to avoid large payloads
                del doc[field]["stops"]
                
    return doc

async def populate_requests(req_list: List[Dict[str, Any]], db) -> List[Dict[str, Any]]:
    if not req_list:
        return []
        
    # Gather IDs
    p_ids = set()
    r_ids = set()
    s_ids = set()
    for r in req_list:
        if r.get("passenger"):
            p_ids.add(ObjectId(r["passenger"]))
        if r.get("route"):
            r_ids.add(ObjectId(r["route"]))
        if r.get("stop"):
            s_ids.add(ObjectId(r["stop"]))
            
    # Query database
    passengers = await db.passengers.find({"_id": {"$in": list(p_ids)}}, {"mobile": 1}).to_list(None)
    routes = await db.busroutes.find({"_id": {"$in": list(r_ids)}}, {"routeNumber": 1, "busName": 1}).to_list(None)
    stops = await db.busstops.find({"_id": {"$in": list(s_ids)}}, {"name": 1, "lat": 1, "lng": 1}).to_list(None)
    
    # Map by ID
    p_map = {p["_id"]: p for p in passengers}
    r_map = {rt["_id"]: rt for rt in routes}
    s_map = {s["_id"]: s for s in stops}
    
    # Inject references
    for r in req_list:
        p_id = ObjectId(r.get("passenger")) if r.get("passenger") else None
        rt_id = ObjectId(r.get("route")) if r.get("route") else None
        st_id = ObjectId(r.get("stop")) if r.get("stop") else None
        
        r["passenger"] = p_map.get(p_id) if p_id in p_map else None
        r["route"] = r_map.get(rt_id) if rt_id in r_map else None
        r["stop"] = s_map.get(st_id) if st_id in s_map else None
        
    return req_list

@router.post("", status_code=201)
async def create_request(
    body: BusRequestCreate,
    request: FastAPIRequest,
    user: dict = Depends(auth_middleware(["passenger"]))
):
    db = get_db()
    sio = request.app.state.sio
    
    passenger_id = ObjectId(user["id"])
    route_id = ObjectId(body.routeId)
    stop_id = ObjectId(body.stopId)
    
    # One active request per passenger
    existing = await db.requests.find_one({"passenger": passenger_id, "status": "pending"})
    if existing:
        populated = await populate_requests([existing], db)
        raise HTTPException(
            status_code=409,
            detail={
                "message": "You already have an active request. Please wait for it to be fulfilled before making a new one.",
                # jsonable_encoder converts datetimes/ObjectIds so the error
                # body serializes (HTTPException details bypass FastAPI's
                # automatic response encoding).
                "existingRequest": jsonable_encoder(serialize_doc(populated[0]))
            }
        )
        
    new_request = {
        "passenger": passenger_id,
        "route": route_id,
        "stop": stop_id,
        "status": "pending",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    
    result = await db.requests.insert_one(new_request)
    new_request["_id"] = result.inserted_id
    
    # Populate for socket emit and response
    populated = await populate_requests([new_request], db)
    req_data = serialize_doc(populated[0])
    
    # Socket.io: emit to depot
    if sio:
        await sio.emit("new-request", req_data, room="depot")
        
        # Check threshold alert
        count = await db.requests.count_documents({
            "stop": stop_id,
            "route": route_id,
            "status": "pending"
        })
        if count >= THRESHOLD:
            await sio.emit("threshold-alert", {
                "stopId": str(stop_id),
                "routeId": str(route_id),
                "count": count,
                "message": f"Alert! {count} passengers waiting at this stop for this route."
            }, room="depot")
            
    return {"message": "Request sent successfully", "request": req_data}

@router.get("")
async def get_requests(
    status: Optional[str] = Query(None),
    stopId: Optional[str] = Query(None),
    routeId: Optional[str] = Query(None),
    user: dict = Depends(auth_middleware(["depot", "admin"]))
):
    db = get_db()
    filter_query = {}
    if status:
        filter_query["status"] = status
    if stopId and ObjectId.is_valid(stopId):
        filter_query["stop"] = ObjectId(stopId)
    if routeId and ObjectId.is_valid(routeId):
        filter_query["route"] = ObjectId(routeId)
        
    cursor = db.requests.find(filter_query).sort("createdAt", -1)
    requests = await cursor.to_list(None)
    
    # Populate
    requests = await populate_requests(requests, db)
    serialized = [serialize_doc(r) for r in requests]
    
    # Group by stop + route
    grouped = {}
    for r in serialized:
        stop_name = r.get("stop", {}).get("name", "Unknown") if r.get("stop") else "Unknown"
        route_num = r.get("route", {}).get("routeNumber", "?") if r.get("route") else "?"
        key = f"{stop_name}||{route_num}"
        if key not in grouped:
            grouped[key] = {
                "stop": r.get("stop"),
                "route": r.get("route"),
                "requests": [],
                "count": 0
            }
        grouped[key]["requests"].append(r)
        grouped[key]["count"] += 1
        
    return {
        "requests": serialized,
        "grouped": list(grouped.values())
    }

@router.get("/my")
async def get_my_requests(user: dict = Depends(auth_middleware(["passenger"]))):
    db = get_db()
    passenger_id = ObjectId(user["id"])
    
    cursor = db.requests.find({"passenger": passenger_id}).sort("createdAt", -1)
    requests = await cursor.to_list(None)
    
    requests = await populate_requests(requests, db)
    return [serialize_doc(r) for r in requests]

@router.patch("/{request_id}/send-bus")
async def send_bus(
    request_id: str,
    request: FastAPIRequest,
    user: dict = Depends(auth_middleware(["depot", "admin"]))
):
    db = get_db()
    sio = request.app.state.sio
    
    if not ObjectId.is_valid(request_id):
        raise HTTPException(status_code=400, detail="Invalid request ID format")
        
    req_doc = await db.requests.find_one({"_id": ObjectId(request_id)})
    if not req_doc:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req_doc.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Request is already processed")
        
    # Update status to sent
    updated_at = datetime.utcnow()
    await db.requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": "sent",
            "sentAt": updated_at,
            "updatedAt": updated_at
        }}
    )
    
    req_doc["status"] = "sent"
    req_doc["sentAt"] = updated_at
    
    # Populate
    populated = await populate_requests([req_doc], db)
    req_data = serialize_doc(populated[0])
    
    passenger_id_str = str(req_doc["passenger"]["id"] if isinstance(req_doc["passenger"], dict) else req_doc["passenger"])
    
    # Socket emits
    if sio:
        # Notify wait passenger
        await sio.emit("bus-sent", {
            "requestId": request_id,
            "message": "Bus is on the way! Watch it live on the map 🚌",
            "route": req_data["route"],
            "stop": req_data["stop"]
        }, room=f"passenger:{passenger_id_str}")
        
        # Notify depot dashboard
        await sio.emit("request-updated", {
            "requestId": request_id,
            "status": "sent"
        }, room="depot")
        
    # Animate bus in simulator
    stop_id_str = str(req_doc["stop"]["id"] if isinstance(req_doc["stop"], dict) else req_doc["stop"])
    await dispatch_bus_to_stop(stop_id_str)
    
    return {"message": "Bus dispatched and passenger notified", "request": req_data}

@router.patch("/send-all")
async def send_all(
    body: Dict[str, Any],
    request: FastAPIRequest,
    user: dict = Depends(auth_middleware(["depot", "admin"]))
):
    db = get_db()
    sio = request.app.state.sio
    
    stop_id = body.get("stopId")
    route_id = body.get("routeId")
    
    if not stop_id or not route_id:
        raise HTTPException(status_code=400, detail="stopId and routeId required")
        
    pending = await db.requests.find({
        "stop": ObjectId(stop_id),
        "route": ObjectId(route_id),
        "status": "pending"
    }).to_list(None)
    
    if not pending:
        raise HTTPException(status_code=404, detail="No pending requests found")
        
    sent_at = datetime.utcnow()
    await db.requests.update_many(
        {
            "stop": ObjectId(stop_id),
            "route": ObjectId(route_id),
            "status": "pending"
        },
        {"$set": {
            "status": "sent",
            "sentAt": sent_at,
            "updatedAt": sent_at
        }}
    )
    
    # Populate to notify waiting passengers
    populated = await populate_requests(pending, db)
    serialized_requests = [serialize_doc(r) for r in populated]
    
    if sio:
        for r in serialized_requests:
            p_id = str(r["passenger"]["id"] if isinstance(r["passenger"], dict) else r["passenger"])
            await sio.emit("bus-sent", {
                "requestId": r["id"],
                "message": "Bus is on the way! 🚌",
                "route": r["route"],
                "stop": r["stop"]
            }, room=f"passenger:{p_id}")
            
    # Dispatch simulator bus
    await dispatch_bus_to_stop(stop_id)
    
    if sio:
        await sio.emit("bulk-updated", {
            "stopId": stop_id,
            "routeId": route_id,
            "count": len(pending)
        }, room="depot")
        
    return {"message": f"Bus dispatched for {len(pending)} passenger(s)", "count": len(pending)}
