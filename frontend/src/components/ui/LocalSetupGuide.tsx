"use client";

import React from "react";
import { 
  Download, 
  Play, 
  Terminal, 
  CheckCircle2, 
  X, 
  ExternalLink,
  ShieldAlert,
  Anchor
} from "lucide-react";

interface LocalSetupGuideProps {
  isOpen: boolean;
  onClose: () => void;
  status: {
    ollama_installed: boolean;
    ollama_running: boolean;
    model_ready: boolean;
    model_name: string;
    install_url: string;
    server_is_local: boolean;
  };
}

export function LocalSetupGuide({ isOpen, onClose, status }: LocalSetupGuideProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-300">
      <div className="bg-white rounded-3xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col md:flex-row animate-in zoom-in-95 duration-300">
        
        {/* Left Side: Visual/Context */}
        <div className="bg-ocean-900 md:w-1/3 p-8 text-white flex flex-col items-center justify-center text-center">
          <div className="bg-ocean-800 p-4 rounded-2xl mb-6 shadow-inner">
            <Anchor size={48} className="text-ocean-200" />
          </div>
          <h2 className="text-xl font-bold mb-2">Offline Power</h2>
          <p className="text-ocean-300 text-sm leading-relaxed">
            Switching to Local mode lets Vessel Ops work even in the middle of the ocean with zero internet.
          </p>
        </div>

        {/* Right Side: Steps */}
        <div className="md:w-2/3 p-8 relative">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 p-2 hover:bg-slate-100 rounded-full text-slate-400 transition-colors"
          >
            <X size={20} />
          </button>

          <h3 className="text-2xl font-bold text-slate-900 mb-6 flex items-center gap-2">
            <ShieldAlert className="text-amber-500" size={24} />
            Local Setup Needed
          </h3>

          <div className="space-y-6">
            {/* Step 1 */}
            <div className={`flex gap-4 p-4 rounded-2xl border-2 transition-all ${status.ollama_installed ? "bg-emerald-50 border-emerald-100" : "bg-slate-50 border-slate-100"}`}>
              <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold ${status.ollama_installed ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-500"}`}>
                {status.ollama_installed ? <CheckCircle2 size={24} /> : "1"}
              </div>
              <div className="flex-1">
                <h4 className="font-bold text-slate-900">Install Ollama</h4>
                <p className="text-sm text-slate-500 mb-3">This is the engine that runs the AI on your computer.</p>
                {!status.ollama_installed && (
                  <a 
                    href={status.install_url} 
                    target="_blank" 
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-ocean-600 text-white text-sm font-bold rounded-xl hover:bg-ocean-700 transition-all shadow-lg shadow-ocean-200"
                  >
                    <Download size={16} /> Download for Windows
                  </a>
                )}
                {status.ollama_installed && <span className="text-emerald-600 text-xs font-bold uppercase tracking-wider">Installed & Ready</span>}
              </div>
            </div>

            {/* Step 2 */}
            <div className={`flex gap-4 p-4 rounded-2xl border-2 transition-all ${status.ollama_running ? "bg-emerald-50 border-emerald-100" : (status.ollama_installed ? "bg-amber-50 border-amber-100" : "bg-slate-50 border-slate-50 opacity-50")}`}>
              <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold ${status.ollama_running ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-500"}`}>
                {status.ollama_running ? <CheckCircle2 size={24} /> : "2"}
              </div>
              <div className="flex-1">
                <h4 className="font-bold text-slate-900">Start Ollama</h4>
                <p className="text-sm text-slate-500 mb-2">Open the Ollama app from your Start menu.</p>
                {status.ollama_installed && !status.ollama_running && (
                  <div className="flex items-center gap-2 text-amber-700 font-bold text-xs bg-amber-100 px-3 py-1.5 rounded-lg w-fit">
                    <Play size={12} fill="currentColor" /> Application not running yet
                  </div>
                )}
                {status.ollama_running && <span className="text-emerald-600 text-xs font-bold uppercase tracking-wider">Running in background</span>}
              </div>
            </div>

            {/* Step 3 */}
            <div className={`flex gap-4 p-4 rounded-2xl border-2 transition-all ${status.model_ready ? "bg-emerald-50 border-emerald-100" : (status.ollama_running ? "bg-sky-50 border-sky-100" : "bg-slate-50 border-slate-50 opacity-50")}`}>
              <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold ${status.model_ready ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-500"}`}>
                {status.model_ready ? <CheckCircle2 size={24} /> : "3"}
              </div>
              <div className="flex-1">
                <h4 className="font-bold text-slate-900">Download the {status.model_name} Model</h4>
                <p className="text-sm text-slate-500 mb-3">Vessel Ops needs this model file to run locally.</p>
                {!status.model_ready && status.ollama_running && (
                  <button 
                    onClick={() => window.location.href = "/welcome/setup"}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-sky-600 text-white text-sm font-bold rounded-xl hover:bg-sky-700 transition-all"
                  >
                    <Terminal size={16} /> Go to Download Page
                  </button>
                )}
                {status.model_ready && <span className="text-emerald-600 text-xs font-bold uppercase tracking-wider">Model Loaded</span>}
              </div>
            </div>
          </div>

          {!status.server_is_local ? (
            <div className="mt-6 text-[12px] text-sky-900 bg-sky-50 border border-sky-100 rounded-xl px-4 py-3 leading-relaxed">
              <p className="font-bold mb-2">Want to use this offline at sea?</p>
              <p className="mb-2">
                The web version can&apos;t reach Ollama on your device. Install the
                <strong> Vessel Ops AI desktop app</strong> (one-time, while you have internet):
              </p>
              <ol className="list-decimal list-inside space-y-1 mb-2">
                <li>
                  Download{" "}
                  <a
                    href="https://github.com/switzloco/sail_pal/releases/latest"
                    target="_blank"
                    rel="noreferrer"
                    className="underline font-semibold hover:text-sky-700"
                  >
                    the latest Windows installer
                  </a>{" "}
                  (<code className="bg-sky-100 px-1 rounded">.exe</code>, ~40 MB)
                </li>
                <li>
                  Double-click the <code className="bg-sky-100 px-1 rounded">.exe</code>. On the SmartScreen warning,
                  click <strong>More info → Run anyway</strong>. No admin password needed.
                </li>
                <li>
                  Open <strong>Vessel Ops AI</strong> from your Start Menu. The app will guide you through
                  installing <a href="https://ollama.com/download" target="_blank" rel="noreferrer" className="underline font-semibold hover:text-sky-700">Ollama</a>{" "}
                  and pulling the Gemma 4 model (~8 GB) from inside the app.
                </li>
              </ol>
              <p className="text-[11px] text-sky-700">
                Total setup: ~1 hour, mostly the model download. Speed depends on your internet.
              </p>
            </div>
          ) : (
            <p className="mt-6 text-center text-[11px] text-amber-600 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2">
              Ollama runs on desktop/laptop computers only — not available on phones or tablets.
            </p>
          )}
          <p className="mt-3 text-center text-[11px] text-slate-400">
            Need more help? Check the <a href="https://ollama.com" target="_blank" rel="noreferrer" className="underline hover:text-ocean-600">Ollama Documentation</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
