from __future__ import annotations
from fastapi import APIRouter, HTTPException
import os
from fastapi.responses import FileResponse


router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/download")
def download(path: str):
    # Caution: in a real app, validate and authorize path access strictly
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path)

