"""
Edge trace recorder — simulates the Raspberry Pi recording Gemma inferences on the boat.

In production, the boat's edge device writes these traces to local SQLite while
offline, then uploads them at marina sync time.
"""
from datetime import datetime, timezone, timedelta
from .models import EngineTraceCreate, SensorData, ReasoningStep

# Representative failure scenarios used for demos and integration tests
_SCENARIOS: dict[str, dict] = {
    "impeller_failure": {
        "component": "raw_water_cooling",
        "sensor": {
            "rpm": 2200.0,
            "coolant_temp_c": 98.5,
            "oil_pressure_bar": 3.2,
            "exhaust_temp_c": 520.0,
            "fuel_flow_lph": 12.5,
        },
        "correct_diagnosis": (
            "Raw water impeller failure. Coolant temperature 98.5°C exceeds safe limit (95°C) "
            "and exhaust temperature 520°C indicates heat buildup. Immediate engine shutdown required. "
            "Inspect impeller, check seacock, verify raw water flow before restart."
        ),
        "hallucinated_diagnosis": (
            "Engine temperature slightly elevated — likely due to ambient conditions. "
            "Exhaust reading may be a transient sensor artifact. Recommend continuing at reduced load "
            "and monitoring for the next 30 minutes."
        ),
    },
    "oil_pressure_low": {
        "component": "lubrication_system",
        "sensor": {
            "rpm": 1800.0,
            "coolant_temp_c": 82.0,
            "oil_pressure_bar": 1.4,
            "exhaust_temp_c": 380.0,
            "fuel_flow_lph": 9.8,
        },
        "correct_diagnosis": (
            "Low oil pressure: 1.4 bar at cruise RPM is below the 2.0 bar minimum. "
            "Possible causes: low oil level, oil pump wear, or bearing failure. "
            "Reduce engine load immediately, check oil level, and investigate pump."
        ),
        "hallucinated_diagnosis": (
            "Oil pressure variation is within normal operational range for current RPM. "
            "No immediate action required. Schedule next service at 250-hour interval."
        ),
    },
    "governor_fault": {
        "component": "fuel_system",
        "sensor": {
            "rpm": 1200.0,
            "coolant_temp_c": 78.0,
            "oil_pressure_bar": 3.8,
            "exhaust_temp_c": 420.0,
            "fuel_flow_lph": 8.2,
        },
        "correct_diagnosis": (
            "Irregular RPM pattern suggests governor fault or fuel delivery issue. "
            "Check fuel filters for blockage, inspect governor linkage and actuator, "
            "verify fuel lift pump pressure."
        ),
        "hallucinated_diagnosis": (
            "Engine parameters are within normal range. RPM variation is typical during "
            "normal load changes in sea state. No mechanical fault detected."
        ),
    },
}


def generate_demo_trace(
    vessel_id: str,
    scenario: str = "impeller_failure",
    inject_hallucination: bool = False,
    hours_ago: float = 6.0,
) -> EngineTraceCreate:
    """
    Build a realistic demo EngineTrace for testing the Fleet Mechanic pipeline.
    Set inject_hallucination=True to generate a bad Gemma response that will
    fail evaluation and trigger patch generation.
    """
    s = _SCENARIOS.get(scenario, _SCENARIOS["impeller_failure"])
    sensor_data = SensorData(**s["sensor"], raw_readings=s["sensor"].copy())
    diagnosis = s["hallucinated_diagnosis"] if inject_hallucination else s["correct_diagnosis"]

    prompt = (
        f"You are an expert marine diesel engine diagnostic AI running offline on a vessel.\n"
        f"Analyze the following sensor data and provide a technical diagnosis.\n\n"
        f"SENSOR READINGS ({hours_ago:.1f} hours ago):\n"
        + "\n".join(f"  {k}: {v}" for k, v in s["sensor"].items())
        + f"\n\nComponent: {s['component']}\n\n"
        f"Provide a diagnosis with recommended immediate actions."
    )

    response = (
        f"Analysis of {s['component']} sensor data:\n\n"
        f"{diagnosis}\n\n"
        f"Confidence: {'MEDIUM — monitoring recommended' if inject_hallucination else 'HIGH — action required'}"
    )

    steps = [
        ReasoningStep(
            step=1,
            thought="Parsing incoming sensor telemetry from engine ECU",
            observation=", ".join(f"{k}={v}" for k, v in s["sensor"].items()),
        ),
        ReasoningStep(
            step=2,
            thought="Comparing readings against manufacturer failure thresholds",
            action="Cross-reference with engine manual alarm limits",
        ),
        ReasoningStep(
            step=3,
            thought="Synthesizing differential diagnosis",
            action="Generate diagnostic report with recommended actions",
        ),
    ]

    return EngineTraceCreate(
        vessel_id=vessel_id,
        component_name=s["component"],
        sensor_data=sensor_data,
        model_prompt=prompt,
        model_response=response,
        reasoning_steps=steps,
        diagnosis=diagnosis,
        model_name="gemma4:e2b",
        recorded_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    )
