"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch, getUploadUrl } from "@/lib/api";
import type { HealthEvent } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import Link from "next/link";
import { Plus, Activity, Sparkles } from "lucide-react";
import VitalsTrendChart from "@/components/VitalsTrendChart";
import { useState } from "react";
import type { CrewMember } from "@/lib/types";
import { useQueryClient } from "@tanstack/react-query";

export default function HealthPage() {
  const [selectedCrewId, setSelectedCrewId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: crew } = useQuery({
    queryKey: ["crew"],
    queryFn: () => apiFetch<CrewMember[]>("/crew/"),
  });

  const { data: events, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthEvent[]>("/health/events"),
  });

  const activeCrewId = selectedCrewId || crew?.[0]?.crew_id;

  const { data: trends } = useQuery({
    queryKey: ["vitals-trend", activeCrewId],
    queryFn: () => activeCrewId ? apiFetch<any[]>(`/health/crew/${activeCrewId}/vitals-trend`) : Promise.resolve([]),
    enabled: !!activeCrewId,
  });

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Health Center</h1>
          <p className="text-slate-500 text-sm">Vessel medical logs and vital trends</p>
        </div>
        <Link
          href="/health/new"
          className="flex items-center gap-2 bg-ocean-700 text-white px-4 py-2 rounded-xl text-sm font-bold hover:bg-ocean-800 transition-all hover:scale-105 active:scale-95 shadow-lg shadow-ocean-200"
        >
          <Plus size={16} strokeWidth={3} /> Log Event
        </Link>
      </div>

      {/* Vitals Trends Section */}
      <section className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
            <Activity size={16} /> Vital Sign Trends
          </h2>
          {crew && crew.length > 1 && (
            <select 
              className="bg-transparent text-sm font-bold text-ocean-600 outline-none cursor-pointer"
              value={selectedCrewId || ""}
              onChange={(e) => setSelectedCrewId(e.target.value)}
            >
              {crew.map(c => (
                <option key={c.crew_id} value={c.crew_id}>{c.role}: {c.full_name}</option>
              ))}
            </select>
          )}
        </div>
        <VitalsTrendChart data={trends || []} />
      </section>

      {/* Quick Log Chat-style Interface */}
      <section className="mb-10 bg-ocean-50/50 border border-ocean-100 rounded-2xl p-5 shadow-sm shadow-ocean-100/50">
        <h2 className="text-sm font-black text-ocean-900/40 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
          <Sparkles size={16} className="text-ocean-500" /> Quick Log Event
        </h2>
        <form 
          onSubmit={async (e) => {
            e.preventDefault();
            const text = (e.currentTarget.elements.namedItem("quick_log") as HTMLInputElement).value;
            if (!text.trim()) return;
            
            try {
              await apiFetch("/health/events", {
                method: "POST",
                body: JSON.stringify({
                  vessel_id: "vessel-mv-resolute-001",
                  crew_id: activeCrewId || "guest",
                  logged_by: "guest", // Default for quick log
                  severity: "minor",
                  diagnosis: `Quick Log: ${text}`,
                  event_time: new Date().toISOString(),
                }),
              });
              (e.currentTarget.elements.namedItem("quick_log") as HTMLInputElement).value = "";
              // Trigger a refetch of the events
              queryClient.invalidateQueries({ queryKey: ["health"] });
            } catch (err) {
              console.error("Failed to log event", err);
            }
          }}
          className="flex gap-3"
        >
          <input
            name="quick_log"
            placeholder="Type a quick medical note (e.g. Smith has a minor headache)..."
            className="flex-1 bg-white border border-ocean-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-ocean-500 shadow-inner"
            autoComplete="off"
          />
          <button
            type="submit"
            className="bg-ocean-600 hover:bg-ocean-700 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all hover:scale-105 active:scale-95 shadow-md shadow-ocean-200 flex items-center gap-2"
          >
            Log <Plus size={16} strokeWidth={3} />
          </button>
        </form>
        <p className="text-[11px] text-ocean-400 mt-2 ml-1 italic">
          Logging for: <span className="font-bold">{crew?.find(c => c.crew_id === activeCrewId)?.full_name || "Guest"}</span>
        </p>
      </section>

      <h2 className="text-sm font-black text-slate-400 uppercase tracking-[0.2em] mb-4">Recent Incidents</h2>

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
                  {evt.photo_paths && evt.photo_paths.length > 0 && (
                    <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
                      {evt.photo_paths.map((p, i) => (
                        <img 
                          key={i} 
                          src={getUploadUrl(p)} 
                          alt="Medical" 
                          className="w-16 h-16 rounded-lg object-cover border border-slate-100 flex-shrink-0" 
                        />
                      ))}
                    </div>
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
