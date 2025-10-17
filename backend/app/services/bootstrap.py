from __future__ import annotations
import os
import stat
from typing import Tuple, Optional
import httpx
import shutil
import subprocess
import tempfile
from ..config import settings


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def _download(url: str, dest: str) -> Tuple[bool, str]:
    _ensure_dir(dest)
    try:
        with httpx.Client(follow_redirects=True, timeout=300) as client:
            with client.stream("GET", url) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
        return True, "downloaded"
    except Exception as e:
        return False, str(e)


def ensure_whisper_model() -> Tuple[bool, str]:
    model_path = settings.whisper_model_path
    if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
        return True, "exists"
    url = settings.whisper_model_url
    if not url:
        return False, "WHISPER_MODEL_URL not set; cannot auto-download"
    ok, msg = _download(url, model_path)
    return ok, msg


def ensure_whisper_binary() -> Tuple[bool, str]:
    bin_path = settings.whisper_binary_path
    if os.path.exists(bin_path) and os.access(bin_path, os.X_OK):
        return True, "exists"
    # Try to locate in PATH under common names
    # Only consider known whisper.cpp binary names, not generic 'whisper' (python CLI)
    for name in ("whisper.cpp", "whisper-cpp", "main"):
        found = shutil.which(name)
        if found and os.access(found, os.X_OK):
            # Optionally copy into configured path for stability
            try:
                if os.path.abspath(found) != os.path.abspath(bin_path):
                    _ensure_dir(bin_path)
                    shutil.copy2(found, bin_path)
                    st = os.stat(bin_path)
                    os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
                return True, f"found: {found}"
            except Exception:
                return True, f"found in PATH: {found}"
    url = settings.whisper_bin_url
    if not url:
        return False, "WHISPER_BIN_URL not set; cannot auto-download CLI"
    ok, msg = _download(url, bin_path)
    if ok:
        # chmod +x
        st = os.stat(bin_path)
        os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
    return ok, msg


def build_whisper_from_source() -> Tuple[bool, str]:
    """Attempt to build whisper.cpp from source using git+make and install binary."""
    bin_path = settings.whisper_binary_path
    with tempfile.TemporaryDirectory() as td:
        try:
            repo = os.path.join(td, "whisper.cpp")
            subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ggerganov/whisper.cpp", repo], check=True)
            # Build; default make should work on macOS/Linux with Accelerate/BLAS
            subprocess.run(["make"], cwd=repo, check=True)
            candidate = os.path.join(repo, "main")
            if not os.path.exists(candidate):
                return False, "build succeeded but binary not found"
            _ensure_dir(bin_path)
            shutil.copy2(candidate, bin_path)
            st = os.stat(bin_path)
            os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
            return True, "built from source"
        except Exception as e:
            return False, f"build failed: {e}"


def _find_built_binary(root: str) -> Optional[str]:
    # Check common locations/names after CMake or Make builds
    candidates = [
        os.path.join(root, "main"),
        os.path.join(root, "bin", "main"),
        os.path.join(root, "bin", "whisper"),
        os.path.join(root, "bin", "whisper.cpp"),
        os.path.join(root, "bin", "whisper-cpp"),
        os.path.join(root, "whisper"),
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


def build_whisper_from_source() -> Tuple[bool, str]:
    """Attempt to build whisper.cpp from source using CMake; fallback to make; then install binary."""
    bin_path = settings.whisper_binary_path
    with tempfile.TemporaryDirectory() as td:
        try:
            repo = os.path.join(td, "whisper.cpp")
            subprocess.run(["git", "clone", "--depth", "1", "https://github.com/ggerganov/whisper.cpp", repo], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Prefer CMake
            built = False
            try:
                build_dir = os.path.join(repo, "build")
                os.makedirs(build_dir, exist_ok=True)
                subprocess.run(["cmake", "-S", repo, "-B", build_dir, "-DCMAKE_BUILD_TYPE=Release"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["cmake", "--build", build_dir, "-j"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                candidate = _find_built_binary(build_dir)
                if candidate:
                    _ensure_dir(bin_path)
                    shutil.copy2(candidate, bin_path)
                    st = os.stat(bin_path)
                    os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
                    built = True
            except Exception:
                built = False
            if not built:
                # Fallback to legacy make
                subprocess.run(["make"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                candidate = _find_built_binary(repo)
                if not candidate:
                    # Last resort: assume repo/main
                    candidate = os.path.join(repo, "main")
                if not (os.path.exists(candidate) and os.access(candidate, os.X_OK)):
                    return False, "build succeeded but binary not found"
                _ensure_dir(bin_path)
                shutil.copy2(candidate, bin_path)
                st = os.stat(bin_path)
                os.chmod(bin_path, st.st_mode | stat.S_IEXEC)
            return True, "built from source"
        except Exception as e:
            return False, f"build failed: {e}"


def ensure_whisper_ready() -> Tuple[bool, dict]:
    # Binary
    b_ok, b_msg = ensure_whisper_binary()
    if not b_ok:
        # If no URL or PATH match, attempt to build from source automatically
        built_ok, built_msg = build_whisper_from_source()
        if built_ok:
            b_ok, b_msg = True, built_msg
        else:
            b_ok, b_msg = False, f"{b_msg}; build_attempt: {built_msg}"
    # Model
    m_ok, m_msg = ensure_whisper_model()
    ok = b_ok and m_ok
    return ok, {"binary": {"ok": b_ok, "msg": b_msg}, "model": {"ok": m_ok, "msg": m_msg}}
