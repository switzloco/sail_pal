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
              <h3 className="font-bold text-slate-900 mb-1">Download the Vessel Ops AI installer</h3>
              <a href="https://github.com/switzloco/sail_pal/releases/latest"
                target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-ocean-600 text-sm font-semibold hover:underline">
                <Download size={14} /> Latest Release on GitHub <ExternalLink size={12} />
              </a>
              <p className="text-xs text-slate-400 mt-1.5">
                Grab <code className="bg-slate-100 px-1 rounded">Vessel-Ops-AI_x64-setup.exe</code> (Windows, ~40 MB).
                No admin password required — installs to your user folder.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 flex gap-4 shadow-sm">
            <div className="w-8 h-8 rounded-full bg-ocean-600 text-white flex items-center justify-center font-bold text-sm shrink-0 mt-0.5">2</div>
            <div className="flex-1">
              <h3 className="font-bold text-slate-900 mb-1">Run the installer, then launch the app</h3>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Double-click the downloaded <code className="bg-slate-100 px-1 rounded">.exe</code>. When Windows shows
                a SmartScreen warning, click <strong>More info → Run anyway</strong> (we&apos;re not yet code-signed).
                After install completes, open <strong>Vessel Ops AI</strong> from your Start Menu.
              </p>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                The app will guide you through installing <a href="https://ollama.com/download" target="_blank" rel="noreferrer" className="text-ocean-600 font-semibold hover:underline">Ollama</a> and downloading
                the Gemma 4 AI model (~8 GB, one-time) from inside the app.
              </p>
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mt-3">
                ⏱ Total setup: ~1 hour, mostly the Gemma 4 model download. Speed depends on your internet.
                If the download is interrupted, just retry — Ollama resumes from where it left off.
              </p>
            </div>
          </div>

        </div>

        {/* Mac / Linux demand signal */}
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 mb-8">
          <p className="text-sm font-bold text-slate-800 mb-1">Not on Windows?</p>
          <p className="text-xs text-slate-500 mb-3 leading-relaxed">
            v1 ships Windows-only. macOS and Linux installers will be added if there&apos;s enough demand —
            click below to open a pre-filled GitHub issue, then 👍 existing requests from other users.
          </p>
          <div className="flex flex-wrap gap-2">
            <a
              href="https://github.com/switzloco/sail_pal/issues/new?title=Add%20macOS%20installer&labels=enhancement%2Cplatform-request&body=I%27d%20use%20Vessel%20Ops%20AI%20on%20macOS.%0A%0A-%20Mac%20model%20(e.g.%2C%20M2%20MacBook%20Pro)%3A%20%0A-%20Use%20case%2Fvessel%20type%3A%20%0A-%20Roughly%20when%20you%27d%20use%20it%3A%20%0A%0A%F0%9F%91%8D%20this%20issue%20to%20upvote%20macOS%20support."
              target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              🍎 Request macOS support
            </a>
            <a
              href="https://github.com/switzloco/sail_pal/issues/new?title=Add%20Linux%20installer&labels=enhancement%2Cplatform-request&body=I%27d%20use%20Vessel%20Ops%20AI%20on%20Linux.%0A%0A-%20Distro%20%2F%20version%3A%20%0A-%20Use%20case%2Fvessel%20type%3A%20%0A-%20Roughly%20when%20you%27d%20use%20it%3A%20%0A%0A%F0%9F%91%8D%20this%20issue%20to%20upvote%20Linux%20support."
              target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors"
            >
              🐧 Request Linux support
            </a>
          </div>
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
