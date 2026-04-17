"""
Seed the database with MV Resolute demo data.

Idempotent — safe to run multiple times. Clears existing data and reinserts.
Run from repo root: python -m scripts.seed
"""
import json
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.database import SessionLocal, engine, Base
from backend.db.models import Vessel, CrewMember, Component

Base.metadata.create_all(bind=engine)


VESSEL_ID = "vessel-mv-resolute-001"

CREW = [
    {
        "crew_id": "crew-001",
        "full_name": "Captain James Hargreaves",
        "role": "Captain",
        "date_of_birth": date(1971, 3, 14),
        "blood_type": "O+",
        "allergies": [],
        "medical_notes": "Mild hypertension, on lisinopril 10mg daily.",
        "emergency_contact": {"name": "Sandra Hargreaves", "phone": "+44 7700 900123", "relation": "Spouse"},
    },
    {
        "crew_id": "crew-002",
        "full_name": "Chief Engineer Mikael Lindqvist",
        "role": "Chief Engineer",
        "date_of_birth": date(1978, 8, 22),
        "blood_type": "A+",
        "allergies": [],
        "medical_notes": "No chronic conditions.",
        "emergency_contact": {"name": "Eva Lindqvist", "phone": "+46 70 123 4567", "relation": "Spouse"},
    },
    {
        "crew_id": "crew-003",
        "full_name": "Dr. Priya Nair",
        "role": "Medical Person in Charge",
        "date_of_birth": date(1985, 11, 5),
        "blood_type": "B+",
        "allergies": ["Penicillin"],
        "medical_notes": "Penicillin allergy — document clearly. Use cephalosporins with caution.",
        "emergency_contact": {"name": "Arjun Nair", "phone": "+91 98765 43210", "relation": "Brother"},
    },
    {
        "crew_id": "crew-004",
        "full_name": "Cook Tomás Guerrero",
        "role": "Cook",
        "date_of_birth": date(1990, 6, 18),
        "blood_type": "AB-",
        "allergies": [],
        "medical_notes": "No known conditions.",
        "emergency_contact": {"name": "Carmen Guerrero", "phone": "+34 612 345 678", "relation": "Mother"},
    },
    {
        "crew_id": "crew-005",
        "full_name": "Deck Hand Oluwaseun Adeyemi",
        "role": "Deck Hand",
        "date_of_birth": date(1996, 2, 28),
        "blood_type": "O-",
        "allergies": [],
        "medical_notes": "No known conditions.",
        "emergency_contact": {"name": "Grace Adeyemi", "phone": "+234 803 456 7890", "relation": "Mother"},
    },
    {
        "crew_id": "crew-006",
        "full_name": "Deck Hand Rūta Kazlauskaitė",
        "role": "Deck Hand",
        "date_of_birth": date(1999, 9, 10),
        "blood_type": "A-",
        "allergies": ["Ibuprofen"],
        "medical_notes": "NSAID intolerance — paracetamol only for pain management.",
        "emergency_contact": {"name": "Darius Kazlauskas", "phone": "+370 612 34567", "relation": "Father"},
    },
]

