import os
from pathlib import Path
from dotenv import load_dotenv

# Load the .env that lives alongside this backend.
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

PORT = int(os.getenv("PORT", 5000))
MONGO_URI = os.getenv("MONGO_URI", "")
JWT_SECRET = os.getenv("JWT_SECRET", "smartbus_super_secret_jwt_key_2024")
JWT_EXPIRES_IN = os.getenv("JWT_EXPIRES_IN", "7d")
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", 5))
