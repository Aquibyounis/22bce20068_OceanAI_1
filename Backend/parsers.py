# Backend/parsers.py
from pathlib import Path
import json
import fitz
from bs4 import BeautifulSoup

def extract_text(path: str) -> str:
    p = Path(path)
    ext = p.suffix.lower()

    if ext == ".pdf":
        return extract_pdf(p)
    elif ext == ".json":
        return extract_json(p)
    elif ext in [".html", ".htm"]:
        return extract_html(p)
    else:
        return extract_textfile(p)

def extract_pdf(path: Path) -> str:
    doc = fitz.open(str(path))
    pages = [page.get_text() for page in doc]
    return "\n".join(pages)

def extract_json(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        return json.dumps(obj, indent=2)
    except Exception:
        return path.read_text(encoding="utf-8", errors="ignore")

def extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")
    return soup.get_text(separator="\n")

def extract_textfile(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")
