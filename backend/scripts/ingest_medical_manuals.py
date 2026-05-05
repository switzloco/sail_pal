import os
import urllib.request
import fitz  # PyMuPDF
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.ai.rag_engine import RAGEngine

MANUALS = [
    {
        "name": "Ship's Medicine Chest and Medical Aid at Sea",
        "url": "https://fas.org/irp/doddir/milmed/ships.pdf"
    },
    {
        "name": "USCG Medical Manual COMDTINST M6000.1F",
        "url": "https://media.defense.gov/2017/Mar/29/2001723588/-1/-1/0/CIM_6000_1F.PDF"
    }
]

def main():
    rag = RAGEngine()
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "manuals")
    os.makedirs(data_dir, exist_ok=True)
    
    for manual in MANUALS:
        pdf_path = os.path.join(data_dir, f"{manual['name'].replace(' ', '_')}.pdf")
        print(f"Downloading {manual['name']}...")
        
        try:
            req = urllib.request.Request(manual['url'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(pdf_path, 'wb') as out_file:
                out_file.write(response.read())
                
            print(f"Processing {manual['name']}...")
            doc = fitz.open(pdf_path)
            chunks = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if not text.strip():
                    continue
                    
                chunks.append({
                    "text": text.strip(),
                    "metadata": {"source": manual["name"], "page": page_num + 1}
                })
            
            doc.close()
            print(f"Extracted {len(chunks)} pages from {manual['name']}.")
            
            if not chunks:
                continue
                
            ids = [f"{manual['name'][:10]}-{c['metadata']['page']}-{uuid.uuid4().hex[:8]}" for c in chunks]
            texts = [c["text"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                rag.add_documents(
                    collection_name="medical_protocols",
                    documents=texts[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size],
                    ids=ids[i:i+batch_size]
                )
            print(f"Added {len(chunks)} chunks to RAG for {manual['name']}")
            
        except Exception as e:
            print(f"Failed to process {manual['name']}: {e}")

if __name__ == "__main__":
    main()
