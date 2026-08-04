# Hackathon archive

Materials from Vessel Ops AI's original submission to the **Gemma 4 Good Hackathon**
(Kaggle × Google DeepMind, May 2026).

These are kept for provenance. They are **not maintained** and describe the app as it
stood at submission — before it was pared back to the Medical and Inventory pillars.
Where they disagree with the [README](../../../README.md) or
[CLAUDE.md](../../../CLAUDE.md), those are correct and this folder is not.

| File | What it is |
|------|------------|
| `KAGGLE_WRITEUP.md` | Competition writeup — fine-tune methodology, eval results, architecture rationale. Still the best single explanation of *why* the medical fine-tune exists. |
| `Competition Info.txt` | Hackathon rules, prize tracks, and judging criteria. |
| `SOCIAL_POSTS.md` | Launch post drafts (r/sailing, LocalLLaMA, Hacker News, LinkedIn). |
| `VIDEO_SCRIPT.md` | Demo video script. |
| `VIDEO_SCRIPT_ALT.md` | Alternate demo video script (credibility-led cut). |

The technical artifacts these reference are still live and still maintained:

- [`notebooks/unsloth_finetune.ipynb`](../../../notebooks/unsloth_finetune.ipynb) — fine-tune training
- [`notebooks/eval_medical_finetune.ipynb`](../../../notebooks/eval_medical_finetune.ipynb) — fine-tune vs. base bake-off
- [`hf.co/nswitzer/gemma4-maritime-medical-GGUF`](https://huggingface.co/nswitzer/gemma4-maritime-medical-GGUF) — the published model

If a future hackathon comes around, start here rather than from scratch.
