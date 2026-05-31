"""
Gemini Fleet Mechanic Agent

Wakes up when a vessel connects at the marina. Ingests offline Gemma inference
traces into Arize Phoenix, runs autonomous hallucination and correctness
evaluations, then drafts prompt patches for any flagged inferences.
"""
import json
import logging
import uuid
from typing import Any

from google import genai
from google.genai import types

from ..config import settings
from .arize_client import (
    ArizePhoenixClient,
    EVAL_RUBRIC_HALLUCINATION,
    EVAL_RUBRIC_CORRECTNESS,
)
from .models import EngineTraceCreate, MarinaSyncReport

logger = logging.getLogger(__name__)

# Schema shared by both evaluation calls
_EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number"},
        "label": {"type": "string", "enum": ["pass", "fail", "warning"]},
        "explanation": {"type": "string"},
    },
    "required": ["score", "label", "explanation"],
}

_PATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "patch_type": {"type": "string", "enum": ["system_instruction", "few_shot_example", "rag_addition"]},
        "original_section": {"type": "string"},
        "patched_section": {"type": "string"},
        "rationale": {"type": "string"},
        "agent_reasoning": {"type": "string"},
    },
    "required": ["patch_type", "original_section", "patched_section", "rationale", "agent_reasoning"],
}


