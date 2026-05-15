# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Vessel Ops AI backend sidecar.
#
# Build from the project root with:
#   pyinstaller backend/pyinstaller.spec --clean --noconfirm
#
# Output: dist/vessel-ops-backend(.exe). The GitHub Actions release workflow
# renames this with the Rust target triple suffix Tauri expects, e.g.
# `vessel-ops-backend-aarch64-apple-darwin`.

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# SPECPATH is provided by PyInstaller and is the absolute path to this spec's
# directory (backend/). Resolve everything against it so the build works no
# matter what cwd pyinstaller is invoked from.
_spec_dir = SPECPATH
_project_root = os.path.dirname(_spec_dir)

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
    "google.genai",
):
    try:
        _b, _d, _h = collect_all(pkg)
        binaries += _b
        datas += _d
        hiddenimports += _h
    except Exception:
        # Package not installed in this environment — skip gracefully.
        pass

# Our own backend package — make sure every router/model module is picked up.
hiddenimports += collect_submodules("backend")

# Alembic migration scripts — bundle conditionally so the spec works before
# migrations have been scaffolded.
_alembic_dir = os.path.join(_project_root, "alembic")
_alembic_ini = os.path.join(_project_root, "alembic.ini")
if os.path.isdir(_alembic_dir):
    datas += [(_alembic_dir, "alembic")]
if os.path.isfile(_alembic_ini):
    datas += [(_alembic_ini, ".")]

# Bundled .env (optional) — release workflow writes one with the cloud preview
# key; in dev the user provides their own.
_env_file = os.path.join(_project_root, ".env")
if os.path.isfile(_env_file):
    datas += [(_env_file, ".")]

# Bundled RAG knowledge chunks (read-only). The FTS5 engine in
# backend/ai/rag_engine.py expects to find these at <bundle>/backend/data/knowledge/
# relative to its own __file__, which PyInstaller resolves under _MEIPASS at
# runtime. Without this datas entry the desktop build ships with an empty RAG
# index and Ask Gemma loses WHO IMGS grounding.
_knowledge_dir = os.path.join(_project_root, "backend", "data", "knowledge")
if os.path.isdir(_knowledge_dir):
    datas += [(_knowledge_dir, os.path.join("backend", "data", "knowledge"))]

# Bundle the WHO IMGS PDF itself so users can browse/print the full manual
# offline at sea. ~2.2 MB, negligible vs the rest of the bundle. The RAG
# engine queries the chunked JSON for speed; this PDF is the source of
# truth users open via the "WHO Manual" button in the UI.
_who_pdf = os.path.join(_project_root, "backend", "data", "manuals", "WHO_IMGS_3rd_Edition.pdf")
if os.path.isfile(_who_pdf):
    datas += [(_who_pdf, os.path.join("backend", "data", "manuals"))]


a = Analysis(
    [os.path.join(_spec_dir, "entrypoint.py")],
    pathex=[_project_root, _spec_dir],
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