COMPONENTS = [
    # Propulsion
    {
        "component_id": "comp-001",
        "name": "Main Engine",
        "system": "propulsion",
        "manufacturer": "MAN B&W",
        "model_number": "6S50MC-C8",
        "serial_number": "MBW-2019-0042",
        "install_date": date(2019, 4, 10),
        "location": "Engine Room — Centre",
        "manual_ref": "MAN B&W 6S50MC-C8 Operating Manual Rev.4",
        "spare_parts": ["Fuel injector set", "Piston rings", "Exhaust valve"],
        "notes": "Last major overhaul April 2023. Next due April 2027.",
    },
    {
        "component_id": "comp-002",
        "name": "Auxiliary Engine",
        "system": "propulsion",
        "manufacturer": "Caterpillar",
        "model_number": "C18 ACERT",
        "serial_number": "CAT-C18-78231",
        "install_date": date(2019, 4, 10),
        "location": "Engine Room — Port Side",
        "manual_ref": "Caterpillar C18 Marine Generator Set Manual",
        "spare_parts": ["Fuel filter", "Oil filter", "Drive belt"],
        "notes": "Runs at 450kW. Primary hotel load generator.",
    },
    # Electrical
    {
        "component_id": "comp-003",
        "name": "Main Switchboard",
        "system": "electrical",
        "manufacturer": "ABB",
        "model_number": "MNS 3.0",
        "serial_number": "ABB-MSB-2019-117",
        "install_date": date(2019, 4, 10),
        "location": "Engine Control Room",
        "manual_ref": "ABB MNS 3.0 Switchgear Manual",
        "spare_parts": ["Circuit breaker 400A", "Fuse 630A"],
        "notes": "440V 60Hz system. Shore power connection via port-side panel.",
    },
    {
        "component_id": "comp-004",
        "name": "Emergency Generator",
        "system": "electrical",
        "manufacturer": "Volvo Penta",
        "model_number": "D7A-MG",
        "serial_number": "VP-D7A-55443",
        "install_date": date(2019, 4, 10),
        "location": "Emergency Generator Room — Deck 3",
        "manual_ref": "Volvo Penta D7A Marine Generator Manual",
        "spare_parts": ["Fuel filter", "Cooling water pump impeller"],
        "notes": "SOLAS required. Test run monthly per ISM. Last test: satisfactory.",
    },
    # Navigation
    {
        "component_id": "comp-005",
        "name": "GPS/ECDIS Unit",
        "system": "navigation",
        "manufacturer": "Furuno",
        "model_number": "FMD-3300",
        "serial_number": "FUR-ECDIS-20211",
        "install_date": date(2021, 2, 15),
        "location": "Bridge — Starboard Console",
        "manual_ref": "Furuno FMD-3300 ECDIS Operator Manual",
        "spare_parts": ["Backup chart media"],
        "notes": "ENC licence renewed Jan 2026. Next renewal Jan 2027.",
    },
    {
        "component_id": "comp-006",
        "name": "VHF Radio",
        "system": "navigation",
        "manufacturer": "Sailor",
        "model_number": "RT6222",
        "serial_number": "SAI-VHF-9834",
        "install_date": date(2019, 4, 10),
        "location": "Bridge — Centre Console",
        "manual_ref": "Sailor RT6222 VHF DSC Radio Manual",
        "spare_parts": ["Spare handset", "Antenna connector"],
        "notes": "DSC-enabled. MMSI 123456789. Channel 16 always monitored.",
    },
    # Safety
    {
        "component_id": "comp-007",
        "name": "Fire Suppression System",
        "system": "safety",
        "manufacturer": "Kidde",
        "model_number": "FM-200 Fixed System",
        "serial_number": "KID-FM200-2019-03",
        "install_date": date(2019, 4, 10),
        "location": "Engine Room / Paint Store",
        "manual_ref": "Kidde FM-200 Marine System Manual",
        "spare_parts": ["Agent cylinder"],
        "notes": "Serviced annually. Last inspection: Oct 2025.",
    },
    {
        "component_id": "comp-008",
        "name": "Life Raft Release Mechanism",
        "system": "safety",
        "manufacturer": "Survitec",
        "model_number": "HRU MkIII",
        "serial_number": "SUR-HRU-7721",
        "install_date": date(2022, 6, 1),
        "location": "Boat Deck — Port and Starboard",
        "manual_ref": "Survitec HRU MkIII Service Manual",
        "spare_parts": [],
        "notes": "Hydrostatic release. Serviced every 2 years. Next due June 2026.",
    },
    # HVAC
    {
        "component_id": "comp-009",
        "name": "Engine Room Ventilation",
        "system": "hvac",
        "manufacturer": "Novenco Marine & Offshore",
        "model_number": "ZerAx 1250",
        "serial_number": "NOV-ERV-20221",
        "install_date": date(2019, 4, 10),
        "location": "Engine Room — Overhead",
        "manual_ref": "Novenco ZerAx Marine Fan Manual",
        "spare_parts": ["Fan motor bearings", "Drive belt"],
        "notes": "Runs continuously at sea. Alarm set at 45°C engine room ambient.",
    },
    # Hull
    {
        "component_id": "comp-010",
        "name": "Bilge Pump System",
        "system": "hull",
        "manufacturer": "Hamworthy",
        "model_number": "Viking 125",
        "serial_number": "HAM-BP-2019-09",
        "install_date": date(2019, 4, 10),
        "location": "Engine Room — Bilge",
        "manual_ref": "Hamworthy Viking Series Bilge Pump Manual",
        "spare_parts": ["Impeller", "Shaft seal kit"],
        "notes": "Automatic float switch. Test manually monthly. MARPOL ODM fitted.",
    },
]


def seed():
    db = SessionLocal()
    try:
        print("Clearing existing data...")
        db.query(Component).delete()
        db.query(CrewMember).delete()
        db.query(Vessel).delete()
        db.commit()

        print("Seeding vessel: MV Resolute")
        vessel = Vessel(
            vessel_id=VESSEL_ID,
            name="MV Resolute",
            imo_number="9876543",
            created_at=datetime.utcnow(),
        )
        db.add(vessel)
        db.commit()

        print(f"Seeding {len(CREW)} crew members...")
        for c in CREW:
            member = CrewMember(
                crew_id=c["crew_id"],
                vessel_id=VESSEL_ID,
                full_name=c["full_name"],
                role=c["role"],
                date_of_birth=c["date_of_birth"],
                blood_type=c["blood_type"],
                allergies=json.dumps(c["allergies"]),
                medical_notes=c["medical_notes"],
                emergency_contact=json.dumps(c["emergency_contact"]),
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(member)
        db.commit()

        print(f"Seeding {len(COMPONENTS)} components...")
        for comp in COMPONENTS:
            component = Component(
                component_id=comp["component_id"],
                vessel_id=VESSEL_ID,
                name=comp["name"],
                system=comp["system"],
                manufacturer=comp["manufacturer"],
                model_number=comp["model_number"],
                serial_number=comp["serial_number"],
                install_date=comp["install_date"],
                location=comp["location"],
                manual_ref=comp["manual_ref"],
                spare_parts=json.dumps(comp["spare_parts"]),
                notes=comp["notes"],
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(component)
        db.commit()

        print("✓ Seed complete.")
        print(f"  Vessel: MV Resolute (IMO {vessel.imo_number})")
        print(f"  Crew:   {len(CREW)}")
        print(f"  Components: {len(COMPONENTS)} across 6 systems")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
