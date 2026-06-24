"""Auth + OTP endpoint tests."""
import pytest


async def test_send_otp_valid(client, mock_db):
    resp = await client.post("/api/auth/send-otp", json={"mobile": "9876543210"})
    assert resp.status_code == 200
    assert resp.json()["mobile"] == "9876543210"
    # OTP is generated and stored
    p = await mock_db.passengers.find_one({"mobile": "9876543210"})
    assert p is not None
    assert p["otpCode"] and len(p["otpCode"]) == 6


async def test_send_otp_rejects_bad_mobile(client):
    resp = await client.post("/api/auth/send-otp", json={"mobile": "123"})
    assert resp.status_code == 400


async def test_verify_otp_success_returns_token(client, mock_db):
    await client.post("/api/auth/send-otp", json={"mobile": "9876543210"})
    otp = (await mock_db.passengers.find_one({"mobile": "9876543210"}))["otpCode"]

    resp = await client.post(
        "/api/auth/verify-otp", json={"mobile": "9876543210", "otp": otp}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["passenger"]["mobile"] == "9876543210"
    # OTP is cleared after successful verification
    p = await mock_db.passengers.find_one({"mobile": "9876543210"})
    assert p.get("isVerified") is True
    assert "otpCode" not in p


async def test_verify_otp_wrong_code(client, mock_db):
    await client.post("/api/auth/send-otp", json={"mobile": "9876543210"})
    resp = await client.post(
        "/api/auth/verify-otp", json={"mobile": "9876543210", "otp": "000000"}
    )
    assert resp.status_code == 400


async def test_verify_otp_unknown_passenger(client):
    resp = await client.post(
        "/api/auth/verify-otp", json={"mobile": "9000000000", "otp": "123456"}
    )
    assert resp.status_code == 404


async def test_admin_login_success(client, seed_admin):
    resp = await client.post(
        "/api/auth/admin-login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["user"]["role"] == "admin"


async def test_admin_login_wrong_password(client, seed_admin):
    resp = await client.post(
        "/api/auth/admin-login", json={"username": "admin", "password": "nope"}
    )
    assert resp.status_code == 401


async def test_admin_login_unknown_user(client):
    resp = await client.post(
        "/api/auth/admin-login", json={"username": "ghost", "password": "x"}
    )
    assert resp.status_code == 401
