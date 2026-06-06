# Stage 1: build Next.js static export
# NEXT_PUBLIC_API_BASE="" → all API calls use relative paths, so the app
# works whether served from the FastAPI backend (local/Docker) or Firebase Hosting.
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN NEXT_PUBLIC_API_BASE="" WEB_EXPORT=1 npm run build

# Stage 2: Python backend
FROM python:3.11-slim

WORKDIR /app

# Install deps first so this layer is cached across code changes.
# The hosted image includes the Arize observability extras; the lean offline
# desktop bundle omits them (tracing degrades to a no-op — see ai/tracing.py).
COPY backend/requirements.txt ./backend/requirements.txt
COPY backend/requirements-observability.txt ./backend/requirements-observability.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && pip install --no-cache-dir -r backend/requirements-observability.txt

# Copy source (alembic.ini lives at repo root)
COPY alembic.ini .
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Embed the built frontend — backend serves it when running locally / in Docker
COPY --from=frontend-build /frontend/out ./frontend_out

# Persistent data volume mount point
RUN mkdir -p /data/uploads

ENV VESSEL_OPS_DATA_DIR=/data

EXPOSE 8080

CMD ["python", "-m", "backend.web_entrypoint"]
