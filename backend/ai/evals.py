"""LLM-as-judge evals for the medical triage agent.

This is the Arize half of the safety story. Every piece of guidance the agent
produces is scored for *groundedness* against the WHO IMGS protocol excerpts it
retrieved — the same pattern as Arize Phoenix's hallucination / groundedness
eval templates. A low score means the model invented a clinical claim or
dosage, which is dangerous at sea, so the agent uses this as a guardrail:
regenerate once with stricter grounding, and surface the verdict to the MPIC.

The eval result is also written onto the current trace as an EVALUATOR span so
the score shows up alongside the generation in Arize / Phoenix.
"""
from __future__ import annotations

import json
import re
from typing import Dict, List

from backend.ai import tracing
from backend.ai.llm import llm_complete
from backend.ai.prompt_templates import GROUNDEDNESS_EVAL_PROMPT

# Below this groundedness score the guidance is treated as unsafe and the agent
# regenerates with a stricter grounding instruction.
GROUNDEDNESS_THRESHOLD = 0.6


def _format_context(excerpts: List[Dict]) -> str:
    if not excerpts:
        return "(no protocol excerpts were retrieved)"
    lines = []
    for e in excerpts:
        meta = e.get("metadata", {}) or {}
        source = meta.get("source", "Unknown")
        page = meta.get("page", "?")
        lines.append(f"- {e.get('text', '')} (Source: {source}, p. {page})")
    return "\n".join(lines)


def _parse_verdict(raw: str) -> Dict:
    """Extract the judge's JSON verdict, defaulting safe-but-flagged on failure."""
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            label = str(data.get("label", "")).lower()
            score = float(data.get("score", 0.0))
            score = max(0.0, min(1.0, score))
            return {
                "label": "grounded" if label == "grounded" else "hallucinated",
                "score": score,
                "explanation": str(data.get("explanation", ""))[:500],
            }
    except (ValueError, TypeError, json.JSONDecodeError):
        pass
    # Judge output unparseable → flag for human review rather than pass silently.
    return {
        "label": "unknown",
        "score": 0.0,
        "explanation": "Evaluator response could not be parsed; manual review advised.",
    }


async def evaluate_groundedness(
    question: str,
    answer: str,
    excerpts: List[Dict],
) -> Dict:
    """Score how well `answer` is supported by the retrieved `excerpts`.

    Returns ``{"label", "score", "explanation", "passed"}``. Never raises —
    on any failure it returns a failing verdict so the agent errs toward
    caution and human review.
    """
    context = _format_context(excerpts)
    prompt = GROUNDEDNESS_EVAL_PROMPT.format(
        question=question,
        context=context,
        answer=answer,
    )

    with tracing.span(
        "eval.groundedness",
        kind=tracing.EVALUATOR,
        input_value=answer,
    ) as span:
        try:
            raw = await llm_complete(
                "You are a precise JSON-only clinical safety evaluator.",
                prompt,
            )
            verdict = _parse_verdict(raw)
        except Exception as exc:  # pragma: no cover - defensive
            verdict = {
                "label": "unknown",
                "score": 0.0,
                "explanation": f"Evaluator error: {exc}",
            }

        verdict["passed"] = verdict["score"] >= GROUNDEDNESS_THRESHOLD
        span.set("eval.label", verdict["label"])
        span.set("eval.score", verdict["score"])
        span.set("eval.passed", verdict["passed"])
        span.set_output(verdict["explanation"])

    return verdict
