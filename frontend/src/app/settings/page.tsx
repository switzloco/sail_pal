"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Vessel } from "@/lib/types";
import {
  Settings as SettingsIcon,
  Ship,
  Trash2,
  Cpu,
  Database,
  FileText,
  Save,
  RotateCcw,
  Cloud,
  HardDrive,
  ExternalLink,
  CheckCircle2,
  ChevronDown,
  FlaskConical
} from "lucide-react";
import { useState } from "react";
import Link from "next/link";
import { useToast } from "@/components/ui/Toast";
import { LocalSetupGuide } from "@/components/ui/LocalSetupGuide";
import { fetchSetupStatus, type SetupStatus } from "@/lib/setup";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { data: vessel, isLoading: vesselLoading } = useQuery({ 
    queryKey: ["vessel-info"], 
    queryFn: () => apiFetch<Vessel>("/setup/vessel-info") 
  });
  const { data: stats } = useQuery({ 
    queryKey: ["knowledge-stats"], 
    queryFn: () => apiFetch<Record<string, number>>("/ai/knowledge-stats") 
  });
  const { data: modeInfo } = useQuery({ 
    queryKey: ["ai-mode"], 
    queryFn: () => apiFetch<{ mode: string }>("/setup/mode") 
  });

  const [vesselName, setVesselName] = useState("");
  const [imo, setImo] = useState("");
  const [showGuide, setShowGuide] = useState(false);
  const [showNerdInfo, setShowNerdInfo] = useState(false);

  const { data: status } = useQuery({ 
    queryKey: ["setup-status"], 
    queryFn: () => fetchSetupStatus() 
  });

  const updateVessel = useMutation({
    mutationFn: (payload: { name: string; imo_number: string }) => 
      apiFetch("/setup/vessel-info", { method: "POST", body: JSON.stringify(payload) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["vessel-info"] })
  });

  const toggleMode = useMutation({
    mutationFn: (mode: string) => 
      apiFetch("/setup/mode", { method: "POST", body: JSON.stringify({ mode }) }),
    onSuccess: () => {
      showToast("AI Intelligence mode updated.", "success");
      queryClient.invalidateQueries({ queryKey: ["ai-mode"] });
    },
    onError: (err) => {
      showToast(err.message, "error");
      setShowGuide(true);
    }
  });

  const clearDemoData = async () => {
    if (!confirm("Delete all demo crew and logs? This cannot be undone.")) return;
    try {
      await apiFetch("/setup/reset-demo-data", { method: "POST" });
      showToast("Demo data cleared.", "success");
      window.location.reload();
    } catch (err) {
      showToast("Failed to clear data.", "error");
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center gap-3 mb-8">
        <div className="bg-ocean-100 text-ocean-700 p-2 rounded-xl">
          <SettingsIcon size={28} />
        </div>
        <h1 className="text-3xl font-bold text-slate-900">System Settings</h1>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Vessel Info Card */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <Ship className="text-ocean-600" size={20} />
            <h2 className="font-bold text-slate-800">Vessel Identity</h2>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Vessel Name</label>
              <input 
                type="text" 
                defaultValue={vessel?.name}
                onChange={(e) => setVesselName(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ocean-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">IMO Number</label>
              <input 
                type="text" 
                defaultValue={vessel?.imo_number}
                onChange={(e) => setImo(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-ocean-500 outline-none"
              />
            </div>
            <button 
              onClick={() => updateVessel.mutate({ name: vesselName || vessel?.name || "", imo_number: imo || vessel?.imo_number || "" })}
              className="w-full py-2 bg-ocean-600 text-white rounded-lg text-sm font-bold flex items-center justify-center gap-2 hover:bg-ocean-700 transition-colors"
            >
              <Save size={16} /> Save Changes
            </button>
          </div>
        </section>

        {/* AI Engine Card */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <Cpu className="text-purple-600" size={20} />
            <h2 className="font-bold text-slate-800">AI Intelligence Mode</h2>
          </div>
          <div className="space-y-4">
            <div className="flex p-1 bg-slate-100 rounded-xl">
              <button 
                onClick={() => toggleMode.mutate("local")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${
                  modeInfo?.mode === "local" ? "bg-white shadow-sm text-ocean-700" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <HardDrive size={16} /> Local (Ollama)
              </button>
              <button 
                onClick={() => toggleMode.mutate("cloud")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${
                  modeInfo?.mode === "cloud" ? "bg-white shadow-sm text-blue-600" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                <Cloud size={16} /> Cloud (Gemma API)
              </button>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed italic">
              Local mode runs Gemma 4 entirely on your hardware for 100% offline operation. 
              Cloud mode uses Google AI Studio for faster responses while connected.
            </p>
            <div className="pt-2 border-t border-slate-50">
              <button 
                onClick={() => setShowGuide(true)}
                className="text-[11px] text-ocean-600 font-bold hover:underline flex items-center gap-1"
              >
                Local AI Setup Guide <ExternalLink size={10} />
              </button>
            </div>
          </div>
        </section>

        {status && (
          <LocalSetupGuide 
            isOpen={showGuide} 
            onClose={() => setShowGuide(false)} 
            status={status} 
          />
        )}

        {/* Under the Hood */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm md:col-span-2">
          <button
            onClick={() => setShowNerdInfo(v => !v)}
            className="w-full flex items-center justify-between p-6 text-left"
          >
            <div className="flex items-center gap-2">
              <FlaskConical className="text-violet-500" size={20} />
              <h2 className="font-bold text-slate-800">Under the Hood</h2>
              <span className="text-[10px] font-bold bg-violet-100 text-violet-600 px-2 py-0.5 rounded-full uppercase tracking-wide">for nerds</span>
            </div>
            <ChevronDown
              size={18}
              className={`text-slate-400 transition-transform duration-200 ${showNerdInfo ? "rotate-180" : ""}`}
            />
          </button>

          {showNerdInfo && (
            <div className="px-6 pb-6 space-y-6 border-t border-slate-100 pt-5">

              {/* FAQ grid */}
              <div className="grid md:grid-cols-2 gap-4">

                <div className="bg-slate-50 rounded-xl p-4 space-y-1">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Why Gemma 4?</p>
                  <p className="text-sm text-slate-700">
                    Gemma 4 2B hits the sweet spot for 8&ndash;16 GB laptops: fast enough to be useful in an
                    emergency (&lt;15s responses), small enough to co-exist with the OS, and capable enough
                    to follow complex clinical protocols. The 4B variant is available for 32 GB+ hardware.
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 space-y-1">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Why a maritime-specific fine-tune?</p>
                  <p className="text-sm text-slate-700">
                    The base Gemma model has never seen the WHO <em>International Medical Guide for Ships</em>
                    in depth. The fine-tune trains it on ~1,400 clinical Q&amp;A pairs drawn directly from the
                    IMGS, so it internalises the drug names, dosage patterns, and protocol structure used by
                    maritime medicine &mdash; reducing hallucination on specific dosages before RAG even kicks in.
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 space-y-1">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Two models — why not one?</p>
                  <p className="text-sm text-slate-700">
                    The WHO fine-tune is laser-focused on medical prose. Asking it about engine diagnostics
                    or SOLAS regulations would degrade its answers. So medical routes
                    (injury triage, drug queries, WHO protocols) use the fine-tune; everything else &mdash;
                    engine fault analysis, maintenance, MPIC study, trivia &mdash; stays on vanilla Gemma 4.
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 space-y-1">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">What is RAG?</p>
                  <p className="text-sm text-slate-700">
                    Retrieval-Augmented Generation. Every medical query retrieves the top 3 most relevant
                    passages from the 938-chunk WHO IMGS index (SQLite FTS5, BM25 ranking) and injects them
                    into the prompt with page citations. The AI must answer from those passages and cite the
                    page &mdash; dramatically cutting hallucination on dosages and protocols.
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 space-y-1">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">What is GGUF / Q4_K_M?</p>
                  <p className="text-sm text-slate-700">
                    GGUF is the file format used by Ollama and llama.cpp for local inference. Q4_K_M means
                    the model weights are quantised to ~4 bits using a K-quant scheme &mdash; roughly 3&times;
                    smaller than the full 16-bit model (~1.3 GB vs ~5 GB) with minimal quality loss.
                    That&apos;s what lets the medical fine-tune fit on the same laptop as the base model.
                  </p>
                </div>

                <div className="bg-slate-50 rounded-xl p-4 space-y-1">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">What is Unsloth?</p>
                  <p className="text-sm text-slate-700">
                    Unsloth is a fine-tuning library that makes training large language models 2&times; faster
                    with ~70% less GPU memory than standard HuggingFace Trainer. That&apos;s what made it
                    possible to fine-tune Gemma 4 on a free Kaggle T4 GPU in ~3 hours &mdash; the same class
                    of hardware found on many modern vessels.
                  </p>
                </div>

              </div>

              {/* Stack summary */}
              <div className="bg-slate-900 rounded-xl p-4 text-xs font-mono space-y-1 text-slate-300">
                <p className="text-slate-500 mb-2"># model routing</p>
                <p><span className="text-violet-400">medical routes</span>  →  <span className="text-green-400">hf.co/nswitzer/gemma4-maritime-medical-GGUF</span>  <span className="text-slate-500">(Unsloth WHO fine-tune, Q4_K_M)</span></p>
                <p><span className="text-violet-400">everything else</span>  →  <span className="text-green-400">gemma4:e2b</span>  <span className="text-slate-500">(vanilla Gemma 4, general purpose)</span></p>
                <p className="text-slate-500 mt-2"># retrieval</p>
                <p><span className="text-blue-400">RAG</span>  →  <span className="text-slate-300">SQLite FTS5 · BM25 · 938 WHO IMGS chunks · top-3 per query</span></p>
                <p className="text-slate-500 mt-2"># inference</p>
                <p><span className="text-yellow-400">runtime</span>  →  <span className="text-slate-300">Ollama · llama.cpp · 100% local · no internet required</span></p>
              </div>

              {/* Links */}
              <div className="flex flex-wrap gap-3 text-xs">
                <a
                  href="https://huggingface.co/nswitzer/gemma4-maritime-medical-GGUF"
                  target="_blank" rel="noreferrer"
                  className="flex items-center gap-1 text-violet-600 font-bold hover:underline"
                >
                  <ExternalLink size={11} /> Fine-tune on HuggingFace
                </a>
                <a
                  href="https://www.kaggle.com/code/nswitzer/vessel-ops-extra-credit"
                  target="_blank" rel="noreferrer"
                  className="flex items-center gap-1 text-violet-600 font-bold hover:underline"
                >
                  <ExternalLink size={11} /> Training notebook (Kaggle)
                </a>
                <a
                  href="https://github.com/switzloco/sail_pal"
                  target="_blank" rel="noreferrer"
                  className="flex items-center gap-1 text-violet-600 font-bold hover:underline"
                >
                  <ExternalLink size={11} /> Source on GitHub
                </a>
              </div>

              {/* Inspiration */}
              <div className="bg-gradient-to-r from-ocean-50 to-violet-50 rounded-xl p-4 text-xs text-slate-700 leading-relaxed">
                <p className="font-bold text-slate-800 mb-1">Built for real voyages.</p>
                <p>
                  Inspired by sailors like Dr. Michael, whose{" "}
                  <a
                    href="https://www.youtube.com/playlist?list=PLAo18mQiH8HZomYH0nXURxcgQ5NnNvRB5"
                    target="_blank" rel="noreferrer"
                    className="text-ocean-600 font-bold hover:underline inline-flex items-center gap-1"
                  >
                    deep-water sailing series <ExternalLink size={10} />
                  </a>{" "}
                  captures exactly the kind of long passages, equipment failures, and quiet
                  self-reliance this app was designed to support.
                </p>
              </div>

            </div>
          )}
        </section>

        {/* Knowledge Base Card */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <Database className="text-green-600" size={20} />
            <h2 className="font-bold text-slate-800">RAG Knowledge Base</h2>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
              <div className="flex items-center gap-3">
                <FileText className="text-slate-400" size={18} />
                <span className="text-sm font-medium text-slate-700">Medical Protocols (WHO)</span>
              </div>
              <span className="text-xs font-bold text-ocean-600 px-2 py-1 bg-ocean-50 rounded-lg">
                {stats?.medical_protocols ?? 0} chunks
              </span>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
              <div className="flex items-center gap-3">
                <FileText className="text-slate-400" size={18} />
                <span className="text-sm font-medium text-slate-700">Technical Manuals</span>
              </div>
              <span className="text-xs font-bold text-ocean-600 px-2 py-1 bg-ocean-50 rounded-lg">
                {stats?.engine_manuals ?? 0} chunks
              </span>
            </div>
            <button 
              onClick={() => (window.location.href = "/vessel")}
              className="w-full py-2 border border-slate-200 text-slate-600 rounded-lg text-sm font-bold hover:bg-slate-50 transition-colors"
            >
              Manage Documents
            </button>
          </div>
        </section>

        {/* Maintenance Card */}
        <section className="bg-white rounded-2xl border border-red-100 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <RotateCcw className="text-red-500" size={20} />
            <h2 className="font-bold text-slate-800">Maintenance & Reset</h2>
          </div>
          <div className="space-y-4">
            <button 
              onClick={() => {
                localStorage.removeItem("vessel_ops_onboarded");
                window.location.href = "/welcome";
              }}
              className="w-full py-2 bg-ocean-900 text-white rounded-lg text-sm font-bold hover:bg-black transition-colors flex items-center justify-center gap-2"
            >
              <CheckCircle2 size={16} /> Run System Health Check & Setup
            </button>
            <button 
              onClick={clearDemoData}
              className="w-full py-2 border border-red-200 text-red-600 rounded-lg text-sm font-bold hover:bg-red-50 transition-colors flex items-center justify-center gap-2"
            >
              <Trash2 size={16} /> Clear All Demo Data
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
