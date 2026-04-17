"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { HealthEvent } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import Link from "next/link";
import { Plus } from "lucide-react";

export default function HealthPage() {
  const { data: events, isLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthEvent[]>("/health/events"),
  });

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Health Log</h1>
        <Link
          href="/health/new"
          className="flex items-center gap-2 bg-ocean-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-ocean-800 transition-colors"
        >
          <Plus size={16} /> Log Event
        </Link>
      </div>

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
