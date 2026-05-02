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


def _load_bundled_env() -> None:
    """Populate os.environ from a .env bundled into the frozen app.

    The release workflow writes .env (containing CLOUD_MODE + GOOGLE_API_KEY)
    before PyInstaller runs; the spec bundles it into the one-file archive.
    Pydantic BaseSettings looks for .env relative to cwd and will miss the
    bundled copy, so we hydrate os.environ manually before the app imports.
    """
    if not getattr(sys, "frozen", False):
        return
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if not bundle_dir:
        return
    env_path = Path(bundle_dir) / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


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
    _load_bundled_env()
    data_dir = _resolve_data_dir()
    os.environ.setdefault("VESSEL_OPS_DATA_DIR", str(data_dir))
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{data_dir / 'vessel_ops.db'}")

    # Import the app object directly rather than using the module-path string
    # so PyInstaller picks up the dependency at analysis time and uvicorn
    # doesn't have to resolve it through the frozen importer at runtime.
    import uvicorn
    from backend.main import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("VESSEL_OPS_PORT", "8000")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
