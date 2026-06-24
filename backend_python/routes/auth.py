import re
import random
import asyncio
import logging
from datetime import datetime, timedelta
import jwt
import bcrypt
from fastapi import APIRouter, HTTPException, Depends, status
from bson import ObjectId
from database import get_db
from config import JWT_SECRET, OTP_EXPIRY_MINUTES
from middleware.auth import auth_middleware
from models import PassengerLoginRequest, VerifyOtpRequest, AdminLoginRequest
from email_service import smtp_configured, send_otp_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Log through uvicorn's logger so OTP messages reliably appear in the server
# console (plain print() gets swallowed by uvicorn's stream handling).
logger = logging.getLogger("uvicorn.error")

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

def create_jwt_token(payload: dict) -> str:
    expiry = datetime.utcnow() + timedelta(days=7)
    jwt_payload = payload.copy()
    jwt_payload["exp"] = expiry
    return jwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")

@router.post("/send-otp")
async def send_otp(body: PassengerLoginRequest):
    db = get_db()
    mobile = body.mobile
    if not mobile or not re.match(r"^[0-9]{10}$", mobile):
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit mobile number")
        
    otp = generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    email = (body.email or "").strip() or None

    # Upsert passenger (store email so we know where to deliver / resend the OTP)
    passenger = await db.passengers.find_one({"mobile": mobile})
    if not passenger:
        await db.passengers.insert_one({
            "mobile": mobile,
            "email": email,
            "otpCode": otp,
            "otpExpiry": expiry,
            "isVerified": False,
            "name": "",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        })
    else:
        update = {"otpCode": otp, "otpExpiry": expiry, "updatedAt": datetime.utcnow()}
        if email:
            update["email"] = email
        await db.passengers.update_one({"_id": passenger["_id"]}, {"$set": update})
        email = email or passenger.get("email")

    # Always log to the server console (development fallback)
    logger.info("=" * 50)
    logger.info(f"OTP for {mobile}: {otp}  (valid for {OTP_EXPIRY_MINUTES} minutes)")
    logger.info("=" * 50)

    # Deliver by email when an address is available and SMTP is configured.
    emailed = False
    if email and smtp_configured():
        try:
            await asyncio.to_thread(send_otp_email, email, otp)
            emailed = True
            logger.info(f"OTP emailed to {email}")
        except Exception as e:
            logger.warning(f"Failed to email OTP to {email}: {e}")

    return {"message": "OTP sent successfully", "mobile": mobile, "emailed": emailed}

@router.post("/verify-otp")
async def verify_otp(body: VerifyOtpRequest):
    db = get_db()
    passenger = await db.passengers.find_one({"mobile": body.mobile})
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found. Please send OTP first.")
        
    otp_code = passenger.get("otpCode")
    otp_expiry = passenger.get("otpExpiry")
    
    if not otp_code or otp_code != body.otp or not otp_expiry or otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    await db.passengers.update_one(
        {"_id": passenger["_id"]},
        {
            "$set": {"isVerified": True, "updatedAt": datetime.utcnow()},
            "$unset": {"otpCode": "", "otpExpiry": ""}
        }
    )
    
    passenger_id = str(passenger["_id"])
    token = create_jwt_token({
        "id": passenger_id,
        "mobile": passenger["mobile"],
        "role": "passenger"
    })
    
    return {
        "message": "Login successful",
        "token": token,
        "passenger": {
            "id": passenger_id,
            "mobile": passenger["mobile"]
        }
    }

@router.post("/admin-login")
async def admin_login(body: AdminLoginRequest):
    db = get_db()
    admin = await db.admins.find_one({"username": body.username})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    hashed_pw = admin["password"].encode('utf-8')
    if not bcrypt.checkpw(body.password.encode('utf-8'), hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    admin_id = str(admin["_id"])
    token = create_jwt_token({
        "id": admin_id,
        "username": admin["username"],
        "role": admin["role"]
    })
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": admin_id,
            "name": admin["name"],
            "username": admin["username"],
            "role": admin["role"]
        }
    }

@router.get("/me")
async def get_me(user: dict = Depends(auth_middleware(["passenger", "admin", "depot"]))):
    return {"user": user}
