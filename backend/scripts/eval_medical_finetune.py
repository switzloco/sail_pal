"""
Eval: Unsloth fine-tune vs vanilla Gemma 4 on WHO IMGS medical Q&A.

Runs a held-out set of maritime medical questions through both models via the
local Ollama API, then scores each response with Gemini-as-judge (1–10 rubric).
Outputs a markdown comparison table. Re-run this after any change to the
medical routing or grounding prompts to confirm answer quality hasn't regressed.

Usage:
    GOOGLE_API_KEY=<key> python -m backend.scripts.eval_medical_finetune
    # Or with explicit model overrides:
    BASELINE_MODEL=gemma4:e2b MEDICAL_MODEL=hf.co/nswitzer/gemma4-maritime-medical-GGUF \\
        GOOGLE_API_KEY=<key> python -m backend.scripts.eval_medical_finetune

Requirements:
    - Ollama running locally (http://localhost:11434)
    - Both models pulled: ollama pull gemma4:e2b
                          ollama pull hf.co/nswitzer/gemma4-maritime-medical-GGUF
    - GOOGLE_API_KEY set for Gemini-as-judge scoring (optional; skips scoring if absent)

Output files written to backend/data/eval/:
    - eval_results.jsonl      raw per-question scores
    - eval_report.md          markdown comparison table
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = REPO_ROOT / "backend" / "data" / "knowledge" / "who_imgs.json"
OUTPUT_DIR = REPO_ROOT / "backend" / "data" / "eval"

BASELINE_MODEL = os.getenv("BASELINE_MODEL", "gemma4:e2b")
MEDICAL_MODEL = os.getenv(
    "MEDICAL_MODEL",
    os.getenv("MODEL_MEDICAL", "hf.co/nswitzer/gemma4-maritime-medical-GGUF"),
)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

JUDGE_MODEL = "gemma-2.0-flash"   # fast, cheap; swap to gemini-1.5-flash if unavailable

# ── Hard-coded held-out test questions ────────────────────────────────────────
# These are drawn from WHO IMGS topics NOT included in the first 600 training
# chunks (training used pages 1-340; these span pages 341-420 and appendices).
# Also includes 10 general maritime questions to check regression.

MEDICAL_QUESTIONS: list[dict[str, str]] = [
    # Pharmacology / dosing (p.341+)
    {
        "question": "What is the recommended adult oral dose of amoxicillin for a chest infection at sea, and how long should treatment continue?",
        "domain": "medical",
        "topic": "pharmacology",
    },
    {
        "question": "A sailor has been stung by a jellyfish and is experiencing urticaria. What antihistamine is available on the ship's medicine chest and what dose should be given?",
        "domain": "medical",
        "topic": "envenomation",
    },
    {
        "question": "The MPIC needs to give an intramuscular injection. Describe the correct site and technique to avoid hitting the sciatic nerve.",
        "domain": "medical",
        "topic": "procedures",
    },
    {
        "question": "A crew member has been prescribed metronidazole. What food interaction must they be warned about?",
        "domain": "medical",
        "topic": "pharmacology",
    },
    {
        "question": "What are the WHO IMGS criteria for deciding to evacuate a patient with a suspected appendicitis versus managing on board?",
        "domain": "medical",
        "topic": "surgical emergencies",
    },
    # Burns and trauma (p.80+, advanced)
    {
        "question": "How do you estimate the percentage body surface area burned using the Rule of Nines? Give the percentage for the head, each arm, each leg, and the torso.",
        "domain": "medical",
        "topic": "burns",
    },
    {
        "question": "A crew member has a deep second-degree burn covering approximately 20% BSA. What is the fluid resuscitation formula and how much fluid should be given in the first 8 hours?",
        "domain": "medical",
        "topic": "burns",
    },
    {
        "question": "Describe the WHO IMGS approach to wound closure for a laceration on the scalp. When is it appropriate to close with adhesive strips vs sutures?",
        "domain": "medical",
        "topic": "wounds",
    },
    # Cardiac and chest (p.155+)
    {
        "question": "A 52-year-old Chief Engineer has crushing central chest pain radiating to the left arm. What drugs does the ship's medicine chest have for suspected ACS, and what doses should be given?",
        "domain": "medical",
        "topic": "cardiac",
    },
    {
        "question": "What are the WHO IMGS signs distinguishing a tension pneumothorax from a simple pneumothorax, and what emergency intervention is indicated?",
        "domain": "medical",
        "topic": "chest",
    },
    # Infectious disease
    {
        "question": "A crew member returns from shore leave in a tropical port with fever, rigors, and headache 10 days later. What is the most likely diagnosis and what WHO IMGS guidance applies?",
        "domain": "medical",
        "topic": "tropical medicine",
    },
    {
        "question": "What is the WHO IMGS definition of a medical emergency requiring radio medical advice, and what information should the MPIC prepare before calling?",
        "domain": "medical",
        "topic": "telemedicine",
    },
    # Obstetrics / gynecology
    {
        "question": "A crew member who is 36 weeks pregnant goes into labour at sea. What immediate steps should the MPIC take and what equipment will be needed?",
        "domain": "medical",
        "topic": "obstetrics",
    },
    # Mental health
    {
        "question": "A crew member is exhibiting acute psychosis — disorganised speech and aggression. What pharmacological intervention does the WHO IMGS recommend and what dose?",
        "domain": "medical",
        "topic": "mental health",
    },
    # Anatomy questions that test memorisation of WHO IMGS structure
    {
        "question": "According to the WHO IMGS anatomy chapter, where is the liver located relative to the diaphragm and what physical signs suggest hepatomegaly?",
        "domain": "medical",
        "topic": "anatomy",
    },
    # Poisoning
    {
        "question": "A crew member accidentally ingested a cleaning product containing sodium hydroxide (lye). Should vomiting be induced? What does WHO IMGS recommend?",
        "domain": "medical",
        "topic": "poisoning",
    },
    # Eye injuries
    {
        "question": "A welder's assistant has a chemical splash to both eyes. Describe the WHO IMGS irrigation procedure and how long it should continue.",
        "domain": "medical",
        "topic": "eye injuries",
    },
    # Vital signs / assessment
    {
        "question": "What vital signs should the MPIC record for a seriously ill patient, and at what frequency does the WHO IMGS recommend recording them?",
        "domain": "medical",
        "topic": "assessment",
    },
    # Dental
    {
        "question": "A crew member has severe toothache at sea with signs of dental abscess. What antibiotic and analgesic regimen does the WHO IMGS recommend?",
        "domain": "medical",
        "topic": "dental",
    },
    # Hypothermia
    {
        "question": "A sailor pulled from cold water has a core temperature of 30°C and is unconscious. What does the WHO IMGS say about rewarming technique and CPR in severe hypothermia?",
        "domain": "medical",
        "topic": "hypothermia",
    },
]

# General maritime / engineering questions — fine-tune should NOT improve these
# (used as a regression check: we expect similar scores from both models)
GENERAL_QUESTIONS: list[dict[str, str]] = [
    {
        "question": "What are the SOLAS requirements for the number of survival craft a cargo ship must carry?",
        "domain": "general",
        "topic": "SOLAS",
    },
    {
        "question": "Explain how a centrifugal pump primes itself and what causes cavitation.",
        "domain": "general",
        "topic": "engineering",
    },
    {
        "question": "What is the difference between a four-stroke and two-stroke diesel engine in terms of power stroke frequency?",
        "domain": "general",
        "topic": "engineering",
    },
    {
        "question": "What does ISM Code require the master to do after a near-miss incident?",
        "domain": "general",
        "topic": "safety management",
    },
    {
        "question": "Describe the fire triangle and explain how CO2 extinguishers suppress fire.",
        "domain": "general",
        "topic": "fire safety",
    },
    {
        "question": "What is the purpose of a bilge alarm and at what level does it typically activate?",
        "domain": "general",
        "topic": "engineering",
    },
    {
        "question": "What navigational lights must a vessel under 50 metres show when underway at night?",
        "domain": "general",
        "topic": "navigation",
    },
    {
        "question": "What is a Mayday call and what information must it contain according to GMDSS procedure?",
        "domain": "general",
        "topic": "communications",
    },
    {
        "question": "Explain the difference between true wind and apparent wind.",
        "domain": "general",
        "topic": "sailing",
    },
    {
        "question": "What is cathodic protection and why is it used on ship hulls?",
        "domain": "general",
        "topic": "engineering",
    },
]

ALL_QUESTIONS = MEDICAL_QUESTIONS + GENERAL_QUESTIONS

MEDICAL_SYSTEM = (
    "You are a maritime medical assistant trained on the WHO International Medical "
    "Guide for Ships (3rd Edition). Provide accurate, actionable guidance for "
    "emergencies at sea. Cite the relevant WHO IMGS page number when you reference "
    "a specific protocol or dosage."
)

JUDGE_PROMPT_TEMPLATE = """You are evaluating an AI response to a maritime question.

