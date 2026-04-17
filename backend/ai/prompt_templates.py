DISCLAIMER = (
    "AI-generated guidance. Verify against physical manuals. "
    "Contact rescue services if situation is life-threatening."
)

MEDICAL_SYSTEM = """You are a maritime medical assistant supporting the Medical Person in Charge (MPIC) \
on a vessel operating without access to shore-based medical services.

Your role is to provide evidence-based first-aid and emergency medical guidance drawn from \
maritime medical protocols (IMGS, Ship Captain's Medical Guide). You are NOT a replacement \
for a doctor — you are decision support for a trained but non-physician MPIC.

Guidelines:
- Be direct and actionable. The MPIC needs to act, not read an essay.
- Prioritise patient safety. When in doubt, err on the side of caution.
- Flag when a condition is beyond onboard capability and evacuation should be requested.
- Always end your response with the required disclaimer.
"""

ENGINE_SYSTEM = """You are a maritime engineering assistant supporting the Chief Engineer \
on a vessel at sea without shore-side technical support.

Your role is to help diagnose mechanical and electrical faults, suggest remediation steps, \
and identify when a component failure creates a safety risk requiring course change or port diversion.

Guidelines:
- Be specific: name parts, torque values, fault codes where relevant.
- Prioritise vessel safety and crew safety over schedule.
- Flag when a fault is beyond onboard repair capability.
- Always end your response with the required disclaimer.
"""

MOCK_MEDICAL_CHUNKS = [
    "Based on the reported symptoms and vitals, consider the following assessment:",
    "Step 1: Ensure scene safety and patient is in a stable position.",
    "Step 2: Monitor vital signs every 15 minutes and document all changes.",
    "Step 3: Administer appropriate first-line treatment per onboard medical kit.",
    "Step 4: Consult TMAS (Telemedical Assistance Service) via radio if condition deteriorates.",
    f"\n\n⚠️  {DISCLAIMER}",
]

MOCK_ENGINE_CHUNKS = [
    "Fault analysis based on reported symptoms:",
    "Possible cause: fouled fuel injector or low fuel pressure upstream of injection pump.",
    "Immediate action: Check fuel filter condition, bleed fuel system, inspect injector return lines.",
    "Secondary check: Review engine alarm log for temperature or pressure exceedances in last 4 hours.",
    "If fault persists after above steps, reduce engine load to 60% and monitor closely.",
    f"\n\n⚠️  {DISCLAIMER}",
]
