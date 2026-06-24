"""Route endpoint tests, including the stop-based boarding filter."""
import pytest


async def test_get_routes_populates_stops(client, seed_route):
    resp = await client.get("/api/routes")
    assert resp.status_code == 200
    routes = resp.json()
    assert len(routes) == 1
    stops = routes[0]["stops"]
    assert [s["name"] for s in stops] == ["Alpha", "Bravo", "Charlie"]


async def test_filter_by_start_stop_includes_route(client, seed_route):
    start = seed_route["stop_ids"][0]            # Alpha
    resp = await client.get("/api/routes", params={"stopId": start})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_filter_by_intermediate_stop_includes_route(client, seed_route):
    mid = seed_route["stop_ids"][1]              # Bravo
    resp = await client.get("/api/routes", params={"stopId": mid})
    assert len(resp.json()) == 1


async def test_filter_by_terminus_excludes_route(client, seed_route):
    """A bus that ENDS at the selected stop must not be offered for boarding."""
    terminus = seed_route["stop_ids"][2]         # Charlie (last stop)
    resp = await client.get("/api/routes", params={"stopId": terminus})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_route_by_id(client, seed_route):
    resp = await client.get(f"/api/routes/{seed_route['route_id']}")
    assert resp.status_code == 200
    assert resp.json()["routeNumber"] == "T1"


async def test_get_route_invalid_id(client):
    resp = await client.get("/api/routes/xyz")
    assert resp.status_code == 400


async def test_search_routes(client, seed_route):
    resp = await client.get("/api/routes/search", params={"q": "Alpha"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_inactive_route_hidden_from_public(client, mock_db, seed_route):
    await mock_db.busroutes.update_one(
        {"routeNumber": "T1"}, {"$set": {"isActive": False}}
    )
    resp = await client.get("/api/routes")
    assert resp.json() == []