Question: {question}
Domain: {domain} ({topic})

Response to evaluate:
---
{response}
---

Score this response from 1 to 10 on each of these criteria:
1. **Accuracy** — Is the information factually correct for maritime/medical use?
2. **Specificity** — Does it give concrete actionable details (doses, quantities, procedures)?
3. **Citation quality** — For medical questions, does it cite WHO IMGS page numbers or protocols?
4. **Hallucination risk** — Does it invent specific numbers or protocols it shouldn't know? (10 = no hallucination, 1 = serious fabrications)

Respond with ONLY a JSON object, no other text:
{{"accuracy": <1-10>, "specificity": <1-10>, "citation": <1-10>, "hallucination": <1-10>, "reasoning": "<one sentence>"}}"""


# ── Ollama helper ──────────────────────────────────────────────────────────────

async def ollama_generate(
    model: str,
    system: str,
    prompt: str,
    timeout: float = 120.0,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 512},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


async def check_model_available(model: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            tags = resp.json()
            models = [m["name"] for m in tags.get("models", [])]
            # Ollama may store hf.co/ models with different tag format
            return any(model in m or m in model for m in models)
    except Exception:
        return False


# ── Gemini judge ───────────────────────────────────────────────────────────────

async def gemini_score(
    question: str,
    domain: str,
    topic: str,
    response: str,
) -> dict[str, Any] | None:
    if not GOOGLE_API_KEY:
        return None

    prompt = JUDGE_PROMPT_TEMPLATE.format(
        question=question, domain=domain, topic=topic, response=response
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{JUDGE_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Strip markdown code fences if present
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()
            return json.loads(text)
    except Exception as exc:
        print(f"    [judge error] {exc}", file=sys.stderr)
        return None


# ── Main eval loop ─────────────────────────────────────────────────────────────

async def run_eval() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUTPUT_DIR / "eval_results.jsonl"
    report_path = OUTPUT_DIR / "eval_report.md"

    print(f"Baseline model : {BASELINE_MODEL}")
    print(f"Medical model  : {MEDICAL_MODEL}")
    print(f"Ollama URL     : {OLLAMA_URL}")
    print(f"Gemini judge   : {'enabled' if GOOGLE_API_KEY else 'DISABLED (no GOOGLE_API_KEY)'}")
    print()

    # Check Ollama is reachable
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(f"{OLLAMA_URL}/api/tags")
    except Exception:
        print(f"ERROR: Cannot reach Ollama at {OLLAMA_URL}. Is it running?", file=sys.stderr)
        sys.exit(1)

    baseline_available = await check_model_available(BASELINE_MODEL)
    medical_available = await check_model_available(MEDICAL_MODEL)

    if not baseline_available:
        print(f"WARNING: {BASELINE_MODEL} not found in Ollama. Responses will fail.", file=sys.stderr)
    if not medical_available:
        print(f"WARNING: {MEDICAL_MODEL} not found in Ollama. Responses will fail.", file=sys.stderr)
        print(f"  Pull it with: ollama pull {MEDICAL_MODEL}", file=sys.stderr)

    results: list[dict[str, Any]] = []

    for i, q in enumerate(ALL_QUESTIONS, 1):
        question = q["question"]
        domain = q["domain"]
        topic = q["topic"]
        system = MEDICAL_SYSTEM if domain == "medical" else "You are a knowledgeable maritime professional."

        print(f"[{i:2d}/{len(ALL_QUESTIONS)}] {domain:8s} / {topic}")
        print(f"         Q: {question[:80]}...")

        row: dict[str, Any] = {"question": question, "domain": domain, "topic": topic}

        # Query both models
        for label, model in [("baseline", BASELINE_MODEL), ("finetuned", MEDICAL_MODEL)]:
            t0 = time.monotonic()
            try:
                response = await ollama_generate(model, system, question)
                elapsed = time.monotonic() - t0
                print(f"         {label:10s}: {len(response)} chars in {elapsed:.1f}s")
            except Exception as exc:
                response = f"[ERROR: {exc}]"
                elapsed = 0.0
                print(f"         {label:10s}: ERROR — {exc}", file=sys.stderr)

            row[f"{label}_response"] = response
            row[f"{label}_latency"] = round(elapsed, 2)

            # Score with Gemini
            if GOOGLE_API_KEY:
                scores = await gemini_score(question, domain, topic, response)
                row[f"{label}_scores"] = scores
                if scores:
                    avg = sum(scores[k] for k in ("accuracy", "specificity", "citation", "hallucination")) / 4
                    print(f"         {label:10s}: judge avg={avg:.1f}  ({scores.get('reasoning','')[:60]})")
                await asyncio.sleep(0.5)  # rate limit Gemini

        results.append(row)

        # Flush after every question so a crash doesn't lose data
        with open(results_path, "a") as f:
            f.write(json.dumps(row) + "\n")

    # ── Build report ──────────────────────────────────────────────────────────
    _write_report(results, report_path)
    print(f"\nResults written to {results_path}")
    print(f"Report written  to {report_path}")


def _composite(scores: dict | None) -> float | None:
    if not scores:
        return None
    return round(
        sum(scores[k] for k in ("accuracy", "specificity", "citation", "hallucination")) / 4,
        1,
    )


def _write_report(results: list[dict], path: Path) -> None:
    medical = [r for r in results if r["domain"] == "medical"]
    general = [r for r in results if r["domain"] == "general"]

    def avg_score(rows: list[dict], label: str) -> str:
        scores = [_composite(r.get(f"{label}_scores")) for r in rows]
        scores = [s for s in scores if s is not None]
        return f"{sum(scores)/len(scores):.1f}" if scores else "n/a"

    def avg_latency(rows: list[dict], label: str) -> str:
        lats = [r.get(f"{label}_latency", 0) for r in rows]
        return f"{sum(lats)/len(lats):.1f}s"

    lines: list[str] = []

    lines += [
        "## Eval: Unsloth Fine-tune vs Vanilla Gemma 4",
        "",
        f"**Baseline:** `{BASELINE_MODEL}`  ",
        f"**Fine-tune:** `{MEDICAL_MODEL}`  ",
        f"**Scoring:** Gemini-as-judge (1–10 per axis: accuracy, specificity, citation quality, anti-hallucination)  ",
        f"**Questions:** {len(medical)} held-out WHO IMGS medical + {len(general)} general maritime (regression check)  ",
        "",
    ]

    # Summary table
    lines += [
        "### Summary",
        "",
        "| Category | Questions | Baseline avg score | Fine-tune avg score | Baseline latency | Fine-tune latency |",
        "|----------|-----------|-------------------|---------------------|-----------------|-------------------|",
        f"| Medical (WHO IMGS) | {len(medical)} | {avg_score(medical, 'baseline')} | {avg_score(medical, 'finetuned')} | {avg_latency(medical, 'baseline')} | {avg_latency(medical, 'finetuned')} |",
        f"| General maritime   | {len(general)} | {avg_score(general, 'baseline')} | {avg_score(general, 'finetuned')} | {avg_latency(general, 'baseline')} | {avg_latency(general, 'finetuned')} |",
        "",
        "> Scores are means of four 1–10 axes. General maritime questions serve as a **regression check** — "
        "both models should score similarly here; a large drop would indicate the fine-tune hurt general capability.",
        "",
    ]

    # Per-question breakdown
    lines += [
        "### Per-question scores (medical)",
        "",
        "| Topic | Question (truncated) | Baseline | Fine-tune | Delta |",
        "|-------|---------------------|----------|-----------|-------|",
    ]
    for r in medical:
        b = _composite(r.get("baseline_scores"))
        f = _composite(r.get("finetuned_scores"))
        delta = f"**+{f-b:.1f}**" if (b and f and f > b) else (f"{f-b:.1f}" if (b and f) else "n/a")
        bs = f"{b:.1f}" if b else "n/a"
        fs = f"{f:.1f}" if f else "n/a"
        q_trunc = r["question"][:65].replace("|", "\\|") + "…"
        lines.append(f"| {r['topic']} | {q_trunc} | {bs} | {fs} | {delta} |")

    lines += [
        "",
        "### Per-question scores (general maritime — regression check)",
        "",
        "| Topic | Question (truncated) | Baseline | Fine-tune | Delta |",
        "|-------|---------------------|----------|-----------|-------|",
    ]
    for r in general:
        b = _composite(r.get("baseline_scores"))
        f = _composite(r.get("finetuned_scores"))
        delta = f"**+{f-b:.1f}**" if (b and f and f > b) else (f"{f-b:.1f}" if (b and f) else "n/a")
        bs = f"{b:.1f}" if b else "n/a"
        fs = f"{f:.1f}" if f else "n/a"
        q_trunc = r["question"][:65].replace("|", "\\|") + "…"
        lines.append(f"| {r['topic']} | {q_trunc} | {bs} | {fs} | {delta} |")

    # Sample responses
    lines += ["", "### Sample responses (first medical question)", ""]
    if medical:
        r = medical[0]
        lines += [
            f"**Question:** {r['question']}",
            "",
            f"**Baseline (`{BASELINE_MODEL}`):**",
            "```",
            (r.get("baseline_response") or "no response")[:600],
            "```",
            "",
            f"**Fine-tune (`{MEDICAL_MODEL}`):**",
            "```",
            (r.get("finetuned_response") or "no response")[:600],
            "```",
            "",
        ]

    path.write_text("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(run_eval())
