"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CrewMember, HealthEvent } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
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

export default function CrewDetailPage({ params }: { params: { id: string } }) {
  const { data: member, isLoading } = useQuery({
    queryKey: ["crew", params.id],
    queryFn: () => apiFetch<CrewMember>(`/crew/${params.id}`),
  });

  const { data: history } = useQuery({
    queryKey: ["crew-health", params.id],
    queryFn: () => apiFetch<HealthEvent[]>(`/health/crew/${params.id}/history`),
    enabled: !!member,
  });

  if (isLoading) return <CardSkeleton />;
  if (!member) return <p className="text-red-600">Crew member not found.</p>;

  return (
    <div className="max-w-2xl">
      <Link href="/crew" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-6">
        <ArrowLeft size={14} /> Back to roster
      </Link>

      <h1 className="text-2xl font-bold text-slate-900">{member.full_name}</h1>
      <p className="text-slate-500 mb-6">{member.role}</p>

      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="font-semibold text-slate-700 mb-3">Medical Profile</h2>
        <Row label="Blood type" value={member.blood_type} />
        <Row label="Allergies" value={member.allergies?.join(", ") || "None known"} />
        <Row label="Medical notes" value={member.medical_notes} />
        <Row label="Date of birth" value={member.date_of_birth} />
        {member.emergency_contact && (
          <Row
            label="Emergency contact"
            value={`${member.emergency_contact.name} (${member.emergency_contact.relation}) — ${member.emergency_contact.phone}`}
          />
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-700 mb-3">Health History</h2>
        {!history || history.length === 0 ? (
          <p className="text-sm text-slate-400">No health events recorded.</p>
        ) : (
          <div className="space-y-3">
            {history.map((evt) => (
              <div key={evt.event_id} className="flex items-start justify-between py-2 border-b border-slate-100 last:border-0">
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {evt.symptoms?.join(", ") || evt.diagnosis || "Event logged"}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {new Date(evt.event_time).toLocaleDateString()}
                  </p>
                </div>
                <SeverityBadge severity={evt.severity} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
