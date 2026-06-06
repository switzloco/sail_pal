"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Vessel, CrewMember, Component, HealthEvent, MaintenanceLog } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { Users, Wrench, HeartPulse, AlertTriangle, Sparkles, Stethoscope, GraduationCap } from "lucide-react";

function StatCard({
  label,
  value,
  href,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number | string;
  href: string;
  icon: React.ElementType;
  accent: string;
}) {
  return (
    <Link
      href={href}
      className="bg-white rounded-xl border border-slate-200 p-6 flex items-center gap-5 hover:shadow-md transition-shadow"
    >
      <div className={`p-3 rounded-lg ${accent}`}>
        <Icon size={24} />
      </div>
      <div>
        <p className="text-3xl font-bold text-slate-900">{value}</p>
        <p className="text-sm text-slate-500 mt-0.5">{label}</p>
      </div>
    </Link>
  );
}

export default function Dashboard() {
  const crew = useQuery({ queryKey: ["crew"], queryFn: () => apiFetch<CrewMember[]>("/crew") });
  const vessel = useQuery({ queryKey: ["vessel-info"], queryFn: () => apiFetch<Vessel>("/setup/vessel-info") });
  const components = useQuery({ queryKey: ["components"], queryFn: () => apiFetch<Component[]>("/components") });
  const healthEvents = useQuery({ queryKey: ["health"], queryFn: () => apiFetch<HealthEvent[]>("/health/events") });
  const maintenanceLogs = useQuery({ queryKey: ["maintenance"], queryFn: () => apiFetch<MaintenanceLog[]>("/maintenance/logs") });

  const isLoading = crew.isLoading || components.isLoading || vessel.isLoading;
  const openIssues = maintenanceLogs.data?.filter((l) => !l.resolved).length ?? 0;

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">{vessel.data?.name ?? "Vessel Ops AI"}</h1>
        <p className="text-slate-500 mt-1">{vessel.data?.imo_number ? `IMO ${vessel.data.imo_number}` : "Vessel Ops AI Dashboard"}</p>
      </div>

      {crew.data?.some(c => c.crew_id.startsWith("crew-00")) && (
        <div className="mb-6 p-4 bg-amber-50 border border-amber-100 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-3 text-amber-800">
            <AlertTriangle size={20} />
            <p className="text-sm font-medium">You are viewing demo data (MV Resolute).</p>
          </div>
          <button 
            onClick={async () => {
              if (confirm("Clear all demo crew, logs, and components?")) {
                await apiFetch("/setup/reset-demo-data", { method: "POST" });
                window.location.reload();
              }
            }}
            className="text-amber-700 text-xs font-bold hover:underline"
          >
            Clear Demo Data
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatCard
            label="Active crew"
            value={crew.data?.length ?? 0}
            href="/crew"
            icon={Users}
            accent="bg-blue-50 text-blue-600"
          />
          <StatCard
            label="Components tracked"
            value={components.data?.length ?? 0}
            href="/vessel"
            icon={Wrench}
            accent="bg-slate-100 text-slate-600"
          />
          <StatCard
            label="Health events logged"
            value={healthEvents.data?.length ?? 0}
            href="/health"
            icon={HeartPulse}
            accent="bg-green-50 text-green-600"
          />
          <StatCard
            label="Open maintenance issues"
            value={openIssues}
            href="/maintenance"
            icon={AlertTriangle}
            accent={openIssues > 0 ? "bg-amber-50 text-amber-600" : "bg-slate-50 text-slate-400"}
          />
        </div>
      )}

      <div className="mt-10 grid grid-cols-1 md:grid-cols-4 gap-6">
        <Link
          href="/chat"
          className="md:col-span-2 p-6 bg-gradient-to-br from-ocean-600 to-ocean-800 rounded-2xl text-white hover:shadow-xl transition-all hover:-translate-y-1 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Sparkles size={120} />
          </div>
          
          <div className="relative z-10">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-white/20 p-2 rounded-lg backdrop-blur-md">
                  <Sparkles size={24} />
                </div>
                <h2 className="text-xl font-bold">Ask Gemma</h2>
              </div>
              <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1 rounded-full border border-white/20">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-white">System Ready</span>
              </div>
            </div>
            
            <p className="text-sm text-ocean-50 leading-relaxed max-w-lg">
              Consult your vessel&apos;s medical and technical knowledge base. Powered by 
              <strong> Gemma</strong>.
            </p>
          </div>
        </Link>

        <Link
          href="/study"
          className="p-6 bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-2xl text-white hover:shadow-xl transition-all hover:-translate-y-1 relative overflow-hidden group"
        >
          <div className="absolute top-0 right-0 p-4 opacity-20 group-hover:scale-110 transition-transform">
            <GraduationCap size={80} />
          </div>
          
          <div className="relative z-10 h-full flex flex-col justify-between">
            <div>
              <div className="bg-white/20 p-2 rounded-lg backdrop-blur-md w-fit mb-4">
                <GraduationCap size={24} />
              </div>
              <h2 className="text-xl font-bold">MPIC Study</h2>
              <p className="text-xs text-indigo-50 mt-1">Medical Simulations</p>
            </div>
            <p className="text-xs font-bold uppercase tracking-widest mt-4">Start Training &rarr;</p>
          </div>
        </Link>

        <Link
          href="/triage"
          className="p-6 bg-gradient-to-br from-rose-600 to-rose-800 rounded-2xl text-white hover:shadow-xl transition-all hover:-translate-y-1 relative overflow-hidden group"
        >
          <div className="absolute top-0 right-0 p-4 opacity-20 group-hover:scale-110 transition-transform">
            <Stethoscope size={80} />
          </div>

          <div className="relative z-10 h-full flex flex-col justify-between">
            <div>
              <div className="bg-white/20 p-2 rounded-lg backdrop-blur-md w-fit mb-4">
                <Stethoscope size={24} />
              </div>
              <h2 className="text-xl font-bold">Triage Agent</h2>
              <p className="text-xs text-rose-50 mt-1">Multi-step · Arize-traced</p>
            </div>
            <p className="text-xs font-bold uppercase tracking-widest mt-4">Run Triage &rarr;</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
