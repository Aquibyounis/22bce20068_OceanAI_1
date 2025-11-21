# Backend/config.py
from pathlib import Path

# Root directory where all project folders live (absolute to avoid cwd issues)
PROJECT_ROOT = (Path.cwd() / "ProjectData").resolve()

# Chunking config
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200

# Embedding model
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
