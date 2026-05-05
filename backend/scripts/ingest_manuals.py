
import os
import sys
import uuid
import fitz
from typing import List

# Add project root to sys.path to allow importing from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.ai.rag_engine import RAGEngine

def ingest_pdf(file_path: str, category: str):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    filename = os.path.basename(file_path)
    print(f"Ingesting {filename} into {category}...")

    rag = RAGEngine()
    doc = fitz.open(file_path)
    chunks = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if not text.strip():
            continue
            
        chunks.append({
            "text": text.strip(),
            "metadata": {"source": filename, "page": page_num + 1}
        })

    doc.close()

    if not chunks:
        print(f"No text found in {filename}")
        return

    # Add to ChromaDB in batches
    ids = [f"{filename}-{c['metadata']['page']}-{uuid.uuid4().hex[:8]}" for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        end = min(i + batch_size, len(chunks))
        print(f"  Processing batch {i//batch_size + 1}: documents {i} to {end}...")
        rag.add_documents(
            collection_name=category,
            documents=texts[i:end],
            metadatas=metadatas[i:end],
            ids=ids[i:end]
        )

    print(f"Successfully ingested {filename}. Processed {len(chunks)} pages.")

if __name__ == "__main__":
    # Ensure directories exist
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manuals_dir = os.path.join(backend_dir, "data", "manuals")
    
    # Process WHO IMGS if it exists
    who_imgs = os.path.join(manuals_dir, "WHO_IMGS_3rd_Edition.pdf")
    if os.path.exists(who_imgs):
        ingest_pdf(who_imgs, "medical_protocols")
    else:
        print(f"WHO IMGS not found at {who_imgs}")
