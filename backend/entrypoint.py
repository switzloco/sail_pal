"""PyInstaller entrypoint for the bundled backend.

Launches uvicorn against `backend.main:app` on port 8000. When frozen by
PyInstaller, relative data paths are resolved against the executable's
directory so the SQLite DB and uploads land next to the binary rather
than in a read-only app bundle location.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _resolve_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller --onefile: use the user's application-support dir so
        # writes survive app updates and bundle re-mounts.
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "VesselOpsAI"
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", str(Path.home()))) / "VesselOpsAI"
        else:
            base = Path.home() / ".local" / "share" / "VesselOpsAI"
    else:
        base = Path(__file__).resolve().parent / "data"
    base.mkdir(parents=True, exist_ok=True)
    (base / "uploads").mkdir(parents=True, exist_ok=True)
    return base


def main() -> None:
    data_dir = _resolve_data_dir()
    os.environ.setdefault("VESSEL_OPS_DATA_DIR", str(data_dir))
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{data_dir / 'vessel_ops.db'}")

    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("VESSEL_OPS_PORT", "8000")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
