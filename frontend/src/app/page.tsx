"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Vessel, CrewMember, Component, HealthEvent, MaintenanceLog } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { Users, HeartPulse, AlertTriangle, Sparkles, Package, ArrowRight } from "lucide-react";

function Stat({ label, value, href }: { label: string; value: number | string; href: string }) {
  return (
    <Link
      href={href}
      className="flex-1 min-w-[7rem] bg-white rounded-xl border border-slate-200 px-4 py-3 hover:border-ocean-300 hover:shadow-sm transition-all"
    >
      <p className="text-2xl font-bold text-slate-900 leading-none">{value}</p>
      <p className="text-xs text-slate-500 mt-1.5">{label}</p>
    </Link>
  );
}

function PillarCard({
  href,
  title,
  blurb,
  icon: Icon,
  accent,
  stats,
}: {
  href: string;
  title: string;
  blurb: string;
  icon: React.ElementType;
  accent: string;
  stats: { label: string; value: number | string; href: string }[];
}) {
  return (
    <section className="bg-white rounded-2xl border border-slate-200 p-6">
      <Link href={href} className="group flex items-start gap-4">
        <div className={`p-3 rounded-xl shrink-0 ${accent}`}>
          <Icon size={22} />
        </div>
        <div className="min-w-0">
          <h2 className="font-bold text-slate-900 flex items-center gap-1.5">
            {title}
            <ArrowRight size={15} className="text-slate-300 group-hover:translate-x-0.5 group-hover:text-slate-500 transition-all" />
          </h2>
          <p className="text-sm text-slate-500 mt-1 leading-relaxed">{blurb}</p>
        </div>
      </Link>
      <div className="flex gap-3 mt-5">
        {stats.map((s) => (
          <Stat key={s.label} {...s} />
        ))}
      </div>
    </section>
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
  const spareCount = components.data?.reduce((n, c) => n + (c.spare_parts?.length ?? 0), 0) ?? 0;

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">{vessel.data?.name ?? "Vessel Ops AI"}</h1>
        <p className="text-slate-500 mt-1">
          {vessel.data?.imo_number ? `IMO ${vessel.data.imo_number}` : "Medical guidance and vessel inventory, offline."}
        </p>
      </div>

      {crew.data?.some((c) => c.crew_id.startsWith("crew-00")) && (
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

      {/* AI first — this is the app. */}
      <Link
        href="/chat"
        className="block p-6 md:p-8 bg-gradient-to-br from-ocean-600 to-ocean-800 rounded-2xl text-white hover:shadow-xl transition-all hover:-translate-y-0.5 relative overflow-hidden"
      >
        <div className="absolute -top-6 -right-6 opacity-10">
          <Sparkles size={160} />
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1 rounded-full border border-white/20 w-fit mb-4">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-wider">Gemma ready</span>
          </div>
          <h2 className="text-2xl font-bold">Ask Gemma</h2>
          <p className="text-sm text-ocean-50 leading-relaxed max-w-xl mt-2">
            Describe a symptom or ask what&apos;s in the stores. Gemma answers from the WHO medical
            guide and your vessel&apos;s own component and spares inventory &mdash; with no internet
            connection required.
          </p>
          <p className="text-xs font-bold uppercase tracking-widest mt-5 flex items-center gap-1.5">
            Start a conversation <ArrowRight size={13} />
          </p>
        </div>
      </Link>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          {[...Array(2)].map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          <PillarCard
            href="/health"
            title="Medical"
            blurb="Crew records, allergies, and the running health log Gemma reads for patient context."
            icon={HeartPulse}
            accent="bg-green-50 text-green-600"
            stats={[
              { label: "Crew", value: crew.data?.length ?? 0, href: "/crew" },
              { label: "Health events", value: healthEvents.data?.length ?? 0, href: "/health" },
            ]}
          />
          <PillarCard
            href="/vessel"
            title="Inventory"
            blurb="Every component and spare aboard. Gemma reads this before recommending a repair."
            icon={Package}
            accent="bg-ocean-50 text-ocean-600"
            stats={[
              { label: "Components", value: components.data?.length ?? 0, href: "/vessel" },
              { label: "Spares held", value: spareCount, href: "/vessel" },
              { label: "Open issues", value: openIssues, href: "/maintenance" },
            ]}
          />
        </div>
      )}

      {crew.data?.length === 0 && (
        <Link
          href="/crew/new"
          className="mt-4 flex items-center gap-3 p-4 bg-white border border-dashed border-slate-300 rounded-xl text-sm text-slate-600 hover:border-ocean-400 hover:text-ocean-700 transition-colors"
        >
          <Users size={18} className="text-slate-400" />
          Add your crew so Gemma can ground medical answers in their allergies and history.
        </Link>
      )}
    </div>
  );
}
