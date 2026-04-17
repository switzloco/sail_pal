"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CrewMember } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { User } from "lucide-react";

export default function CrewPage() {
  const { data: crew, isLoading, error } = useQuery({
    queryKey: ["crew"],
    queryFn: () => apiFetch<CrewMember[]>("/crew"),
  });

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Crew Roster</h1>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {error && (
        <div className="text-red-600 bg-red-50 p-4 rounded-lg">
          Failed to load crew: {(error as Error).message}
        </div>
      )}

      {crew && (
        <div className="space-y-3">
          {crew.map((member) => (
            <Link
              key={member.crew_id}
              href={`/crew/${member.crew_id}`}
              className="block bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start gap-4">
                <div className="bg-ocean-100 text-ocean-700 p-2 rounded-lg">
                  <User size={20} />
                </div>
                <div className="flex-1">
                  <div className="flex items-baseline justify-between">
                    <p className="font-semibold text-slate-900">{member.full_name}</p>
                    <span className="text-xs text-slate-400">{member.blood_type}</span>
                  </div>
                  <p className="text-sm text-slate-500 mt-0.5">{member.role}</p>
                  {member.allergies && member.allergies.length > 0 && (
                    <p className="text-xs text-red-600 mt-1">
                      ⚠ Allergies: {member.allergies.join(", ")}
                    </p>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
