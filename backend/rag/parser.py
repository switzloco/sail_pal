import os
from pathlib import Path
from backend.rag.store import knowledge_store

def ingest_text_manual(file_path: str, manual_id: str, title: str):
    path = Path(file_path)
    if not path.exists():
        print(f"File not found: {file_path}")
        return

    content = path.read_text(encoding="utf-8")
    # Simple chunking by double newline or specific markers
    chunks = content.split("\n\n")
    sections = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        # Use first line as header if short, otherwise generic
        lines = chunk.strip().split("\n")
        header = lines[0] if len(lines[0]) < 50 else f"Section {i+1}"
        body = "\n".join(lines[1:]) if len(lines[0]) < 50 else chunk
        sections.append({
            "header": header,
            "content": body
        })

    knowledge_store.add_manual(manual_id, title, sections)
    print(f"Ingested {len(sections)} sections for manual '{title}'")

def ingest_protocol_list(title: str, steps: list, protocol_id: str):
    knowledge_store.add_protocol(protocol_id, title, steps)
    print(f"Ingested protocol '{title}'")
