"""Fleet Mechanic — dockside evaluation of offline vessel inferences.

This package is the *cloud* half of the loop. The vessel captures offline
inference traces into SQLite (`backend.ai.trace`); when it reaches the marina
and syncs, the Fleet Mechanic:

  1. replays those traces into Arize as OpenInference LLM spans,
  2. runs a Gemini LLM-as-judge hallucination / groundedness eval over each,
  3. drafts a prompt patch for any inference flagged unsafe or unsupported, and
  4. queues that patch to push back to the vessel before it leaves the dock.

Nothing here runs on the boat. It only activates when Arize/Gemini credentials
are present, so the offline edge build stays dependency-light.
"""
