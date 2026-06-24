"""Bus-request flow tests."""
import pytest


async def _make_request(client, headers, route_id, stop_id):
    return await client.post(
        "/api/requests", json={"routeId": route_id, "stopId": stop_id}, headers=headers
    )


async def test_create_request(client, passenger, seed_route):
    resp = await _make_request(
        client, passenger["headers"], seed_route["route_id"], seed_route["stop_ids"][0]
    )
    assert resp.status_code == 201
    assert resp.json()["request"]["status"] == "pending"


async def test_create_request_requires_passenger_role(client, admin_headers, seed_route):
    resp = await client.post(
        "/api/requests",
        json={"routeId": seed_route["route_id"], "stopId": seed_route["stop_ids"][0]},
        headers=admin_headers,
    )
    assert resp.status_code == 403


async def test_duplicate_active_request_conflicts(client, passenger, seed_route):
    first = await _make_request(
        client, passenger["headers"], seed_route["route_id"], seed_route["stop_ids"][0]
    )
    assert first.status_code == 201
    second = await _make_request(
        client, passenger["headers"], seed_route["route_id"], seed_route["stop_ids"][0]
    )
    assert second.status_code == 409


async def test_depot_lists_and_groups_requests(client, passenger, depot_headers, seed_route):
    await _make_request(
        client, passenger["headers"], seed_route["route_id"], seed_route["stop_ids"][0]
    )
    resp = await client.get("/api/requests", headers=depot_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["requests"]) == 1
    assert len(body["grouped"]) == 1
    assert body["grouped"][0]["count"] == 1


async def test_send_bus_marks_request_sent(client, passenger, depot_headers, seed_route, mock_db):
    created = await _make_request(
        client, passenger["headers"], seed_route["route_id"], seed_route["stop_ids"][0]
    )
    req_id = created.json()["request"]["id"]
    resp = await client.patch(f"/api/requests/{req_id}/send-bus", headers=depot_headers)
    assert resp.status_code == 200
    assert resp.json()["request"]["status"] == "sent"


async def test_requests_endpoint_requires_staff(client, passenger):
    resp = await client.get("/api/requests", headers=passenger["headers"])
    assert resp.status_code == 403
