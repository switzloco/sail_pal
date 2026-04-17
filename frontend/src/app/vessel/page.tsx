"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Component } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { Wrench } from "lucide-react";

const SYSTEM_LABELS: Record<string, string> = {
  propulsion: "Propulsion",
  electrical: "Electrical",
  navigation: "Navigation",
  hvac: "HVAC",
  safety: "Safety",
  hull: "Hull",
};

export default function VesselPage() {
  const { data: components, isLoading } = useQuery({
    queryKey: ["components"],
    queryFn: () => apiFetch<Component[]>("/components"),
  });

  const grouped = components?.reduce((acc, c) => {
    (acc[c.system] = acc[c.system] || []).push(c);
    return acc;
  }, {} as Record<string, Component[]>);

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Component Inventory</h1>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {grouped && Object.entries(grouped).map(([system, items]) => (
        <div key={system} className="mb-6">
          <h2 className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-2">
            {SYSTEM_LABELS[system] ?? system}
          </h2>
          <div className="space-y-2">
            {items.map((c) => (
              <Link
                key={c.component_id}
                href={`/vessel/${c.component_id}`}
                className="flex items-center gap-4 bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow"
              >
                <Wrench size={18} className="text-slate-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 truncate">{c.name}</p>
                  <p className="text-sm text-slate-500 truncate">{c.manufacturer} · {c.location}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
