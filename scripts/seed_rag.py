import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai.rag_engine import RAGEngine

MEDICAL_CHUNKS = [
    ("med-1", "IMGS Ch 1.1: For severe burns, immediately cool the burn with running water for at least 20 minutes. Do not burst blisters.", {"source": "IMGS"}),
    ("med-2", "IMGS Ch 4.2: Symptoms of Appendicitis include pain starting in the center of the abdomen, moving to the lower right side. Nausea and vomiting are common. Immediate TMAS consult required.", {"source": "IMGS"}),
    ("med-3", "Ship Captain's Medical Guide: Paracetamol dosage for adults is 500mg-1g every 4-6 hours, maximum 4g per 24 hours.", {"source": "SCMG"}),
    ("med-4", "IMGS Ch 2.5: For suspected concussion, monitor patient's consciousness every 15 minutes. Check for unequal pupil size. If deteriorating, prepare for evacuation.", {"source": "IMGS"}),
    ("med-5", "IMGS Ch 7.3: In case of severe bleeding, apply direct pressure. Elevate the limb if possible. Use a tourniquet only as a last resort if bleeding cannot be controlled.", {"source": "IMGS"})
]

ENGINE_CHUNKS = [
    ("eng-1", "MAN B&W 6S50MC-C8: If exhaust gas temperature deviation exceeds 50°C, check fuel injector and exhaust valve on the affected cylinder.", {"source": "MAN Manual"}),
    ("eng-2", "Caterpillar C18: Low cooling water pressure alarm. Immediate action: Check expansion tank level and inspect raw water strainer for blockages.", {"source": "Cat C18"}),
    ("eng-3", "Alfa Laval Purifier: If water seal is broken, purifier will discharge oil to the sludge tank. Stop purifier, clean the bowl, and establish new water seal.", {"source": "Alfa Laval"}),
    ("eng-4", "Hamworthy Viking: Pump fails to build pressure. Common causes: Air leak in suction line, worn impeller, or blocked suction strainer.", {"source": "Hamworthy"}),
    ("eng-5", "MAN B&W 6S50MC-C8: Starting air valve stuck open. Warning: Engine may turn unexpectedly. Isolate starting air supply and vent the system before maintenance.", {"source": "MAN Manual"})
]

def seed_rag():
    engine = RAGEngine()
    
    # Medical
    print("Seeding medical_protocols...")
    try:
        engine.client.delete_collection("medical_protocols")
    except:
        pass
    engine.add_documents(
        collection_name="medical_protocols",
        ids=[x[0] for x in MEDICAL_CHUNKS],
        documents=[x[1] for x in MEDICAL_CHUNKS],
        metadatas=[x[2] for x in MEDICAL_CHUNKS]
    )
    
    # Engine
    print("Seeding engine_manuals...")
    try:
        engine.client.delete_collection("engine_manuals")
    except:
        pass
    engine.add_documents(
        collection_name="engine_manuals",
        ids=[x[0] for x in ENGINE_CHUNKS],
        documents=[x[1] for x in ENGINE_CHUNKS],
        metadatas=[x[2] for x in ENGINE_CHUNKS]
    )
    
    print("RAG Seed complete!")

if __name__ == "__main__":
    seed_rag()
