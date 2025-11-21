# Backend/vectorstore.py
"""
Chroma wrapper compatible with multiple chromadb versions.

Tries:
- chromadb.PersistentClient (newer)
- chromadb.Client(Settings(...)) (older)
- chromadb.Client() fallback
"""

from pathlib import Path
from typing import List, Dict, Any
import logging

try:
    import chromadb
    from chromadb.config import Settings
except Exception as e:
    raise RuntimeError("chromadb import failed: " + str(e)) from e

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _make_client(project_chroma_dir: Path):
    project_chroma_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Initializing chroma client for dir: %s", project_chroma_dir)

    # 1) Try PersistentClient (newer API)
    try:
        PersistentClient = getattr(chromadb, "PersistentClient", None)
        if PersistentClient is not None:
            client = PersistentClient(path=str(project_chroma_dir))
            try:
                col = client.get_collection("docs")
            except Exception:
                col = client.create_collection("docs")
            return client, col
    except Exception:
        pass

    # 2) Try Client with Settings (many versions support this)
    try:
        client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=str(project_chroma_dir)))
        try:
            col = client.get_collection("docs")
        except Exception:
            col = client.create_collection("docs")
        return client, col
    except Exception:
        pass

    # 3) Fallback: plain Client()
    try:
        client = chromadb.Client()
        try:
            col = client.get_collection("docs")
        except Exception:
            col = client.create_collection("docs")
        return client, col
    except Exception as exc:
        raise RuntimeError(f"Failed to initialize chromadb client for {project_chroma_dir}: {exc}") from exc


def upsert_chunks(project_chroma_dir: Path,
                  ids: List[str],
                  texts: List[str],
                  metas: List[Dict[str, Any]],
                  embeddings: List[Any]):
    client, col = _make_client(project_chroma_dir)
    col.upsert(ids=ids, documents=texts, metadatas=metas, embeddings=embeddings)
    # attempt to persist if supported
    try:
        if hasattr(client, "persist"):
            client.persist()
    except Exception:
        pass


def list_chunks(project_chroma_dir: Path, limit: int = 20):
    client, col = _make_client(project_chroma_dir)
    try:
        data = col.get()
    except Exception:
        try:
            data = col.get(include=["ids", "documents", "metadatas"])
        except Exception:
            return []
    ids = data.get("ids", [])
    docs = data.get("documents", [])
    metas = data.get("metadatas", [])
    out = []
    for i, (id_, doc, meta) in enumerate(zip(ids, docs, metas)):
        if i >= limit:
            break
        out.append({"id": id_, "text": (doc[:400] if isinstance(doc, str) else str(doc)), "metadata": meta})
    logger.info("list_chunks: returning %d items from %s", len(out), project_chroma_dir)
    return out
