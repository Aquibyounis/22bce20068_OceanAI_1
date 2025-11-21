# Backend/utils.py
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any

from Backend.config import PROJECT_ROOT

def make_project_id() -> str:
    """Generate a simple timestamp-based project id."""
    return f"proj_{int(time.time())}"

def file_hash(path: Path) -> str:
    """Return a short sha256 hash of file bytes."""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()[:12]

def ensure_project_dirs(project_id: str) -> Dict[str, Path]:
    """
    Create and return paths for a project:
    ProjectData/proj_<ID>/uploads and ProjectData/proj_<ID>/chroma
    """
    base = PROJECT_ROOT / project_id
    uploads = base / "uploads"
    chroma = base / "chroma"

    uploads.mkdir(parents=True, exist_ok=True)
    chroma.mkdir(parents=True, exist_ok=True)

    return {"base": base, "uploads": uploads, "chroma": chroma}

def build_metadata(project_id: str,
                   source_document: str,
                   file_type: str,
                   file_hash_str: str,
                   chunk_id: int,
                   page: Optional[int] = None) -> Dict[str, Any]:
    """Standard metadata for each stored chunk."""
    return {
        "project_id": project_id,
        "source_document": source_document,
        "file_type": file_type,
        "file_hash": file_hash_str,
        "chunk_id": int(chunk_id),
        "page": page,
        "ingest_ts": int(time.time())
    }
