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

# ── Email (OTP delivery via SMTP, e.g. Gmail) ────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "SmartBus")

# Brevo HTTP email API key (works where SMTP is blocked, e.g. Render free tier).
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
