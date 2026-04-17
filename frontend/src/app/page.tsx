"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CrewMember, Component, HealthEvent, MaintenanceLog } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { Users, Wrench, HeartPulse, AlertTriangle } from "lucide-react";

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
  const components = useQuery({ queryKey: ["components"], queryFn: () => apiFetch<Component[]>("/components") });
  const healthEvents = useQuery({ queryKey: ["health"], queryFn: () => apiFetch<HealthEvent[]>("/health/events") });
  const maintenanceLogs = useQuery({ queryKey: ["maintenance"], queryFn: () => apiFetch<MaintenanceLog[]>("/maintenance/logs") });

  const isLoading = crew.isLoading || components.isLoading;
  const openIssues = maintenanceLogs.data?.filter((l) => !l.resolved).length ?? 0;

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">MV Resolute</h1>
        <p className="text-slate-500 mt-1">IMO 9876543 · Vessel Ops AI Dashboard</p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
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

      <div className="mt-10 p-4 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-700">
        <strong>AI guidance is in demo mode.</strong> Medical and engineering queries return
        illustrative responses. Ollama integration (Gemma 4) activates in Phase 2.
      </div>
    </div>
  );
}
