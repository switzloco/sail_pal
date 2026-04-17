"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CrewMember } from "@/lib/types";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

const SEVERITIES = ["minor", "moderate", "serious", "critical"] as const;

export default function NewHealthEventPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const { data: crew } = useQuery({
    queryKey: ["crew"],
    queryFn: () => apiFetch<CrewMember[]>("/crew"),
  });

  const [form, setForm] = useState({
    crew_id: "",
    logged_by: "",
    severity: "minor" as typeof SEVERITIES[number],
    symptoms: "",
    diagnosis: "",
    treatment: "",
    hr: "",
    bp: "",
    temp: "",
    spo2: "",
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await apiFetch("/health/events", {
        method: "POST",
        body: JSON.stringify({
          vessel_id: "vessel-mv-resolute-001",
          crew_id: form.crew_id,
          logged_by: form.logged_by,
          severity: form.severity,
          symptoms: form.symptoms.split(",").map((s) => s.trim()).filter(Boolean),
          diagnosis: form.diagnosis || undefined,
          treatment: form.treatment || undefined,
          vital_signs: {
            hr: form.hr ? parseInt(form.hr) : undefined,
            bp: form.bp || undefined,
            temp: form.temp ? parseFloat(form.temp) : undefined,
            spo2: form.spo2 ? parseInt(form.spo2) : undefined,
          },
        }),
      });
      router.push("/health");
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
  const selectClass = inputClass;

  return (
    <div className="max-w-2xl">
      <Link href="/health" className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-6">
        <ArrowLeft size={14} /> Back to health log
      </Link>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Log Health Event</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
        {field("Patient", (
          <select
            className={selectClass}
            required
            value={form.crew_id}
            onChange={(e) => setForm({ ...form, crew_id: e.target.value })}
          >
            <option value="">Select crew member</option>
            {crew?.map((m) => (
              <option key={m.crew_id} value={m.crew_id}>{m.full_name} — {m.role}</option>
            ))}
          </select>
        ))}

        {field("Logged by (MPIC)", (
          <select
            className={selectClass}
            required
            value={form.logged_by}
            onChange={(e) => setForm({ ...form, logged_by: e.target.value })}
          >
            <option value="">Select crew member</option>
            {crew?.map((m) => (
              <option key={m.crew_id} value={m.crew_id}>{m.full_name} — {m.role}</option>
            ))}
          </select>
        ))}

        {field("Severity", (
          <select
            className={selectClass}
            value={form.severity}
            onChange={(e) => setForm({ ...form, severity: e.target.value as typeof SEVERITIES[number] })}
          >
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
        ))}

        {field("Symptoms (comma-separated)", (
          <input
            className={inputClass}
            placeholder="e.g. headache, nausea, dizziness"
            value={form.symptoms}
            onChange={(e) => setForm({ ...form, symptoms: e.target.value })}
          />
        ))}

        <div>
          <p className="text-sm font-medium text-slate-700 mb-3">Vital Signs</p>
          <div className="grid grid-cols-2 gap-3">
            {field("Heart rate (bpm)", (
              <input className={inputClass} inputMode="numeric" placeholder="72" value={form.hr} onChange={(e) => setForm({ ...form, hr: e.target.value })} />
            ))}
            {field("Blood pressure", (
              <input className={inputClass} placeholder="120/80" value={form.bp} onChange={(e) => setForm({ ...form, bp: e.target.value })} />
            ))}
            {field("Temperature (°C)", (
              <input className={inputClass} inputMode="decimal" placeholder="37.0" value={form.temp} onChange={(e) => setForm({ ...form, temp: e.target.value })} />
            ))}
            {field("SpO₂ (%)", (
              <input className={inputClass} inputMode="numeric" placeholder="98" value={form.spo2} onChange={(e) => setForm({ ...form, spo2: e.target.value })} />
            ))}
          </div>
        </div>

        {field("Preliminary diagnosis", (
          <textarea className={inputClass} rows={2} value={form.diagnosis} onChange={(e) => setForm({ ...form, diagnosis: e.target.value })} />
        ))}

        {field("Treatment given", (
          <textarea className={inputClass} rows={2} value={form.treatment} onChange={(e) => setForm({ ...form, treatment: e.target.value })} />
        ))}

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-ocean-700 text-white py-2.5 rounded-lg font-medium hover:bg-ocean-800 transition-colors disabled:opacity-50"
        >
          {submitting ? "Saving…" : "Save Health Event"}
        </button>
      </form>
    </div>
  );
}
