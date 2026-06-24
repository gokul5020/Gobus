import motor.motor_asyncio
import asyncio
import sys
from config import MONGO_URI

client = None
db = None

async def connect_db():
    global client, db
    print("🔌 Connecting to MongoDB...")
    
    # Try env MONGO_URI
    if MONGO_URI:
        try:
            client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            await client.admin.command('ping')
            db = client.get_default_database()
            print("✅ Connected to MongoDB Atlas/Env Database")
            return
        except Exception as e:
            print(f"⚠️  Could not connect to database specified in .env: {e}")
            
    # Try local MongoDB fallback
    print("ℹ️  Attempting to connect to local MongoDB on localhost:27017...")
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/smart_bus", serverSelectionTimeoutMS=3000)
        await client.admin.command('ping')
        db = client["smart_bus"]
        print("✅ Connected to local MongoDB instance on localhost:27017")
    except Exception as e:
        print(f"❌  Failed to connect to local MongoDB: {e}")
        print("🔴  Database connection failed. Please check your connection or run a local MongoDB instance.")
        # Fall back to an un-pinged local client so routes don't throw NameError immediately
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/smart_bus")
        db = client["smart_bus"]

def get_db():
    global db
    return db
