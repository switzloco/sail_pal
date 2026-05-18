---
license: apache-2.0
language:
- en
base_model: unsloth/gemma-4-e2b-it-unsloth-bnb-4bit
library_name: gguf
tags:
- gemma4
- unsloth
- maritime
- medical
- who-imgs
- gguf
- q4_k_m
- ollama
- llama.cpp
- offline
quantized_by: nswitzer
---

# Gemma 4 Maritime Medical — GGUF

A Gemma 4 2B model fine-tuned on the **World Health Organization International Medical Guide for Ships, 3rd Edition** (WHO IMGS), quantized to Q4_K_M for offline inference via Ollama or llama.cpp.

Built for **[Vessel Ops AI](https://github.com/switzloco/sail_pal)** — an offline-first medical and engineering assistant for vessels operating in deep-water environments where there is no doctor and no internet.

---

## What this model is for

Maritime medical decision support at sea, where the Medical Person In Charge (MPIC) is a crew member — not a physician — and there is no shoreside telemedicine available. The model is fine-tuned to speak fluently in the dosages, drug names, and protocol structures used by the WHO IMGS, which is the de-facto standard medical reference carried by commercial vessels.

It is intentionally specialised. It is **not** a general medical assistant. Engine repairs, regulations, navigation, and general health questions should use the vanilla Gemma 4 base model instead — the Vessel Ops AI installer pulls both and routes traffic appropriately.

---

## Quick start — Ollama

```bash
ollama pull hf.co/nswitzer/gemma4-maritime-medical-GGUF
ollama run hf.co/nswitzer/gemma4-maritime-medical-GGUF
```

Then ask:
> *A crew member has a deep laceration on the forearm with arterial bleeding. What should the MPIC do?*

For best results, wrap calls in a retrieval-augmented prompt that injects the relevant WHO IMGS passages with page citations — that is what Vessel Ops AI does on every medical query, and it dramatically reduces hallucination on specific dosages.

---

## Training

| | |
|---|---|
| **Base model** | `unsloth/gemma-4-e2b-it-unsloth-bnb-4bit` |
| **Method** | QLoRA (rank 16, RSLoRA scaling) via [Unsloth](https://github.com/unslothai/unsloth) |
| **Dataset** | ~1,400 clinical Q&A pairs generated from the 938-chunk WHO IMGS index by Gemini, in ShareGPT format |
| **Hardware** | Free Kaggle T4 (16 GB VRAM) |
| **Time** | ~3 hours, 3 epochs, cosine LR schedule |
| **Quantization** | Q4_K_M GGUF (~1.3 GB) via `model.push_to_hub_gguf` |

Training notebook: [kaggle.com/code/nswitzer/vessel-ops-extra-credit](https://www.kaggle.com/code/nswitzer/vessel-ops-extra-credit)

The Unsloth training pipeline is what made this fine-tune feasible on free hardware — ~2× faster than vanilla HuggingFace Trainer with ~70% less VRAM. A shipping company could re-run the same notebook on their own fleet's incident history in an afternoon and get a deployable Ollama model out the other end.

---

## Hardware requirements (inference)

| Laptop RAM | Expected response time |
|------------|------------------------|
| 8 GB       | 10–15 seconds per response |
| 16 GB      | 5–10 seconds per response |
| 32 GB+     | 3–5 seconds, or move to `gemma4:e4b` for stronger reasoning |

CPU-only inference works fine — no GPU required. This is the entire point of the GGUF/Ollama stack: usable AI on whatever laptop is already in the wheelhouse.

---

## Limitations and disclaimer

This is an AI assistant intended as a **second opinion** when no physician is reachable. It is not a substitute for medical training or for shoreside telemedicine (TMAS). Every Vessel Ops AI response carries this disclaimer:

> *AI-generated guidance. Verify against physical manuals. Contact rescue services if situation is life-threatening.*

The model:

- Inherits all biases and limitations of the base Gemma 4 2B model
- Has been specialised on the WHO IMGS specifically — it will be less reliable on medical content outside that corpus
- Should **always** be paired with retrieval over the source manual at inference time. The fine-tune helps with vocabulary and structure; RAG is what keeps the page-cited dosages honest.

---

## Citation

The training corpus is derived from:

> *World Health Organization. International Medical Guide for Ships, 3rd Edition. WHO Press, 2007.*

Please consult the original WHO publication for authoritative medical guidance.

---

## Links

- **App on GitHub:** [github.com/switzloco/sail_pal](https://github.com/switzloco/sail_pal)
- **Training notebook (Kaggle):** [kaggle.com/code/nswitzer/vessel-ops-extra-credit](https://www.kaggle.com/code/nswitzer/vessel-ops-extra-credit)
- **LoRA adapter (Transformers):** [nswitzer/gemma4-maritime-medical](https://huggingface.co/nswitzer/gemma4-maritime-medical)
- **Unsloth:** [unsloth.ai](https://unsloth.ai) · [github.com/unslothai/unsloth](https://github.com/unslothai/unsloth)
