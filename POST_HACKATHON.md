# Post-hackathon backlog

Things deliberately deferred during the Gemma 4 Good Hackathon submission.
Captured at the point of deferral so future-me doesn't have to re-diagnose.

---

## Logging UX (health events + maintenance logs)

**Symptom:** Forms feel clunky. Two underlying causes.

### 1. Too many fields

Both `/health` and `/maintenance` log forms expose every column from the
schema. A crew member in the middle of an incident doesn't have time
to fill out 8+ inputs.

**What to do:**
- Keep only the **3 required-at-incident-time** fields visible by default:
  - Health: `crew_member`, `symptoms`, `severity`
  - Maintenance: `component`, `issue`, `severity`
- Collapse the rest (vitals, allergies snapshot, parts list, hours-since-service,
  etc.) behind a single "More details" disclosure.
- The collapsed fields are useful *after* the fact for sync-to-shore reports,
  but they shouldn't gate logging the incident in the first place.

**Touch points:**
- `frontend/src/app/health/` (event form)
- `frontend/src/app/maintenance/` (log form)
- Backend schemas already accept null on most non-required fields; no
  migration needed. Confirm with `backend/db/models.py` before shipping.

### 2. No upfront explanation of what the log is for

Users land on the form with no framing — they don't know if this goes
to shore, who reads it, why they're logging at all. That ambiguity is
half the friction.

**What to do:**
- Add a one-paragraph intro card above each log form explaining:
  - **Health:** "Logged here so the AI can reference history on follow-up
    queries, and so shore-side TMAS can read the full incident timeline
    once you're back in range. Stays on this laptop until then."
  - **Maintenance:** "Logged here so the engine analyzer has context on
    prior faults, and so the next port can see the running history.
    Stays on this laptop until you sync."
- Tie that copy explicitly to the offline-first / sync-queue story —
  it's a differentiator and users currently can't tell.

### Out of scope (maybe later)

- "Log this from chat" — surface a "Save as health event" button when
  the AI's response identifies a treatable condition. Cuts the
  type-it-twice problem but adds complexity; not worth shipping unless
  we have user feedback that the current form is still the blocker
  after the above changes.
