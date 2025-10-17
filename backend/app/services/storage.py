from __future__ import annotations
import os
import shutil
from typing import Tuple
from ..config import settings
from ..utils.text import safe_filename


def uploads_dir() -> str:
    p = os.path.join(settings.data_dir, "uploads")
    os.makedirs(p, exist_ok=True)
    return p


def artifacts_dir() -> str:
    p = os.path.join(settings.data_dir, "artifacts")
    os.makedirs(p, exist_ok=True)
    return p


def save_upload(temp_path: str, original_name: str) -> Tuple[str, int]:
    name = safe_filename(original_name)
    dest = os.path.join(uploads_dir(), name)
    # Avoid overwrite by appending counter
    base, ext = os.path.splitext(dest)
    i = 1
    while os.path.exists(dest):
        dest = f"{base}-{i}{ext}"
        i += 1
    shutil.move(temp_path, dest)
    size = os.path.getsize(dest)
    return dest, size


def ensure_exists(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

