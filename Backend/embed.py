# Backend/embed.py
from pathlib import Path
from typing import List, Optional, Dict, Any

from Backend.utils import ensure_project_dirs, make_project_id, file_hash, build_metadata
from Backend.parsers import extract_text
from Backend.chunker import split_text
from Backend.embeddings import embed_texts
from Backend.vectorstore import upsert_chunks
from Backend.config import CHUNK_SIZE, CHUNK_OVERLAP


def create_project_and_ingest(uploaded_files: List[Path], checkout_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Save uploaded files into per-project uploads/, chunk, embed, and upsert into per-project chroma/.
    Returns a summary dict with project_id, files and total_chunks.
    """
    project_id = make_project_id()
    dirs = ensure_project_dirs(project_id)
    uploads_dir = dirs["uploads"]
    chroma_dir = dirs["chroma"]

    summary = {"project_id": project_id, "files": [], "total_chunks": 0}

    # save uploaded files into project uploads and remember saved paths
    saved_paths: List[Path] = []
    for f in uploaded_files:
        dest = uploads_dir / f.name
        dest.write_bytes(f.read_bytes())
        saved_paths.append(dest)

    # process each saved file (use current split_text(text) API)
    for p in saved_paths:
        text = extract_text(str(p))
        if not text or not text.strip():
            summary["files"].append({"file": p.name, "chunks": 0})
            continue

        # NOTE: split_text currently expects only the text argument.
        # If you later change chunker to accept CHUNK_SIZE/CHUNK_OVERLAP, update this call.
        chunks = split_text(text)

        if not chunks:
            summary["files"].append({"file": p.name, "chunks": 0})
            continue

        try:
            embeddings = embed_texts(chunks)
        except Exception as e:
            return {"error": "embedding_failed", "file": p.name, "detail": str(e)}

        fh = file_hash(p)

        ids: List[str] = []
        metas: List[dict] = []
        for i, _ in enumerate(chunks):
            uid = f"{project_id}::{p.name}::{fh}::chunk_{i}"
            ids.append(uid)
            metas.append(build_metadata(
                project_id=project_id,
                source_document=p.name,
                file_type=p.suffix.lower().lstrip("."),
                file_hash_str=fh,
                chunk_id=i
            ))

        # Upsert only if we have ids + embeddings
        if ids and embeddings:
            upsert_chunks(chroma_dir, ids, chunks, metas, embeddings)

        summary["files"].append({"file": p.name, "chunks": len(chunks)})
        summary["total_chunks"] += len(chunks)

    # optional checkout.html (if provided separately)
    if checkout_path and checkout_path.exists():
        dest = uploads_dir / "checkout.html"
        dest.write_bytes(checkout_path.read_bytes())

        text = extract_text(str(dest))
        if text and text.strip():
            # use same split_text() API here
            chunks = split_text(text)
            if chunks:
                try:
                    embeddings = embed_texts(chunks)
                except Exception as e:
                    return {"error": "embedding_failed", "file": dest.name, "detail": str(e)}

                fh = file_hash(dest)
                ids = []
                metas = []
                for i, _ in enumerate(chunks):
                    uid = f"{project_id}::{dest.name}::{fh}::chunk_{i}"
                    ids.append(uid)
                    metas.append(build_metadata(
                        project_id=project_id,
                        source_document=dest.name,
                        file_type="html",
                        file_hash_str=fh,
                        chunk_id=i
                    ))

                if ids and embeddings:
                    upsert_chunks(chroma_dir, ids, chunks, metas, embeddings)

                summary["files"].append({"file": dest.name, "chunks": len(chunks)})
                summary["total_chunks"] += len(chunks)
        else:
            summary["files"].append({"file": dest.name, "chunks": 0})

    return summary
