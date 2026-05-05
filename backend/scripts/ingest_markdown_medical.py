import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.ai.rag_engine import RAGEngine

def main():
    rag = RAGEngine()
    md_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "manuals", "medical_protocols_mpic_curated.md")
    
    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found.")
        return
        
    print(f"Ingesting {md_path}...")
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Simple chunking by headers
    chunks = content.split("\n## ")
    processed_chunks = []
    
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
            
        header = chunk.split("\n")[0]
        text = "## " + chunk if i > 0 else chunk
        
        processed_chunks.append({
            "text": text.strip(),
            "metadata": {"source": "MPIC Curated Protocols", "section": header}
        })
        
    print(f"Extracted {len(processed_chunks)} sections.")
    
    ids = [f"mpic-curated-{uuid.uuid4().hex[:8]}" for _ in processed_chunks]
    texts = [c["text"] for c in processed_chunks]
    metadatas = [c["metadata"] for c in processed_chunks]
    
    rag.add_documents(
        collection_name="medical_protocols",
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"Successfully added {len(processed_chunks)} sections to 'medical_protocols' collection.")

if __name__ == "__main__":
    main()
