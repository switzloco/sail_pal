"""
Pre-process the WHO IMGS PDF into bundled chunks.

Run this once locally to regenerate backend/data/knowledge/who_imgs.json.
The result is committed to the repo and ingested into SQLite FTS5 on first
launch (see backend/ai/rag_engine.py).

Why do this offline rather than at runtime:
  - Avoids shipping pymupdf to every end-user just to re-extract the same PDF.
  - Keeps the desktop install path simple (no PDF extraction during boot).
  - Lets us tune chunking once and ship deterministic chunks.

Run:
    python -m backend.scripts.preprocess_who_imgs
"""
import hashlib
import json
import os
import re
import sys
from typing import List, Dict

try:
    import pymupdf  # type: ignore
except ImportError:
    print("pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF_PATH = os.path.join(REPO_ROOT, "backend", "data", "manuals", "WHO_IMGS_3rd_Edition.pdf")
OUTPUT_DIR = os.path.join(REPO_ROOT, "backend", "data", "knowledge")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "who_imgs.json")

# Chunks are roughly 1 page or 1500 chars, whichever is shorter. Smaller chunks
# give FTS5 finer-grained BM25 ranking but more chunks to scan; this size lands
# in the sweet spot for medical reference docs.
MAX_CHUNK_CHARS = 1500


def _chunk_id(text: str, page: int) -> str:
    # Stable id so re-runs are idempotent in FTS5 (delete-then-insert keys on it).
    digest = hashlib.sha1(f"{page}:{text[:200]}".encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return f"who-imgs-p{page}-{digest}"


def _split_long_page(text: str, max_chars: int) -> List[str]:
    """Split a long page into smaller chunks on paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip() if current else paragraph
        else:
            if current:
                chunks.append(current)
            # A single paragraph longer than max_chars: hard-split it.
            while len(paragraph) > max_chars:
                chunks.append(paragraph[:max_chars])
                paragraph = paragraph[max_chars:]
            current = paragraph
    if current:
        chunks.append(current)
    return chunks


def extract_chunks(pdf_path: str) -> List[Dict]:
    chunks: List[Dict] = []
    with pymupdf.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text:
                continue
            # Normalize whitespace: collapse runs of spaces, keep paragraph breaks.
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)

            for piece in _split_long_page(text, MAX_CHUNK_CHARS):
                chunks.append(
                    {
                        "id": _chunk_id(piece, page_num),
                        "text": piece,
                        "metadata": {
                            "source": "WHO International Medical Guide for Ships (3rd Edition)",
                            "page": page_num,
                        },
                    }
                )
    return chunks


def main() -> None:
    if not os.path.isfile(PDF_PATH):
        print(f"PDF not found at {PDF_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting from {PDF_PATH}...")
    chunks = extract_chunks(PDF_PATH)
    print(f"Produced {len(chunks)} chunks.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    payload = {
        "collection": "medical_protocols",
        "source": "WHO International Medical Guide for Ships (3rd Edition)",
        "chunks": chunks,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"Wrote {OUTPUT_PATH} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
