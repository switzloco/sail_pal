"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { MaintenanceLog } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import Link from "next/link";
import { Plus } from "lucide-react";

export default function MaintenancePage() {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["maintenance"],
    queryFn: () => apiFetch<MaintenanceLog[]>("/maintenance/logs"),
  });

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Maintenance Log</h1>
        <Link
          href="/maintenance/new"
          className="flex items-center gap-2 bg-ocean-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-ocean-800 transition-colors"
        >
          <Plus size={16} /> Log Issue
        </Link>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {logs && logs.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <p className="text-lg">No maintenance issues logged yet.</p>
        </div>
      )}

      {logs && logs.length > 0 && (
        <div className="space-y-3">
          {logs.map((log) => (
            <div key={log.log_id} className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="font-semibold text-slate-900">
                    {log.issue_description || "Maintenance issue"}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    {new Date(log.event_time).toLocaleString()}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <SeverityBadge severity={log.severity} type="maintenance" />
                  {log.resolved && (
                    <span className="text-xs text-green-600 font-medium">Resolved</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
