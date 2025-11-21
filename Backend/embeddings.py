# Backend/embeddings.py
from typing import List, Union
from sentence_transformers import SentenceTransformer
from Backend.config import EMBED_MODEL_NAME

# Load model (this will download from HF the first time)
model = SentenceTransformer(EMBED_MODEL_NAME)


def _to_list(v):
    """Convert numpy array or nested lists to plain Python lists."""
    try:
        return v.tolist()
    except Exception:
        # If it's already a list or an iterable, coerce to list
        try:
            return list(v)
        except Exception:
            return [v]


def embed_texts(texts: Union[str, List[str]]) -> List[List[float]]:
    """
    Return list of vectors for texts.

    - Accepts a single string or a list of strings.
    - Always returns a list of Python lists (not numpy arrays).
    """
    if texts is None:
        return []

    # Normalize single string -> list
    if isinstance(texts, str):
        texts = [texts]

    if not isinstance(texts, (list, tuple)) or len(texts) == 0:
        return []

    # Encode (SentenceTransformer returns a numpy array)
    vectors = model.encode(texts, show_progress_bar=False)

    # Convert to Python list of lists
    return _to_list(vectors)


def embed_query(query: str) -> List[float]:
    """
    Convenience helper: embed a single query and return the vector (as list).
    """
    res = embed_texts(query)
    return res[0] if res else []
