"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { HealthEvent } from "@/lib/types";
import { CardSkeleton } from \"@/components/ui/Skeleton\";
import { SeverityBadge } from \"@/components/ui/SeverityBadge\";
import Link from \"next/link\";
import { Plus, Activity } from \"lucide-react\";
import VitalsTrendChart from \"@/components/VitalsTrendChart\";
import { useState } from \"react\";
import type { CrewMember } from \"@/lib/types\";

export default function HealthPage() {
  const [selectedCrewId, setSelectedCrewId] = useState<string | null>(null);

  const { data: crew } = useQuery({
    queryKey: [\"crew\"],
    queryFn: () => apiFetch<CrewMember[]>(\"/crew/\"),
  });

  const { data: events, isLoading } = useQuery({
    queryKey: [\"health\"],
    queryFn: () => apiFetch<HealthEvent[]>(\"/health/events\"),
  });

  const activeCrewId = selectedCrewId || crew?.[0]?.crew_id;

  const { data: trends } = useQuery({
    queryKey: [\"vitals-trend\", activeCrewId],
    queryFn: () => activeCrewId ? apiFetch<any[]>(`/health/crew/${activeCrewId}/vitals-trend`) : Promise.resolve([]),
    enabled: !!activeCrewId,
  });

  return (
    <div className="max-w-3xl">
      <div className=\"flex items-center justify-between mb-8\">
        <div>
          <h1 className=\"text-3xl font-black text-slate-900 tracking-tight\">Health Center</h1>
          <p className=\"text-slate-500 text-sm\">Vessel medical logs and vital trends</p>
        </div>
        <Link
          href=\"/health/new\"
          className=\"flex items-center gap-2 bg-ocean-700 text-white px-4 py-2 rounded-xl text-sm font-bold hover:bg-ocean-800 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-ocean-200\"
        >
          <Plus size={16} strokeWidth={3} /> Log Event
        </Link>
      </div>

      {/* Vitals Trends Section */}
      <section className=\"mb-10\">
        <div className=\"flex items-center justify-between mb-4\">
          <h2 className=\"text-xs font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2\">
            <Activity size={14} /> Vital Sign Trends
          </h2>
          {crew && crew.length > 1 && (
            <select 
              className=\"bg-transparent text-[10px] font-bold text-ocean-600 outline-none\"
              value={selectedCrewId || \"\"}
              onChange={(e) => setSelectedCrewId(e.target.value)}
            >
              {crew.map(c => (
                <option key={c.crew_id} value={c.crew_id}>{c.full_name}</option>
              ))}
            </select>
          )}
        </div>
        <VitalsTrendChart data={trends || []} />
      </section>

      <h2 className=\"text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4\">Recent Incidents</h2>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {events && events.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <p className="text-lg">No health events recorded yet.</p>
          <p className="text-sm mt-1">Use the button above to log the first event.</p>
        </div>
      )}

      {events && events.length > 0 && (
        <div className="space-y-3">
          {events.map((evt) => (
            <div
              key={evt.event_id}
              className="bg-white rounded-xl border border-slate-200 p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="font-semibold text-slate-900">
                    {evt.symptoms?.join(", ") || evt.diagnosis || "Health event"}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    {new Date(evt.event_time).toLocaleString()}
                  </p>
                  {evt.diagnosis && (
                    <p className="text-sm text-slate-600 mt-2">{evt.diagnosis}</p>
                  )}
                </div>
                <SeverityBadge severity={evt.severity} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
