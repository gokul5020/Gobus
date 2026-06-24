# Single-service image: build the Vite frontend, then serve it from FastAPI.
# Result: one URL hosts both the React app and the /api + socket.io backend.

# ── Stage 1: build the React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build          # outputs /fe/dist

# ── Stage 2: Python backend that serves the built frontend ───────────────────
FROM python:3.12-slim
WORKDIR /app
COPY backend_python/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend_python/ ./
# Place the built SPA where main.py serves it from (backend_python/static)
COPY --from=frontend /fe/dist ./static
EXPOSE 10000
CMD ["sh", "-c", "uvicorn main:sio_app --host 0.0.0.0 --port ${PORT:-10000}"]
