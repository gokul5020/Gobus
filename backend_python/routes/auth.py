import re
import random
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
    
    # Upsert passenger
    passenger = await db.passengers.find_one({"mobile": mobile})
    if not passenger:
        passenger = {
            "mobile": mobile,
            "otpCode": otp,
            "otpExpiry": expiry,
            "isVerified": False,
            "name": "",
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        await db.passengers.insert_one(passenger)
    else:
        await db.passengers.update_one(
            {"_id": passenger["_id"]},
            {"$set": {
                "otpCode": otp,
                "otpExpiry": expiry,
                "updatedAt": datetime.utcnow()
            }}
        )
        
    logger.info("=" * 50)
    logger.info(f"OTP for {mobile}: {otp}  (valid for {OTP_EXPIRY_MINUTES} minutes)")
    logger.info("=" * 50)
    return {"message": "OTP sent successfully", "mobile": mobile}

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