class FleetMechanicAgent:
    """
    The Gemini-powered Fleet Mechanic.

    Uses the Arize Phoenix MCP (via ArizePhoenixClient) to ingest offline
    Gemma traces, then calls Gemini with structured-output prompts to run
    hallucination and correctness evaluations. Flagged traces trigger an
    autonomous prompt-patch drafting step.

    Tool surface (analogous to MCP tools the agent calls):
      - arize_ingest_trace     → ArizePhoenixClient.ingest_trace
      - arize_record_eval      → ArizePhoenixClient.record_evaluation
      - gemini_eval_hallucination
      - gemini_eval_correctness
      - gemini_draft_patch
    """

    def __init__(self, phoenix_client: ArizePhoenixClient):
        self.phoenix = phoenix_client
        self._genai = genai.Client(api_key=settings.google_api_key)
        self._model = getattr(settings, "fleet_mechanic_model", "gemini-2.0-flash")

    async def process_marina_sync(
        self,
        traces: list[EngineTraceCreate],
        db_trace_ids: list[str],
    ) -> MarinaSyncReport:
        """
        Main entry: processes all traces uploaded from the vessel.
        Returns a sync report with evaluation results and pending patches.
        """
        sync_id = str(uuid.uuid4())
        logger.info(f"Fleet Mechanic [{sync_id}]: processing {len(traces)} traces")

        trace_results: list[dict[str, Any]] = []
        total_evals = 0
        total_patches = 0
        flagged_count = 0

        for trace, db_id in zip(traces, db_trace_ids):
            result = await self._process_trace(trace, db_id)
            trace_results.append(result)
            total_evals += len(result.get("evaluations", []))
            total_patches += len(result.get("patches", []))
            if result.get("flagged"):
                flagged_count += 1

        summary = self._build_summary(len(traces), flagged_count)
        return MarinaSyncReport(
            sync_id=sync_id,
            traces_ingested=len(traces),
            evaluations_run=total_evals,
            patches_generated=total_patches,
            flagged_count=flagged_count,
            summary=summary,
            trace_results=trace_results,
        )

    async def _process_trace(self, trace: EngineTraceCreate, db_id: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "db_id": db_id,
            "component": trace.component_name,
            "diagnosis": trace.diagnosis,
            "evaluations": [],
            "patches": [],
            "flagged": False,
            "phoenix_trace_id": None,
        }

        # Tool call 1 — arize_ingest_trace
        phoenix_id = await self.phoenix.ingest_trace(trace, db_id)
        result["phoenix_trace_id"] = phoenix_id

        sensor_json = json.dumps(trace.sensor_data.model_dump(), indent=2)

        # Tool call 2 — gemini_eval_hallucination
        halluc = await self._call_gemini_eval(
            EVAL_RUBRIC_HALLUCINATION.format(
                sensor_data=sensor_json,
                response=trace.model_response,
                diagnosis=trace.diagnosis,
            ),
            eval_name="hallucination",
        )
        result["evaluations"].append(halluc)
        # Tool call 3 — arize_record_eval
        await self.phoenix.record_evaluation(
            phoenix_id, "hallucination",
            halluc["label"], halluc["score"], halluc["explanation"],
        )

        # Tool call 4 — gemini_eval_correctness
        correct = await self._call_gemini_eval(
            EVAL_RUBRIC_CORRECTNESS.format(
                sensor_data=sensor_json,
                diagnosis=trace.diagnosis,
            ),
            eval_name="qa_correctness",
        )
        result["evaluations"].append(correct)
        # Tool call 5 — arize_record_eval
        await self.phoenix.record_evaluation(
            phoenix_id, "qa_correctness",
            correct["label"], correct["score"], correct["explanation"],
        )

        # Tool call 6 — gemini_draft_patch (only when flagged)
        failed = [e for e in result["evaluations"] if e["label"] in ("fail", "warning")]
        if failed:
            result["flagged"] = True
            patch = await self._draft_patch(trace, phoenix_id, failed)
            result["patches"].append(patch)

        return result

    async def _call_gemini_eval(self, rubric: str, eval_name: str) -> dict[str, Any]:
        try:
            response = self._genai.models.generate_content(
                model=self._model,
                contents=rubric,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_EVAL_SCHEMA,
                    temperature=0.1,
                ),
            )
            data = json.loads(response.text)
            return {
                "eval_type": eval_name,
                "score": float(data.get("score", 0.5)),
                "label": data.get("label", "warning"),
                "explanation": data.get("explanation", ""),
            }
        except Exception as exc:
            logger.error(f"Gemini eval '{eval_name}' failed: {exc}")
            return {
                "eval_type": eval_name,
                "score": 0.5,
                "label": "warning",
                "explanation": f"Evaluation error: {exc}",
            }

    async def _draft_patch(
        self,
        trace: EngineTraceCreate,
        phoenix_trace_id: str,
        failed_evals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        issues = "\n".join(
            f"  [{e['eval_type']}] score={e['score']:.2f} ({e['label']}): {e['explanation']}"
            for e in failed_evals
        )
        prompt = f"""You are the Fleet Mechanic — an AI systems engineer responsible for improving the Gemma model that runs offline on vessels at sea.

A Gemma inference was flagged during post-voyage evaluation.

COMPONENT DIAGNOSED: {trace.component_name}

SENSOR DATA:
{json.dumps(trace.sensor_data.model_dump(), indent=2)}

ORIGINAL SYSTEM PROMPT (excerpt):
{trace.model_prompt[:1200]}

GEMMA'S RESPONSE:
{trace.model_response}

EVALUATION FAILURES:
{issues}

Your job: draft a targeted prompt patch that would fix this class of inference error on the vessel's hardware.

Think step by step as the Fleet Mechanic, then produce a JSON patch with:
- patch_type: "system_instruction" | "few_shot_example" | "rag_addition"
- original_section: the problematic part of the prompt (or "N/A — missing instruction")
- patched_section: the improved or new prompt text to push to the boat
- rationale: why this specific change fixes the failure
- agent_reasoning: your full reasoning chain as Fleet Mechanic"""

        try:
            response = self._genai.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_PATCH_SCHEMA,
                    temperature=0.2,
                ),
            )
            data = json.loads(response.text)
            return {
                "phoenix_trace_id": phoenix_trace_id,
                "patch_type": data.get("patch_type", "system_instruction"),
                "original_prompt_section": data.get("original_section", ""),
                "patched_prompt_section": data.get("patched_section", ""),
                "rationale": data.get("rationale", ""),
                "agent_reasoning": data.get("agent_reasoning", ""),
                "status": "pending",
            }
        except Exception as exc:
            logger.error(f"Patch drafting failed: {exc}")
            return {
                "phoenix_trace_id": phoenix_trace_id,
                "patch_type": "system_instruction",
                "original_prompt_section": "",
                "patched_prompt_section": f"[Auto-patch failed — manual review required: {exc}]",
                "rationale": "Patch generation error; inspect trace manually.",
                "agent_reasoning": str(exc),
                "status": "pending",
            }

    @staticmethod
    def _build_summary(total: int, flagged: int) -> str:
        healthy = total - flagged
        if flagged == 0:
            return (
                f"All {total} offshore traces passed evaluation. "
                "The vessel's Gemma model performed correctly on this voyage."
            )
        return (
            f"{total} traces analyzed: {healthy} passed, {flagged} flagged. "
            f"Prompt patches queued — review and deploy before vessel departs."
        )
