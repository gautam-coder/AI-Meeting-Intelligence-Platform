import re


def safe_filename(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9._-]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "file"


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

