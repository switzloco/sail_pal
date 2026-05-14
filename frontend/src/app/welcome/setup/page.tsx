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
  AlertCircle,
  Download,
  Globe
} from "lucide-react";
import type { Vessel, CrewMember } from "@/lib/types";

// ── Web-version guide (server_is_local=false) ─────────────────────────────────
function WebUserGuide() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 font-sans">
      <div className="max-w-2xl w-full">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 bg-sky-100 text-sky-700 px-4 py-1.5 rounded-full text-sm font-semibold mb-4">
            <Globe size={14} /> Web Version
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Set Up Offline Mode</h1>
          <p className="text-slate-500 mt-2 max-w-lg mx-auto">
            The web app can&apos;t reach Ollama on your device — that&apos;s a browser security limit.
            To run offline at sea, install the <strong>desktop companion</strong> on your laptop.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-4 mb-8">

          {/* Step 1 */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex gap-4 shadow-sm">
            <div className="w-8 h-8 rounded-full bg-ocean-600 text-white flex items-center justify-center font-bold text-sm shrink-0 mt-0.5">1</div>
            <div className="flex-1">
              <h3 className="font-bold text-slate-900 mb-1">Install Python 3.11+ and Node.js LTS</h3>
              <div className="flex flex-wrap gap-3">
                <a href="https://www.python.org/downloads/" target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-ocean-600 text-sm font-semibold hover:underline">
                  <Download size={14} /> Python (python.org)
                </a>
                <a href="https://nodejs.org/" target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-ocean-600 text-sm font-semibold hover:underline">
                  <Download size={14} /> Node.js (nodejs.org)
                </a>
              </div>
              <p className="text-xs text-slate-400 mt-1">Windows: check &ldquo;Add Python to PATH&rdquo; during install.</p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex gap-4 shadow-sm">
            <div className="w-8 h-8 rounded-full bg-ocean-600 text-white flex items-center justify-center font-bold text-sm shrink-0 mt-0.5">2</div>
            <div className="flex-1">
              <h3 className="font-bold text-slate-900 mb-1">Install Ollama</h3>
              <a href="https://ollama.com/download" target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-ocean-600 text-sm font-semibold hover:underline">
                <Download size={14} /> ollama.com/download <ExternalLink size={12} />
              </a>
              <p className="text-xs text-slate-400 mt-1">Open it after installing — wait for the llama icon in your system tray / menu bar.</p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex gap-4 shadow-sm">
            <div className="w-8 h-8 rounded-full bg-ocean-600 text-white flex items-center justify-center font-bold text-sm shrink-0 mt-0.5">3</div>
            <div className="flex-1">
              <h3 className="font-bold text-slate-900 mb-1">Download Vessel Ops AI</h3>
              <a href="https://github.com/switzloco/sail_pal/archive/refs/heads/main.zip"
                className="inline-flex items-center gap-1.5 text-ocean-600 text-sm font-semibold hover:underline">
                <Download size={14} /> Download ZIP from GitHub
              </a>
              <p className="text-xs text-slate-400 mt-1">Unzip the folder anywhere on your laptop.</p>
            </div>
          </div>

          {/* Step 4 */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex gap-4 shadow-sm">
            <div className="w-8 h-8 rounded-full bg-ocean-600 text-white flex items-center justify-center font-bold text-sm shrink-0 mt-0.5">4</div>
            <div className="flex-1">
              <h3 className="font-bold text-slate-900 mb-2">Run the Installer</h3>
              <div className="grid sm:grid-cols-2 gap-3">
                <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                  <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Windows</p>
                  <p className="text-xs text-slate-600 mb-1.5">Open the <code className="bg-white px-1 rounded border">scripts</code> folder and double-click:</p>
                  <code className="text-[11px] bg-white border border-slate-200 rounded px-2 py-1 block text-slate-700 break-all">
                    install.bat
                  </code>
                  <p className="text-[11px] text-slate-400 mt-1.5">SmartScreen warning? Click &ldquo;More info&rdquo; → &ldquo;Run anyway&rdquo;. If that fails, open <code className="bg-white px-1 rounded border">cmd</code> in the scripts folder and run <code className="bg-white px-1 rounded border">powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1</code>.</p>
                </div>
                <div className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                  <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Mac / Linux</p>
                  <p className="text-xs text-slate-600 mb-1.5">Open Terminal in the project folder:</p>
                  <code className="text-[11px] bg-white border border-slate-200 rounded px-2 py-1 block text-slate-700">
                    bash scripts/install.sh
                  </code>
                </div>
              </div>
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mt-3">
                ⏱ This downloads the Gemma 4 AI model (~8 GB). Allow up to 1 hour depending on your internet speed.
                If interrupted, just re-run — it resumes from where it left off.
              </p>
            </div>
          </div>

          {/* Step 5 */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex gap-4 shadow-sm">
            <div className="w-8 h-8 rounded-full bg-ocean-600 text-white flex items-center justify-center font-bold text-sm shrink-0 mt-0.5">5</div>
            <div className="flex-1">
              <h3 className="font-bold text-slate-900 mb-1">Launch the App</h3>
              <div className="flex gap-4 text-sm">
                <span><strong>Windows:</strong> double-click <code className="bg-slate-100 px-1 rounded text-xs">scripts\start.bat</code></span>
                <span><strong>Mac/Linux:</strong> <code className="bg-slate-100 px-1 rounded text-xs">bash scripts/start.sh</code></span>
              </div>
              <p className="text-xs text-slate-400 mt-1">Then open <strong>http://localhost:8000</strong> in your browser. The AI runs 100% on your device.</p>
            </div>
          </div>

        </div>

        {/* Offline quickstart note */}
        <div className="bg-green-50 border border-green-200 rounded-2xl p-4 mb-8 text-sm text-green-900">
          <p className="font-bold mb-1">Save the offline quickstart</p>
          <p className="text-green-700 text-xs">
            The installer copies <strong>Vessel-Ops-Quickstart.md</strong> to your Desktop. Print it or screenshot it before you leave port — you&apos;ll need it if you lose internet at sea.{" "}
            <a href="https://github.com/switzloco/sail_pal/blob/main/DESKTOP_QUICKSTART.md"
              target="_blank" rel="noreferrer"
              className="underline font-semibold">Preview it here →</a>
          </p>
        </div>

        {/* Continue in cloud */}
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-3">Not ready to install yet? Use the cloud version in the meantime:</p>
          <button
            onClick={() => { localStorage.setItem("vessel_ops_onboarded", "true"); router.push("/"); }}
            className="inline-flex items-center gap-2 px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-2xl font-semibold text-sm transition-all"
          >
            Continue with Cloud Mode <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Local server checklist (server_is_local=true) ──────────────────────────────
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
          alert("Download failed or was interrupted. Re-click ‘Start Download’ — Ollama will resume from where it left off.");
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

  // Web users get a completely different, focused guide
  if (!status.server_is_local) return <WebUserGuide />;

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
            <p className="text-[10px] text-slate-400 mt-1">If interrupted, re-click &ldquo;Start Download&rdquo; to resume.</p>
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
          <p className="text-slate-500 mt-2">Approximately 1 hour to complete local AI configuration, depending on internet speed (most of that is downloading the 8 GB Gemma 4 model).</p>
        </div>

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
