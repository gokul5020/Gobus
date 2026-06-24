import asyncio
import random
import math
from bson import ObjectId
from database import get_db

ENHANCED_SPEED = 0.0004

simulated_buses = [
    {
        "id": f"BUS-{i + 101}",
        "name": f"TN01 {random.randint(1000, 9999)}",
        "lat": 13.05 + (random.random() * 0.06),
        "lng": 80.21 + (random.random() * 0.06),
        "targetLat": None,
        "targetLng": None,
        "speed": 0.0001 + (random.random() * 0.0001),
        "angle": random.random() * math.pi * 2,
        "isDispatched": False
    } for i in range(8)
]

sio_instance = None


def _eta_seconds(bus):
    """Estimated seconds until a dispatched bus reaches its target stop."""
    if bus["targetLat"] is None or bus["targetLng"] is None or bus["speed"] <= 0:
        return None
    dx = bus["targetLat"] - bus["lat"]
    dy = bus["targetLng"] - bus["lng"]
    dist = math.sqrt(dx * dx + dy * dy)
    return max(1, round(dist / bus["speed"]))


async def update_buses():
    global sio_instance
    while True:
        try:
            for bus in simulated_buses:
                if bus["targetLat"] is not None and bus["targetLng"] is not None:
                    dx = bus["targetLat"] - bus["lat"]
                    dy = bus["targetLng"] - bus["lng"]
                    dist = math.sqrt(dx * dx + dy * dy)
                    
                    if dist < bus["speed"]:
                        bus["lat"] = bus["targetLat"]
                        bus["lng"] = bus["targetLng"]
                        bus["targetLat"] = None
                        bus["targetLng"] = None
                        bus["isDispatched"] = False
                        bus["speed"] = 0.0001 + (random.random() * 0.0001)
                    else:
                        bus["lat"] += (dx / dist) * bus["speed"]
                        bus["lng"] += (dy / dist) * bus["speed"]
                else:
                    # Wander randomly in a small area
                    bus["angle"] += (random.random() - 0.5) * 0.5
                    bus["lat"] += math.cos(bus["angle"]) * bus["speed"]
                    bus["lng"] += math.sin(bus["angle"]) * bus["speed"]
            
            if sio_instance:
                await sio_instance.emit('live-buses', [
                    {
                        "id": b["id"],
                        "name": b["name"],
                        "lat": b["lat"],
                        "lng": b["lng"],
                        "isDispatched": b["isDispatched"],
                        "etaSeconds": _eta_seconds(b) if b["isDispatched"] else None,
                    } for b in simulated_buses
                ])
        except Exception as e:
            print("Error in bus simulator loop:", e)
        await asyncio.sleep(1)

def start_simulation(sio):
    global sio_instance
    sio_instance = sio
    asyncio.create_task(update_buses())

async def dispatch_bus_to_stop(stop_id):
    db = get_db()
    if not db:
        return
    try:
        stop = await db.busstops.find_one({"_id": ObjectId(stop_id)})
        if stop and "lat" in stop and "lng" in stop:
            free_bus = next((b for b in simulated_buses if not b["isDispatched"]), None)
            if free_bus:
                free_bus["targetLat"] = stop["lat"]
                free_bus["targetLng"] = stop["lng"]
                free_bus["speed"] = ENHANCED_SPEED
                free_bus["isDispatched"] = True
                print(f"[Simulator] Dispatched {free_bus['name']} to coordinates {stop['lat']}, {stop['lng']}")
    except Exception as e:
        print("Dispatch error in simulator:", e)
