"use client";

import { useEffect, useState } from "react";
import { fetchSetupStatus, setMode } from "@/lib/setup";
import type { SetupStatus } from "@/lib/setup";
import { useToast } from "@/components/ui/Toast";
import { LocalSetupGuide } from "./LocalSetupGuide";

export function CloudBanner() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [switching, setSwitching] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const { showToast } = useToast();

  async function refresh() {
    try {
      setStatus(await fetchSetupStatus());
    } catch {
      // OfflineBanner handles backend-unreachable state
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
  }, []);

  async function handleSwitch(target: "cloud" | "local") {
    setSwitching(true);
    try {
      await setMode(target);
      await refresh();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Switch failed";
      showToast(msg, "error");
      setShowGuide(true); // Pop the guide automatically on failure
    } finally {
      setSwitching(false);
    }
  }

  if (!status) return null;

  const ollamaReady = status.ollama_installed && status.ollama_running && status.model_ready;

  if (status.mode === "cloud") {
    return (
      <div className="sticky top-0 z-50 bg-amber-400 text-amber-950 text-sm font-semibold px-4 py-2 flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
        <span>☁ Cloud — running <strong>Gemma</strong> via Google AI Studio.</span>
        {!status.server_is_local ? (
          <span className="text-xs text-amber-800">
            Local AI requires running the backend on your own machine.
          </span>
        ) : ollamaReady ? (
          <button
            onClick={() => handleSwitch("local")}
            disabled={switching}
            className="px-3 py-0.5 rounded bg-amber-800 text-white text-xs font-bold hover:bg-amber-900 disabled:opacity-50 transition-colors"
          >
            {switching ? "Switching…" : "Switch to Local Ollama"}
          </button>
        ) : (
          <button
            onClick={() => setShowGuide(true)}
            className="text-xs font-bold underline decoration-amber-600 hover:text-amber-900 transition-colors"
          >
            Setup local AI for offline use →
          </button>
        )}

        <LocalSetupGuide 
          isOpen={showGuide} 
          onClose={() => setShowGuide(false)} 
          status={status} 
        />
      </div>
    );
  }

  // Local mode — subtle green indicator with option to switch back to cloud
  return (
    <div className="sticky top-0 z-50 bg-emerald-700 text-white text-xs font-semibold px-4 py-1.5 flex items-center justify-center gap-3">
      <span>🖥 Local AI — Gemma running on-device via Ollama.</span>
      <button
        onClick={() => handleSwitch("cloud")}
        disabled={switching}
        className="px-2 py-0.5 rounded bg-emerald-900 hover:bg-emerald-950 disabled:opacity-50 transition-colors"
      >
        {switching ? "…" : "Use Cloud"}
      </button>
    </div>
  );
}
