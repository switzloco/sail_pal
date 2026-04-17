"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CrewMember, Component } from "@/lib/types";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

const SEVERITIES = ["advisory", "degraded", "critical", "down"] as const;
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function NewMaintenanceLogPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const { data: crew } = useQuery({ queryKey: ["crew"], queryFn: () => apiFetch<CrewMember[]>("/crew") });
  const { data: components } = useQuery({ queryKey: ["components"], queryFn: () => apiFetch<Component[]>("/components") });

  const [form, setForm] = useState({
    component_id: "",
    logged_by: "",
    severity: "advisory" as typeof SEVERITIES[number],
    issue_description: "",
    follow_up: "",
  });
  const [photo, setPhoto] = useState<File | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const fd = new FormData();
      fd.append("vessel_id", "vessel-mv-resolute-001");
      fd.append("component_id", form.component_id);
      fd.append("logged_by", form.logged_by);
      fd.append("severity", form.severity);
      fd.append("issue_description", form.issue_description);
      if (form.follow_up) fd.append("follow_up", form.follow_up);
      if (photo) fd.append("photos", photo);

      const res = await fetch(`${API_BASE}/maintenance/logs`, { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Request failed");
      router.push("/maintenance");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  function field(label: string, children: React.ReactNode) {
    return (
      <label className="block">
        <span className="text-sm font-medium text-slate-700 mb-1 block">{label}</span>
        {children}
      </label>
    );
  }

  const inputClass = "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ocean-600";

  return (
    <div className="max-w-2xl">
      <Link href="/maintenance" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-6">
        <ArrowLeft size={14} /> Back to maintenance log
      </Link>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Log Maintenance Issue</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
        {field("Component", (
          <select className={inputClass} required value={form.component_id} onChange={(e) => setForm({ ...form, component_id: e.target.value })}>
            <option value="">Select component</option>
            {components?.map((c) => (
              <option key={c.component_id} value={c.component_id}>{c.name} — {c.system}</option>
            ))}
          </select>
        ))}

        {field("Logged by", (
          <select className={inputClass} required value={form.logged_by} onChange={(e) => setForm({ ...form, logged_by: e.target.value })}>
            <option value="">Select crew member</option>
            {crew?.map((m) => (
              <option key={m.crew_id} value={m.crew_id}>{m.full_name} — {m.role}</option>
            ))}
          </select>
        ))}

        {field("Severity", (
          <select className={inputClass} value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value as typeof SEVERITIES[number] })}>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        ))}

        {field("Issue description", (
          <textarea className={inputClass} rows={3} required value={form.issue_description} onChange={(e) => setForm({ ...form, issue_description: e.target.value })} />
        ))}

        {field("Follow-up required", (
          <input className={inputClass} value={form.follow_up} onChange={(e) => setForm({ ...form, follow_up: e.target.value })} placeholder="Optional notes on next steps" />
        ))}

        {field("Photo (optional)", (
          <input
            type="file"
            accept="image/*"
            className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-ocean-50 file:text-ocean-700 file:font-medium hover:file:bg-ocean-100"
            onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
          />
        ))}

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-ocean-700 text-white py-2.5 rounded-lg font-medium hover:bg-ocean-800 transition-colors disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Save Issue"}
        </button>
      </form>
    </div>
  );
}
