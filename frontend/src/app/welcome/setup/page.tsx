"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  fetchSetupStatus,
  setMode,
  streamModelPull,
  type PullProgress,
  type SetupStatus
} from "@/lib/setup";
import { apiFetch } from "@/lib/api";
import {
  CheckCircle2,
  Loader2,
  ArrowRight,
  ExternalLink,
  Trash2,
  AlertCircle
} from "lucide-react";
import type { Vessel, CrewMember } from "@/lib/types";

export default function SetupChecklistPage() {
  const router = useRouter();
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [vessel, setVessel] = useState<Vessel | null>(null);
  const [crewCount, setCrewCount] = useState(0);
  const [pulling, setPulling] = useState(false);
  const [progress, setProgress] = useState<PullProgress | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [finishError, setFinishError] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);
  const cancelRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [s, v, c] = await Promise.all([
          fetchSetupStatus(),
          apiFetch<Vessel>("/setup/vessel-info"),
          apiFetch<CrewMember[]>("/crew")
        ]);
        setStatus(s);
        setVessel(v);
        setCrewCount(c.length);
      } catch (err) {
        console.error("Failed to fetch setup data", err);
      }
    };
    fetchData();
    const id = setInterval(fetchData, 5000);
    return () => clearInterval(id);
  }, []);

  const handleStartPull = () => {
    setPulling(true);
    setProgress(null);
    cancelRef.current = streamModelPull(
      (p) => setProgress(p),
      (success) => {
        setPulling(false);
        if (success) {
          fetchSetupStatus().then(setStatus);
        } else {
          alert("Download failed or was interrupted. Re-click 'Start Download' — Ollama will resume from where it left off.");
        }
      }
    );
  };

  const handleReset = async () => {
    if (!confirm("This will clear all demo crew and logs. Are you sure?")) return;
    setIsResetting(true);
    try {
      await apiFetch("/setup/reset-demo-data", { method: "POST" });
      setCrewCount(0);
      alert("Demo data cleared!");
    } catch (err) {
      alert("Failed to reset data.");
    } finally {
      setIsResetting(false);
    }
  };

  const handleFinish = async () => {
    setFinishError(null);
    setFinishing(true);
    localStorage.setItem("vessel_ops_onboarded", "true");
    if (status?.model_ready) {
      try {
        await setMode("local");
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Could not switch to local mode.";
        setFinishError(`${msg} You can continue in cloud mode or fix the issue and try again.`);
        setFinishing(false);
        return;
      }
    }
    router.push("/");
  };

  if (!status) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <Loader2 className="animate-spin text-ocean-600" size={32} />
    </div>
  );

  const steps = [
    {
      id: "ollama",
      title: "Install Ollama",
      desc: "Local AI engine for offline privacy.",
      status: status.ollama_installed ? "done" : "active",
      required: true,
      action: status.ollama_installed ? null : (
        <a
          href={status.install_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-ocean-600 font-semibold text-sm hover:underline"
        >
          Download Ollama <ExternalLink size={14} />
        </a>
      )
    },
    {
      id: "model",
      title: "Download Gemma 4 AI Model",
      desc: "The brains of the system (~8 GB). One-time download.",
      status: status.model_ready ? "done" : (status.ollama_running ? "active" : "pending"),
      required: true,
      action: status.model_ready ? null : (
        pulling ? (
          <div className="w-full mt-2">
            <div className="flex justify-between text-[10px] text-slate-400 mb-1">
              <span>{progress?.status ?? "Starting..."}</span>
              {progress?.total && progress?.completed !== undefined && <span>{((progress.completed / progress.total) * 100).toFixed(0)}%</span>}
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-ocean-600 h-full transition-all duration-300"
                style={{ width: `${(progress?.total && progress?.completed !== undefined) ? (progress.completed / progress.total) * 100 : 0}%` }}
              />
            </div>
            <p className="text-[10px] text-slate-400 mt-1">If interrupted, re-click "Start Download" to resume.</p>
          </div>
        ) : (
          <button
            onClick={handleStartPull}
            disabled={!status.ollama_running}
            className="text-ocean-600 font-semibold text-sm hover:underline disabled:text-slate-300"
          >
            {status.ollama_running ? "Start Download" : "Start Ollama first →"}
          </button>
        )
      )
    },
    {
      id: "crew",
      title: "Add Your Crew",
      desc: `Total members: ${crewCount}`,
      status: crewCount > 0 ? "done" : "active",
      required: false,
      action: (
        <div className="flex gap-4 items-center">
          <button
            onClick={() => router.push("/crew/new")}
            className="text-ocean-600 font-semibold text-sm hover:underline"
          >
            Add Member
          </button>
          {crewCount > 0 && (
            <button
              onClick={handleReset}
              disabled={isResetting}
              className="text-red-500 font-medium text-xs hover:underline flex items-center gap-1"
            >
              <Trash2 size={12} /> Clear Demo
            </button>
          )}
        </div>
      )
    },
    {
      id: "vessel",
      title: "Vessel Identity",
      desc: vessel?.name ?? "My Vessel",
      status: vessel && vessel.name !== "My Vessel" ? "done" : "active",
      required: false,
      action: (
        <button
          onClick={() => {
            const name = prompt("Enter vessel name:", vessel?.name);
            if (name) {
              apiFetch("/setup/vessel-info", {
                method: "POST",
                body: JSON.stringify({ name }),
              }).then(v => setVessel(v as Vessel));
            }
          }}
          className="text-ocean-600 font-semibold text-sm hover:underline"
        >
          Rename
        </button>
      )
    }
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 font-sans">
      <div className="max-w-xl w-full">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900">⚓ Offline Setup</h1>
          <p className="text-slate-500 mt-2">Approximately 15 minutes to complete local AI configuration for disconnected maritime operations.</p>
        </div>

        {!status.server_is_local && (
          <div className="mb-6 bg-sky-50 border border-sky-200 rounded-2xl p-5 text-sm text-sky-900">
            <p className="font-bold text-base mb-1">You&apos;re using the web version</p>
            <p className="text-sky-700 mb-3">
              To run offline at sea, install the <strong>desktop companion</strong> on your laptop while you still have internet. It runs Vessel Ops entirely on your device — no cloud needed.
            </p>
            <ol className="list-decimal list-inside space-y-2 text-sky-800">
              <li>
                Install{" "}
                <a href="https://www.python.org/downloads/" target="_blank" rel="noreferrer" className="font-semibold underline">Python 3.11+</a>
                {" "}and{" "}
                <a href="https://nodejs.org/" target="_blank" rel="noreferrer" className="font-semibold underline">Node.js LTS</a>
              </li>
              <li>
                Install{" "}
                <a href="https://ollama.com/download" target="_blank" rel="noreferrer" className="font-semibold underline">Ollama</a>
                {" "}and open it so it&apos;s running in the background
              </li>
              <li>
                <a
                  href="https://github.com/switzloco/sail_pal/archive/refs/heads/main.zip"
                  className="font-semibold underline"
                >
                  Download Vessel Ops AI
                </a>
                {" "}→ unzip it
              </li>
              <li>
                Inside the folder, run{" "}
                <code className="bg-sky-100 px-1.5 py-0.5 rounded text-xs">scripts\install.ps1</code> (Windows) or{" "}
                <code className="bg-sky-100 px-1.5 py-0.5 rounded text-xs">bash scripts/install.sh</code> (Mac/Linux)
              </li>
              <li>
                Then run{" "}
                <code className="bg-sky-100 px-1.5 py-0.5 rounded text-xs">scripts\start.bat</code> (Windows) or{" "}
                <code className="bg-sky-100 px-1.5 py-0.5 rounded text-xs">bash scripts/start.sh</code> and open{" "}
                <code className="bg-sky-100 px-1.5 py-0.5 rounded text-xs">http://localhost:8000</code>
              </li>
            </ol>
            <p className="mt-3 text-xs text-sky-600">
              The installer saves an offline quickstart guide to your Desktop — keep it for use at sea.{" "}
              <a
                href="https://github.com/switzloco/sail_pal/blob/main/DESKTOP_QUICKSTART.md"
                target="_blank"
                rel="noreferrer"
                className="font-semibold underline"
              >
                Preview it here →
              </a>
            </p>
          </div>
        )}

        <div className="space-y-4 mb-10">
          {steps.map((step, idx) => (
            <div
              key={step.id}
              className={`bg-white border rounded-2xl p-5 flex items-start gap-4 transition-all ${
                step.status === "pending" ? "opacity-40 grayscale" : "shadow-sm border-slate-200"
              }`}
            >
              <div className="mt-1">
                {step.status === "done" ? (
                  <CheckCircle2 className="text-green-500" size={24} />
                ) : (
                  <div className="w-6 h-6 rounded-full border-2 border-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-400">
                    {idx + 1}
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900">{step.title}</h3>
                  {!step.required && (
                    <span className="text-[10px] uppercase tracking-wider font-bold text-slate-400 px-1.5 py-0.5 bg-slate-50 rounded">Optional</span>
                  )}
                </div>
                <p className="text-sm text-slate-500">{step.desc}</p>
                {step.action && <div className="mt-3">{step.action}</div>}
              </div>
            </div>
          ))}
        </div>

        {finishError && (
          <div className="mb-4 flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-800">
            <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-500" />
            <span>{finishError}</span>
          </div>
        )}

        <button
          onClick={handleFinish}
          disabled={finishing}
          className="w-full py-4 bg-ocean-600 hover:bg-ocean-700 disabled:opacity-60 text-white rounded-2xl font-bold shadow-xl shadow-ocean-200 transition-all flex items-center justify-center gap-2"
        >
          {finishing ? <Loader2 className="animate-spin" size={20} /> : <ArrowRight size={20} />}
          {finishing ? "Launching…" : "Launch Vessel Ops AI"}
        </button>

        {finishError && (
          <button
            onClick={() => { setFinishError(null); localStorage.setItem("vessel_ops_onboarded", "true"); router.push("/"); }}
            className="mt-3 w-full py-3 border border-slate-200 text-slate-600 rounded-2xl text-sm font-medium hover:bg-slate-50 transition-all"
          >
            Continue in cloud mode anyway →
          </button>
        )}

        <p className="mt-6 text-center text-xs text-slate-400">
          You can always change these settings later in the app.
        </p>
      </div>
    </div>
  );
}
