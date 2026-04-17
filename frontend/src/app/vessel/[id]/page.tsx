"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Component } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

function Row({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex gap-4 py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-500 w-40 shrink-0">{label}</span>
      <span className="text-sm text-slate-900">{value}</span>
    </div>
  );
}

export default function ComponentDetailPage({ params }: { params: { id: string } }) {
  const { data: component, isLoading } = useQuery({
    queryKey: ["component", params.id],
    queryFn: () => apiFetch<Component>(`/components/${params.id}`),
  });

  if (isLoading) return <CardSkeleton />;
  if (!component) return <p className="text-red-600">Component not found.</p>;

  return (
    <div className="max-w-2xl">
      <Link href="/vessel" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-6">
        <ArrowLeft size={14} /> Back to inventory
      </Link>

      <h1 className="text-2xl font-bold text-slate-900">{component.name}</h1>
      <p className="text-slate-500 capitalize mb-6">{component.system} system</p>

      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
        <h2 className="font-semibold text-slate-700 mb-3">Equipment Details</h2>
        <Row label="Manufacturer" value={component.manufacturer} />
        <Row label="Model" value={component.model_number} />
        <Row label="Serial number" value={component.serial_number} />
        <Row label="Location" value={component.location} />
        <Row label="Install date" value={component.install_date} />
        <Row label="Manual reference" value={component.manual_ref} />
      </div>

      {component.spare_parts && component.spare_parts.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
          <h2 className="font-semibold text-slate-700 mb-3">Spare Parts Onboard</h2>
          <ul className="space-y-1">
            {component.spare_parts.map((part, i) => (
              <li key={i} className="text-sm text-slate-700 flex gap-2">
                <span className="text-slate-300">—</span> {part}
              </li>
            ))}
          </ul>
        </div>
      )}

      {component.notes && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-700 mb-2">Notes</h2>
          <p className="text-sm text-slate-600">{component.notes}</p>
        </div>
      )}
    </div>
  );
}
