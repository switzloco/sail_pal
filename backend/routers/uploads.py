import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import APIRouter, File, UploadFile, HTTPException

router = APIRouter()

UPLOAD_DIR = Path("backend/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload one or more files and return their saved paths."""
    saved_paths = []
    for file in files:
        if not file.filename:
            continue
        
        # Generate a unique filename to avoid collisions
        ext = Path(file.filename).suffix
        filename = f"{uuid.uuid4()}{ext}"
        dest = UPLOAD_DIR / filename
        
        try:
            with dest.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file {file.filename}: {str(e)}")
            
    return {"paths": saved_paths}
