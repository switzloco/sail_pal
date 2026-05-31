"""
Arize Phoenix client for the Fleet Mechanic.

Sends offline boat traces to Phoenix in OpenInference span format and records
LLM evaluation results. Gracefully degrades if Phoenix is unreachable.
"""
import json
import logging
import uuid
from typing import Optional

import httpx

from .models import EngineTraceCreate, EvalLabel

logger = logging.getLogger(__name__)

# Evaluation rubrics used by the Gemini Fleet Mechanic agent
EVAL_RUBRIC_HALLUCINATION = """You are evaluating whether an AI marine engineering assistant hallucinated in its response to engine sensor data.

SENSOR DATA PROVIDED:
{sensor_data}

AI MODEL RESPONSE:
{response}

DIAGNOSIS GIVEN:
{diagnosis}

Evaluate: Did the AI fabricate sensor readings, invent failure modes not supported by the data, claim impossible physical states, or contradict what the sensor data clearly shows?

A "fail" means the diagnosis directly contradicts the sensor data or invents facts.
A "warning" means the diagnosis has unsupported claims or missed clear indicators.
A "pass" means the diagnosis is consistent with the sensor data.

Respond with a JSON object containing:
- score: number from 0.0 (severe hallucination) to 1.0 (no hallucination)
- label: "pass" if score >= 0.7, "warning" if 0.4-0.69, "fail" if below 0.4
- explanation: one or two sentences explaining your assessment"""

EVAL_RUBRIC_CORRECTNESS = """You are evaluating whether an AI marine engineering assistant gave a technically correct diagnosis based on engine sensor data.

SENSOR DATA:
{sensor_data}

AI DIAGNOSIS:
{diagnosis}

KNOWN ENGINE FAILURE INDICATORS:
- Coolant temp > 95°C: overheating, likely impeller failure, blocked seacock, or low coolant
- Oil pressure < 2.0 bar at cruise RPM: oil pump failure, low oil level, or bearing wear
- Exhaust temp > 500°C: incomplete combustion, injector fault, or restricted exhaust
- RPM instability / oscillation: governor fault or fuel delivery issue
- Alternator output < 13V at cruise: alternator failure or belt slip

Rate the technical accuracy:
- score: 0.0 (completely wrong) to 1.0 (fully correct)
- label: "pass" / "warning" / "fail"
- explanation: specific reasoning referencing the sensor values

Respond with a JSON object containing score, label, and explanation."""


class ArizePhoenixClient:
    """
    Pushes offline Gemma inference traces to Arize Phoenix for observability
    and records Gemini evaluation results against those traces.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/healthz", headers=self._headers)
                return r.status_code == 200
        except Exception:
            return False

    async def ingest_trace(self, trace: EngineTraceCreate, db_trace_id: str) -> str:
        """
        Format and send an offline engine trace as an OpenInference span.
        Returns the Phoenix trace ID (generated locally if Phoenix is unreachable).
        """
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]

        # OpenTelemetry / OpenInference span format that Phoenix natively understands
        payload = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "vessel-ops-ai-edge"}},
                        {"key": "deployment.mode", "value": {"stringValue": "offline-edge"}},
                        {"key": "vessel.id", "value": {"stringValue": str(trace.vessel_id)}},
                        {"key": "model.name", "value": {"stringValue": trace.model_name}},
                    ]
                },
                "scopeSpans": [{
                    "scope": {"name": "openinference.instrumentation.engine"},
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": f"engine.diagnose.{trace.component_name}",
                        "kind": 3,
                        "startTimeUnixNano": str(int(trace.recorded_at.timestamp() * 1e9)),
                        "endTimeUnixNano": str(int(trace.recorded_at.timestamp() * 1e9 + 2_000_000_000)),
                        "attributes": [
                            {"key": "openinference.span.kind", "value": {"stringValue": "LLM"}},
                            {"key": "input.value", "value": {"stringValue": trace.model_prompt}},
                            {"key": "output.value", "value": {"stringValue": trace.model_response}},
                            {"key": "llm.model_name", "value": {"stringValue": trace.model_name}},
                            {"key": "engine.component", "value": {"stringValue": trace.component_name}},
                            {"key": "engine.diagnosis", "value": {"stringValue": trace.diagnosis}},
                            {"key": "engine.sensor_data", "value": {
                                "stringValue": json.dumps(trace.sensor_data.model_dump())
                            }},
                            {"key": "engine.reasoning_steps", "value": {
                                "stringValue": json.dumps([s.model_dump() for s in trace.reasoning_steps])
                            }},
                            {"key": "fleet.db_trace_id", "value": {"stringValue": db_trace_id}},
                            {"key": "fleet.recorded_at", "value": {"stringValue": trace.recorded_at.isoformat()}},
                        ],
                        "status": {"code": 1},
                    }]
                }]
            }]
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.base_url}/v1/traces",
                    json=payload,
                    headers=self._headers,
                )
                r.raise_for_status()
                logger.info(f"Trace {db_trace_id} ingested to Phoenix as {trace_id}")
        except Exception as exc:
            logger.warning(f"Phoenix ingest skipped (offline or unreachable): {exc}")

        return trace_id

    async def record_evaluation(
        self,
        phoenix_trace_id: str,
        eval_name: str,
        label: str,
        score: float,
        explanation: str,
    ) -> None:
        """Push an evaluation result back to Phoenix so it's visible in the UI."""
        payload = {
            "data": [{
                "trace_id": phoenix_trace_id,
                "name": eval_name,
                "annotator_kind": "LLM",
                "result": {
                    "label": label,
                    "score": score,
                    "explanation": explanation,
                },
            }]
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.base_url}/v1/evaluations",
                    json=payload,
                    headers=self._headers,
                )
                r.raise_for_status()
        except Exception as exc:
            logger.warning(f"Phoenix eval record skipped: {exc}")
