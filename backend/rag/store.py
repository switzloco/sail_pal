import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class KnowledgeStore:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            # Default to backend/data/vessel_knowledge/store.json
            base_dir = Path(__file__).resolve().parent.parent / "data" / "vessel_knowledge"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.storage_path = base_dir / "knowledge_base.json"
        else:
            self.storage_path = Path(storage_path)
        
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return {"manuals": [], "health_protocols": []}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"manuals": [], "health_protocols": []}

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def add_manual(self, manual_id: str, title: str, sections: List[Dict[str, str]]):
        manual = {
            "id": manual_id,
            "title": title,
            "type": "diagnostic",
            "sections": sections
        }
        # Update existing or append
        for i, m in enumerate(self.data["manuals"]):
            if m["id"] == manual_id:
                self.data["manuals"][i] = manual
                self.save()
                return
        self.data["manuals"].append(manual)
        self.save()

    def add_protocol(self, protocol_id: str, title: str, steps: List[str]):
        protocol = {
            "id": protocol_id,
            "title": title,
            "steps": steps
        }
        for i, p in enumerate(self.data["health_protocols"]):
            if p["id"] == protocol_id:
                self.data["health_protocols"][i] = protocol
                self.save()
                return
        self.data["health_protocols"].append(protocol)
        self.save()

    def search_manuals(self, query: str) -> str:
        """Simple keyword search for manuals context."""
        context = []
        query_words = query.lower().split()
        for manual in self.data["manuals"]:
            for section in manual["sections"]:
                if any(word in section["content"].lower() or word in section["header"].lower() for word in query_words):
                    context.append(f"Source: {manual['title']} - {section['header']}\n{section['content']}")
        
        return "\n\n".join(context[:5]) # Limit context size

    def search_protocols(self, query: str) -> str:
        """Simple keyword search for health protocols."""
        context = []
        query_words = query.lower().split()
        for protocol in self.data["health_protocols"]:
            if any(word in protocol["title"].lower() or any(word in step.lower() for step in protocol["steps"]) for word in query_words):
                steps_str = "\n".join([f"- {s}" for s in protocol["steps"]])
                context.append(f"Protocol: {protocol['title']}\nSteps:\n{steps_str}")
        
        return "\n\n".join(context[:3])

knowledge_store = KnowledgeStore()
