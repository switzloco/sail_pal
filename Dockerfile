FROM python:3.11-slim

WORKDIR /app

# Install deps first so this layer is cached across code changes
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy source (alembic.ini lives at repo root)
COPY alembic.ini .
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Persistent data volume mount point
RUN mkdir -p /data/uploads

ENV VESSEL_OPS_DATA_DIR=/data

EXPOSE 8080

CMD ["python", "-m", "backend.web_entrypoint"]
