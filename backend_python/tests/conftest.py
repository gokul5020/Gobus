"""
Shared pytest fixtures for the backend test suite.

The tests run fully offline: a mongomock-motor in-memory database is patched
into `database.db`, and a FastAPI app is assembled directly from the routers
(bypassing main.py's stdout wrapping and the real MongoDB-Atlas lifespan).
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import bcrypt
import pytest
import pytest_asyncio
from bson import ObjectId
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient

# Make the backend package importable when pytest is run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database
from routes.auth import router as auth_router, create_jwt_token
from routes.stops import router as stops_router
from routes.routes import router as routes_router
from routes.requests import router as requests_router


@pytest.fixture
def mock_db():
    """Fresh in-memory database patched into the app's get_db() source."""
    client = AsyncMongoMockClient()
    db = client["smart_bus_test"]
    database.client = client
    database.db = db
    yield db
    database.client = None
    database.db = None


@pytest_asyncio.fixture
async def client(mock_db):
    """httpx AsyncClient bound to an app built from the real routers."""
    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(stops_router)
    app.include_router(routes_router)
    app.include_router(requests_router)
    app.state.sio = AsyncMock()          # stub socket.io – emits become no-ops
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── auth helpers ─────────────────────────────────────────────────────────────
def admin_token(admin_id="0123456789abcdef01234567"):
    return create_jwt_token({"id": admin_id, "username": "admin", "role": "admin"})


def passenger_token(passenger_id):
    return create_jwt_token(
        {"id": passenger_id, "mobile": "9999999999", "role": "passenger"}
    )


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {admin_token()}"}


@pytest.fixture
def passenger():
    """A valid passenger id (24-hex) + auth headers for request tests."""
    pid = str(ObjectId())
    return {"id": pid, "headers": {"Authorization": f"Bearer {passenger_token(pid)}"}}


@pytest.fixture
def depot_headers():
    token = create_jwt_token({"id": str(ObjectId()), "username": "depot", "role": "depot"})
    return {"Authorization": f"Bearer {token}"}


# ── seeding helpers ──────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def seed_admin(mock_db):
    pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt(10)).decode("utf-8")
    await mock_db.admins.insert_one(
        {"name": "System Admin", "username": "admin", "password": pw, "role": "admin"}
    )


@pytest_asyncio.fixture
async def seed_route(mock_db):
    """Insert 3 stops A->B->C and one active route through them.

    Returns the stop ids (str) and the route id (str). C is the terminus.
    """
    stops = []
    for name, lat, lng in [("Alpha", 13.01, 80.21), ("Bravo", 13.02, 80.22),
                           ("Charlie", 13.03, 80.23)]:
        res = await mock_db.busstops.insert_one(
            {"name": name, "lat": lat, "lng": lng, "address": f"{name}, Chennai"}
        )
        stops.append(res.inserted_id)
    route = await mock_db.busroutes.insert_one(
        {
            "routeNumber": "T1",
            "busName": "Alpha to Charlie",
            "busDetails": "T1 : Alpha to Charlie",
            "stops": stops,
            "alternateStops": {},
            "description": "test route",
            "isActive": True,
        }
    )
    return {
        "stop_ids": [str(s) for s in stops],
        "route_id": str(route.inserted_id),
    }
