"""Bus-stop endpoint tests."""
import pytest


async def test_get_stops_sorted(client, seed_route):
    resp = await client.get("/api/stops")
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert names == sorted(names)              # endpoint sorts by name
    assert {"Alpha", "Bravo", "Charlie"} <= set(names)


async def test_search_stops(client, seed_route):
    resp = await client.get("/api/stops/search", params={"q": "brav"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["name"] == "Bravo"


async def test_get_stop_by_id(client, seed_route):
    stop_id = seed_route["stop_ids"][0]
    resp = await client.get(f"/api/stops/{stop_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alpha"


async def test_get_stop_invalid_id(client):
    resp = await client.get("/api/stops/not-an-objectid")
    assert resp.status_code == 400


async def test_create_stop_requires_auth(client):
    resp = await client.post("/api/stops", json={"name": "X", "lat": 1, "lng": 2})
    assert resp.status_code == 401


async def test_create_stop_as_admin(client, admin_headers, mock_db):
    resp = await client.post(
        "/api/stops",
        json={"name": "NewStop", "lat": 13.0, "lng": 80.2},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "NewStop"
    assert await mock_db.busstops.find_one({"name": "NewStop"}) is not None


async def test_create_stop_duplicate_name(client, admin_headers, seed_route):
    resp = await client.post(
        "/api/stops",
        json={"name": "Alpha", "lat": 1, "lng": 2},
        headers=admin_headers,
    )
    assert resp.status_code == 400
