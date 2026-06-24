import sys
import io

# Force standard streams to use UTF-8 on Windows.
# line_buffering=True flushes on every newline so print() output (e.g. the OTP)
# appears immediately in the terminal instead of sitting in a buffer while the
# server keeps running.
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

import socketio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import connect_db
from auto_seed import auto_seed
from bus_simulator import start_simulation
from config import PORT

# Create Socket.io server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Modern FastAPI Lifespan Handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB
    await connect_db()
    # Auto seed initial data if database empty
    await auto_seed()
    # Start bus simulator loop
    start_simulation(sio)
    yield

# Create FastAPI app
app = FastAPI(title="Smart Bus Monitoring API", lifespan=lifespan)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000', 
        'http://localhost:5173', 
        'http://localhost:5174', 
        'http://localhost:5175'
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store sio on app state so it can be used in routes
app.state.sio = sio

# Socket.io Event Handlers
@sio.event
async def connect(sid, environ):
    print(f"[Socket] Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"[Socket] Client disconnected: {sid}")

@sio.on("join-passenger")
async def join_passenger(sid, passengerId):
    await sio.enter_room(sid, f"passenger:{passengerId}")
    print(f"[Socket] Passenger {passengerId} joined personal room")

@sio.on("join-depot")
async def join_depot(sid):
    await sio.enter_room(sid, "depot")
    print(f"[Socket] Depot operator joined")

# Include Routers
from routes.auth import router as auth_router
from routes.stops import router as stops_router
from routes.routes import router as routes_router
from routes.requests import router as requests_router

app.include_router(auth_router)
app.include_router(stops_router)
app.include_router(routes_router)
app.include_router(requests_router)

@app.get("/api/health")
async def health_check():
    from datetime import datetime
    return {"status": "ok", "time": datetime.utcnow()}

# Combine FastAPI and Socket.io using ASGIApp
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    uvicorn.run("main:sio_app", host="0.0.0.0", port=PORT, reload=True, log_level="info")
