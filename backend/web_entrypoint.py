"""Web deployment entrypoint (Railway / any PaaS).

Distinct from entrypoint.py (PyInstaller desktop) — this one:
 - Listens on 0.0.0.0:$PORT (Railway injects PORT)
 - Runs Alembic migrations before starting
 - Auto-seeds demo data if the DB is empty (so judges see MV Resolute on first visit)
 - Never touches sys._MEIPASS or frozen-binary paths
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _ensure_data_dir() -> Path:
    data_dir = Path(os.environ.get("VESSEL_OPS_DATA_DIR", "/data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "uploads").mkdir(exist_ok=True)
    return data_dir


def _run_migrations() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError("Alembic upgrade failed")
    print(result.stdout or "✓ Migrations up to date.")


def _auto_seed() -> None:
    from backend.db.database import SessionLocal
    from backend.db.models import Vessel

    db = SessionLocal()
    try:
        if db.query(Vessel).first():
            print("✓ DB already seeded — skipping.")
            return
    finally:
        db.close()

    print("Seeding demo data (MV Resolute)…")
    from scripts.seed import seed
    seed()


def main() -> None:
    data_dir = _ensure_data_dir()
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{data_dir}/vessel.db")

    _run_migrations()
    _auto_seed()

    import uvicorn
    from backend.main import app

    port = int(os.environ.get("PORT", "8080"))
    print(f"Starting Vessel Ops AI on 0.0.0.0:{port}...")
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
