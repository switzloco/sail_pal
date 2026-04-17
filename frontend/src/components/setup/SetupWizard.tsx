"use client";

import { useEffect, useRef, useState } from "react";
import {
  fetchSetupStatus,
  streamModelPull,
  type PullProgress,
  type SetupStatus,
} from "@/lib/setup";
import { CheckCircle, Circle, Loader2, ExternalLink, Download } from "lucide-react";

type StepState = "pending" | "active" | "done" | "error";

function Step({
  n,
  title,
  subtitle,
  state,
  children,
}: {
  n: number;
  title: string;
  subtitle: string;
  state: StepState;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-xl border p-5 transition-colors ${
        state === "active"
          ? "border-ocean-600 bg-ocean-50"
          : state === "done"
          ? "border-green-200 bg-green-50"
          : state === "error"
          ? "border-red-200 bg-red-50"
          : "border-slate-200 bg-white opacity-60"
      }`}
    >
      <div className="flex items-start gap-4">
        <div className="shrink-0 mt-0.5">
          {state === "done" ? (
            <CheckCircle size={22} className="text-green-600" />
          ) : state === "active" ? (
            <div className="w-6 h-6 rounded-full bg-ocean-700 text-white text-xs font-bold flex items-center justify-center">
              {n}
            </div>
          ) : state === "error" ? (
            <div className="w-6 h-6 rounded-full bg-red-500 text-white text-xs font-bold flex items-center justify-center">
              !
            </div>
          ) : (
            <Circle size={22} className="text-slate-300" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900">{title}</p>
          <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>
          {children && <div className="mt-4">{children}</div>}
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
      <div
        className="bg-ocean-600 h-2.5 rounded-full transition-all duration-300"
        style={{ width: `${Math.min(100, pct)}%` }}
      />
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

export function SetupWizard({ onComplete }: { onComplete: () => void }) {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [checking, setChecking] = useState(true);
  const [pulling, setPulling] = useState(false);
  const [progress, setProgress] = useState<PullProgress | null>(null);
  const [pullError, setPullError] = useState(false);
  const cancelRef = useRef<(() => void) | null>(null);

  async function check() {
    setChecking(true);
    try {
      const s = await fetchSetupStatus();
      setStatus(s);
      if (s.model_ready) onComplete();
    } catch {
      // backend not yet reachable — retry
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    check();
    // poll every 5s so the UI updates when user installs Ollama externally
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, []);

  function startPull() {
    setPulling(true);
    setPullError(false);
    setProgress(null);
    cancelRef.current = streamModelPull(
      (p) => setProgress(p),
      (success) => {
        setPulling(false);
        if (success) {
          check();
        } else {
          setPullError(true);
        }
      },
    );
  }

  useEffect(() => () => { cancelRef.current?.(); }, []);

  if (checking && !status) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 size={32} className="animate-spin text-ocean-600" />
      </div>
    );
  }

  const s = status!;

  // Determine step states
  const step1: StepState = s.ollama_installed ? "done" : "active";
  const step2: StepState = !s.ollama_installed
    ? "pending"
    : !s.ollama_running
    ? "active"
    : "done";
  const step3: StepState =
    !s.ollama_installed || !s.ollama_running
      ? "pending"
      : s.model_ready
      ? "done"
      : "active";

  // Compute download progress
  const pct =
    progress?.total && progress.completed
      ? (progress.completed / progress.total) * 100
      : 0;

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-ocean-900 rounded-2xl mb-4">
            <span className="text-white text-2xl">⚓</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Vessel Ops AI</h1>
          <p className="text-slate-500 mt-1">
            Let&apos;s get the AI ready before you cast off.
          </p>
        </div>

        <div className="space-y-3">
          {/* Step 1 — Install Ollama */}
          <Step
            n={1}
            title="Install Ollama"
            subtitle="Runs the AI model locally — no internet needed at sea."
            state={step1}
          >
            {step1 === "active" && (
              <div className="space-y-3">
                <p className="text-sm text-slate-600">
                  Ollama is a lightweight app that runs Gemma 4 on your laptop.
                  Download and install it, then come back — this page will
                  update automatically.
                </p>
                <a
                  href={s.install_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 bg-ocean-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-ocean-800 transition-colors"
                >
                  <ExternalLink size={15} />
                  Download Ollama
                </a>
              </div>
            )}
          </Step>

          {/* Step 2 — Start Ollama */}
          <Step
            n={2}
            title="Start Ollama"
            subtitle="Open the Ollama app or run it from your terminal."
            state={step2}
          >
            {step2 === "active" && (
              <p className="text-sm text-slate-600">
                Ollama is installed but not running. Open the Ollama app from
                your Applications folder, or run{" "}
                <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">
                  ollama serve
                </code>{" "}
                in a terminal. This page will update automatically.
              </p>
            )}
          </Step>

          {/* Step 3 — Download model */}
          <Step
            n={3}
            title={`Download ${s.model_name}`}
            subtitle="One-time download (~8 GB). Only needs internet this once."
            state={pullError ? "error" : step3}
          >
            {step3 === "active" && !pulling && !pullError && (
              <div className="space-y-3">
                <p className="text-sm text-slate-600">
                  This downloads Gemma 4 to your machine. After this, everything
                  runs completely offline — no internet required.
                </p>
                <button
                  onClick={startPull}
                  className="inline-flex items-center gap-2 bg-ocean-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-ocean-800 transition-colors"
                >
                  <Download size={15} />
                  Download {s.model_name}
                </button>
              </div>
            )}

            {pulling && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-slate-600">
                    {progress?.status === "pulling manifest"
                      ? "Fetching manifest…"
                      : progress?.status?.startsWith("pulling")
                      ? "Downloading…"
                      : progress?.status?.startsWith("verifying")
                      ? "Verifying…"
                      : progress?.status ?? "Starting…"}
                  </span>
                  {pct > 0 && (
                    <span className="text-slate-500 text-xs">
                      {pct.toFixed(1)}%
                      {progress?.total
                        ? ` · ${formatBytes(progress.completed ?? 0)} / ${formatBytes(progress.total)}`
                        : ""}
                    </span>
                  )}
                </div>
                <ProgressBar pct={pct} />
                <p className="text-xs text-slate-400">
                  Keep this window open. Do not close the laptop.
                </p>
              </div>
            )}

            {pullError && (
              <div className="space-y-3">
                <p className="text-sm text-red-600">
                  Download failed. Check your internet connection and try again.
                </p>
                <button
                  onClick={startPull}
                  className="inline-flex items-center gap-2 border border-red-300 text-red-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
                >
                  Retry download
                </button>
              </div>
            )}
          </Step>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6">
          This setup only happens once. After this, Vessel Ops AI works
          completely offline.
        </p>
      </div>
    </div>
  );
}
