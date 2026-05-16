"""
Generate instruction-tuning Q&A pairs from WHO IMGS chunks for Unsloth fine-tuning.

Uses the Gemini API to produce high-quality clinical maritime Q&A from the
938-chunk WHO IMGS corpus. Saves incremental JSONL so the run can be resumed
if interrupted. Falls back to template-based generation when no API key is set.

Output: backend/data/training/who_imgs_qa.jsonl
Format: one JSON object per line, ShareGPT conversations format:
    {"conversations": [{"from": "human", "value": "..."}, {"from": "gpt", "value": "..."}]}

Run:
    GOOGLE_API_KEY=... python -m backend.scripts.generate_training_data
    # or without API key for template-based fallback:
    python -m backend.scripts.generate_training_data
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = REPO_ROOT / "backend" / "data" / "knowledge" / "who_imgs.json"
OUTPUT_PATH = REPO_ROOT / "backend" / "data" / "training" / "who_imgs_qa.jsonl"

# Chunks shorter than this are likely TOC entries or page headers — skip them.
MIN_CHUNK_CHARS = 250

# Gemini call budget: ~2 calls/sec on free tier
RATE_LIMIT_DELAY = 0.6

SYSTEM_PROMPT = (
    "You are an expert maritime medicine assistant trained on the WHO International "
    "Medical Guide for Ships (3rd Edition). You provide accurate, concise medical "
    "guidance to ship officers managing emergencies at sea with no doctor available. "
    "Always cite the relevant WHO IMGS page number when referencing specific protocols."
)

QA_GENERATION_PROMPT = """You are creating training data for a maritime medical AI assistant.

Given this excerpt from the WHO International Medical Guide for Ships (3rd Edition, page {page}):

---
{text}
---

Generate exactly 2 realistic question-answer pairs that a ship's officer might need during a medical emergency at sea. Each answer must:
1. Be grounded ONLY in the provided excerpt
2. Include the page number citation: (WHO IMGS, p.{page})
3. Be practical and actionable for a non-medical professional

Respond with valid JSON only, no markdown, in this exact format:
[
  {{"question": "...", "answer": "..."}},
  {{"question": "...", "answer": "..."}}
]"""


def _is_toc_chunk(text: str) -> bool:
    """Return True for table-of-contents and page-header chunks."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 3:
        return True
    # TOC lines look like "Some Title  42" — lots of trailing numbers
    numeric_lines = sum(1 for l in lines if re.search(r"\s+\d+\s*$", l))
    return numeric_lines > len(lines) * 0.5


def _load_chunks() -> List[Dict]:
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    chunks = data["chunks"]
    good = [
        c for c in chunks
        if len(c["text"]) >= MIN_CHUNK_CHARS and not _is_toc_chunk(c["text"])
    ]
    print(f"Loaded {len(chunks)} chunks → {len(good)} usable after filtering")
    return good


def _load_done_ids(path: Path) -> set:
    done = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    done.add(obj.get("chunk_id", ""))
                except json.JSONDecodeError:
                    pass
    return done


def _template_qa(chunk: Dict) -> List[Dict]:
    """Fallback: produce one simple Q&A from a chunk without an API call."""
    text = chunk["text"].strip()
    page = chunk["metadata"]["page"]
    # Extract the first sentence as a topic hint
    first_sentence = re.split(r"[.!?]", text)[0].strip()[:120]
    question = f"What does the WHO IMGS recommend regarding: {first_sentence}?"
    answer = (
        f"According to the WHO International Medical Guide for Ships (p.{page}):\n\n"
        f"{text}\n\n(WHO IMGS, p.{page})"
    )
    return [{"question": question, "answer": answer}]


def _gemini_qa(chunk: Dict, api_key: str) -> List[Dict]:
    """Call Gemini to generate Q&A pairs for a chunk."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("google-genai not installed, falling back to template QA", file=sys.stderr)
        return _template_qa(chunk)

    page = chunk["metadata"]["page"]
    prompt = QA_GENERATION_PROMPT.format(page=page, text=chunk["text"])

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        raw = response.text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        pairs = json.loads(raw)
        if not isinstance(pairs, list):
            raise ValueError("Expected list")
        return [
            {"question": p["question"], "answer": p["answer"]}
            for p in pairs
            if isinstance(p, dict) and "question" in p and "answer" in p
        ]
    except Exception as exc:
        print(f"  Gemini error on chunk {chunk['id']}: {exc} — using template", file=sys.stderr)
        return _template_qa(chunk)


def _to_conversation(chunk_id: str, qa: Dict) -> Dict:
    return {
        "chunk_id": chunk_id,
        "conversations": [
            {"from": "system", "value": SYSTEM_PROMPT},
            {"from": "human", "value": qa["question"]},
            {"from": "gpt", "value": qa["answer"]},
        ],
    }


def main() -> None:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        # Try .env file
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
                    break

    mode = "gemini" if api_key else "template"
    print(f"Mode: {mode} {'(set GOOGLE_API_KEY for higher quality)' if mode == 'template' else ''}")

    chunks = _load_chunks()
    done_ids = _load_done_ids(OUTPUT_PATH)
    remaining = [c for c in chunks if c["id"] not in done_ids]
    print(f"Already done: {len(done_ids)} | Remaining: {len(remaining)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "a", encoding="utf-8") as out:
        for i, chunk in enumerate(remaining):
            if mode == "gemini":
                pairs = _gemini_qa(chunk, api_key)
                time.sleep(RATE_LIMIT_DELAY)
            else:
                pairs = _template_qa(chunk)

            for qa in pairs:
                record = _to_conversation(chunk["id"], qa)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()

            if (i + 1) % 50 == 0 or i == len(remaining) - 1:
                print(f"  {i + 1}/{len(remaining)} chunks processed")

    # Count total examples written
    total = sum(1 for _ in open(OUTPUT_PATH, encoding="utf-8"))
    print(f"\nDone. {total} training examples → {OUTPUT_PATH}")
    print("Next: upload who_imgs_qa.jsonl to Kaggle or HuggingFace Datasets, then run notebooks/unsloth_finetune.ipynb")


if __name__ == "__main__":
    main()
