# Arize Integration — Medical Triage Agent

Vessel Ops AI's medical flow is built as a **multi-step agent** that is fully
observable and self-evaluated with **Arize**. This is the project's submission
for the **Arize partner track** of the Google Cloud Rapid Agent Hackathon.

## Why this is an agent, not a chatbot

`POST /api/ai/medical-agent` doesn't just answer a question — it **plans a
mission, uses tools, and finishes the job** while keeping the Medical Person in
Charge (MPIC) in control. For each case the agent:

| # | Step | Span kind | What it does |
|---|------|-----------|--------------|
| 1 | **Plan** | `AGENT` | Advertises the steps it will take |
| 2 | `lookup_crew_member` | `TOOL` | Pulls the patient record (allergies, history) from the DB |
| 3 | `retrieve_protocol` | `RETRIEVER` | RAG over WHO IMGS / Ship Captain's Medical Guide |
| 4 | `assess_patient` | `LLM` | Drafts grounded, cited treatment guidance |
| 5 | `evaluate_guidance` | `EVALUATOR` | **Arize groundedness guardrail** (LLM-as-judge) |
| 6 | *(conditional)* regenerate | — | If the guardrail fails, regenerate once with stricter grounding |
| 7 | `log_health_event` | `TOOL` | Writes the outcome to the health record |

The guardrail is the point: at sea, a hallucinated dosage is dangerous. Every
answer is scored for how well it is supported by the retrieved protocol before
it is shown and logged. Low-scoring answers are regenerated and flagged for
human follow-up.

## The two Arize integration surfaces

### 1. Tracing & evals (instrumentation → Arize)

`backend/ai/tracing.py` sets up OpenTelemetry / OpenInference tracing:

- **Arize AX** (hosted cloud) when `ARIZE_API_KEY` + `ARIZE_SPACE_ID` are set.
- **Arize Phoenix** (open-source / self-hosted) otherwise — matching the app's
  offline-first design.

Every step above becomes a span with OpenInference semantic-convention
attributes, and the groundedness verdict is recorded as an `EVALUATOR` span, so
the full reasoning trace + safety score lands in Arize.

All observability deps are **optional** (`backend/requirements-observability.txt`).
The lean offline desktop bundle omits them and tracing degrades to a no-op — a
laptop at sea has nothing to phone home to. Tracing is a hosted-mode concern.

### 2. MCP server (Arize → agent)

`.mcp.json` registers the official **Arize Phoenix MCP server**
(`@arizeai/phoenix-mcp`). This gives an MCP client (Claude, Cursor, or a Google
Cloud Agent Builder agent) tools to query the traces, spans, datasets, and
experiments this app produces — closing the loop from "agent emits traces" to
"agent can reason over its own observability data."

## Running it locally with Phoenix

```bash
# 1. Install the optional observability extras
pip install -r backend/requirements-observability.txt

# 2. Start a local Phoenix collector (UI at http://localhost:6006)
python -m phoenix.server.main serve

# 3. Run the backend (tracing auto-targets local Phoenix)
bash scripts/start.sh        # or: uvicorn backend.main:app --port 8000

# 4. Trigger the agent (or use the “Triage Agent” page in the UI)
curl -N -X POST http://localhost:8000/api/ai/medical-agent \
  -H 'Content-Type: application/json' \
  -d '{"crew_id":"<id>","symptoms":["fever","abdominal pain"],"severity":"serious"}'
```

Open Phoenix → project `vessel-ops-medical` to see the agent trace and the
groundedness eval on each generation.

## Sending traces to Arize AX (hosted)

Set both secrets and traces route to Arize AX instead of Phoenix:

```bash
export ARIZE_API_KEY=...      # app.arize.com → Space Settings
export ARIZE_SPACE_ID=...
```

For Cloud Run, add them as secrets and uncomment the `--set-secrets` line in
`cloudbuild.yaml`.

## Configuration reference

| Env var | Default | Purpose |
|---------|---------|---------|
| `ARIZE_TRACING_ENABLED` | `true` | Master on/off switch |
| `ARIZE_PROJECT_NAME` | `vessel-ops-medical` | Project/app name in Arize/Phoenix |
| `ARIZE_API_KEY` | — | Arize AX API key (enables AX) |
| `ARIZE_SPACE_ID` | — | Arize AX space id (enables AX) |
| `PHOENIX_COLLECTOR_ENDPOINT` | local Phoenix | Phoenix collector URL |
