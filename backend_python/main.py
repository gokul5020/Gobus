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
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
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

# Global HTTPException handler to map to standard {"message": ...} expected by the React frontend
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        content = exc.detail
        if "message" not in content and "detail" in content:
            content["message"] = content["detail"]
        elif "message" not in content:
            content["message"] = str(content)
        return JSONResponse(status_code=exc.status_code, content=content)
    else:
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.detail}
        )

# Add CORS Middleware.
# Local dev origins plus any extra origins from FRONTEND_URL (comma-separated),
# and any *.onrender.com host (covers the deployed Render static site).
import os as _os
_cors_origins = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5174',
    'http://localhost:5175',
]
_extra = _os.getenv("FRONTEND_URL", "")
_cors_origins += [o.strip() for o in _extra.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
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

# ── Serve the built React frontend (single-service deployment) ───────────────
# In Docker the Vite build is copied to backend_python/static. When present,
# serve its assets and fall back to index.html for client-side routes so the
# whole app lives behind one URL.
import os
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.is_dir():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Let unmatched API calls 404 instead of returning the SPA shell.
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"message": "Not found"})
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")

# Combine FastAPI and Socket.io using ASGIApp
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    uvicorn.run("main:sio_app", host="0.0.0.0", port=PORT, reload=True, log_level="info")
