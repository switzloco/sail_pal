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
  CheckCircle2
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
