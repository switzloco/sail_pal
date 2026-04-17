# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Vessel Ops AI backend sidecar.
#
# Build with:
#   pyinstaller backend/pyinstaller.spec --clean
#
# Output: dist/vessel-ops-backend(.exe). The GitHub Actions release workflow
# renames this with the Rust target triple suffix Tauri expects, e.g.
# `vessel-ops-backend-aarch64-apple-darwin`.

from PyInstaller.utils.hooks import collect_all, collect_submodules

hiddenimports = []
datas = []
binaries = []

# FastAPI / Uvicorn and the ecosystems they pull in at runtime.
for pkg in (
    "uvicorn",
    "fastapi",
    "pydantic",
    "pydantic_settings",
    "sqlalchemy",
    "alembic",
    "ollama",
    "httpx",
):
    _b, _d, _h = collect_all(pkg)
    binaries += _b
    datas += _d
    hiddenimports += _h

# Our own backend package — make sure every router/model module is picked up.
hiddenimports += collect_submodules("backend")

# Alembic migration scripts live outside the backend package — bundle them.
datas += [("alembic", "alembic"), ("alembic.ini", ".")]


a = Analysis(
    ["backend/entrypoint.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "pandas",
        "torch",
        "transformers",
        "sentence_transformers",
        "chromadb",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="vessel-ops-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
