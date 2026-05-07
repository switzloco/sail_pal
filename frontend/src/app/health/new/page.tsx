"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { CrewMember } from "@/lib/types";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Sparkles, Mic, MicOff } from "lucide-react";
import { useSpeechToText } from "@/hooks/useSpeechToText";
import { useEffect } from "react";
import ImageUpload from "@/components/ImageUpload";

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
    quick_log: "",
    diagnosis: "",
    treatment: "",
    hr: "",
    bp: "",
    temp: "",
    spo2: "",
    photo_paths: [] as string[],
  });

  const { isListening, transcript, startListening, stopListening, error: sttError } = useSpeechToText();

  useEffect(() => {
    if (transcript) {
      setForm(prev => ({
        ...prev,
        quick_log: (prev.quick_log ? prev.quick_log + " " : "") + transcript
      }));
    }
  }, [transcript]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await apiFetch("/health/events", {
        method: "POST",
        body: JSON.stringify({
          vessel_id: "vessel-mv-resolute-001",
          crew_id: form.crew_id || "guest",
          logged_by: form.logged_by || "unknown",
          severity: form.severity,
          symptoms: form.symptoms ? form.symptoms.split(",").map((s) => s.trim()).filter(Boolean) : [],
          diagnosis: form.diagnosis || (form.quick_log ? `Quick Log: ${form.quick_log}` : undefined),
          treatment: form.treatment || undefined,
          vital_signs: {
            hr: form.hr ? parseInt(form.hr) : undefined,
            bp: form.bp || undefined,
            temp: form.temp ? parseFloat(form.temp) : undefined,
            spo2: form.spo2 ? parseInt(form.spo2) : undefined,
          },
          photo_paths: form.photo_paths,
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
        {/* Quick Log Section */}
        <div className="bg-ocean-50 border border-ocean-100 rounded-xl p-4 mb-2">
          <p className="text-sm font-semibold text-ocean-900 mb-2 flex items-center gap-2">
            <Sparkles size={16} /> Quick Log (Free Text)
          </p>
          <div className="relative">
            <textarea
              className={`${inputClass} bg-white border-ocean-200 focus:ring-ocean-500 pr-10`}
              placeholder="e.g. Cook has a deep cut on his left thumb from a kitchen knife. Bleeding is heavy but controlled with pressure..."
              rows={3}
              value={form.quick_log}
              onChange={(e) => setForm({ ...form, quick_log: e.target.value })}
              autoCorrect="off"
              spellCheck="false"
              autoComplete="off"
            />
            <button 
              type="button"
              onClick={isListening ? stopListening : startListening}
              className={`absolute right-3 top-3 transition-colors ${isListening ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-ocean-600'}`}
              title={isListening ? "Stop Recording" : "Voice Dictation"}
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </button>
            {sttError && <p className="text-[10px] text-red-500 mt-1 absolute right-0 -bottom-4">{sttError}</p>}
          </div>
          <p className="text-[10px] text-ocean-600 mt-2 flex justify-between items-center">
            <span>Tip: You can just type the whole story here and hit save.</span>
            <button
              type="button"
              onClick={async () => {
                if (!form.quick_log) return;
                try {
                  const res = await apiFetch<any>("/ai/extract-medical-info", {
                    method: "POST",
                    body: JSON.stringify({ text: form.quick_log })
                  });
                  if (res) {
                    setForm(prev => ({
                      ...prev,
                      symptoms: res.symptoms || prev.symptoms,
                      hr: res.hr?.toString() || prev.hr,
                      bp: res.bp || prev.bp,
                      temp: res.temp?.toString() || prev.temp,
                      spo2: res.spo2?.toString() || prev.spo2,
                      severity: res.severity || prev.severity,
                    }));
                  }
                } catch (e) {
                  console.error("Extraction failed", e);
                }
              }}
              className="bg-ocean-100 hover:bg-ocean-200 text-ocean-700 px-2 py-1 rounded text-[9px] font-bold uppercase tracking-wider transition-colors"
            >
              Auto-Fill Form
            </button>
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {field("Patient", (
            <select
              className={selectClass}
              value={form.crew_id}
              onChange={(e) => setForm({ ...form, crew_id: e.target.value })}
            >
              <option value="">Unknown / Guest</option>
              {crew?.map((m) => (
                <option key={m.crew_id} value={m.crew_id}>{m.full_name} — {m.role}</option>
              ))}
            </select>
          ))}

          {field("Logged by (MPIC)", (
            <select
              className={selectClass}
              value={form.logged_by}
              onChange={(e) => setForm({ ...form, logged_by: e.target.value })}
            >
              <option value="">Unknown</option>
              {crew?.map((m) => (
                <option key={m.crew_id} value={m.crew_id}>{m.full_name} — {m.role}</option>
              ))}
            </select>
          ))}
        </div>

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
            autoCorrect="off"
            spellCheck="false"
            autoComplete="off"
          />
        ))}

        <div>
          <p className="text-sm font-medium text-slate-700 mb-3">Vital Signs</p>
          <div className="grid grid-cols-2 gap-3">
            {field("Heart rate (bpm)", (
              <input className={inputClass} inputMode="numeric" placeholder="72" value={form.hr} onChange={(e) => setForm({ ...form, hr: e.target.value })} autoCorrect="off" spellCheck="false" />
            ))}
            {field("Blood pressure", (
              <input className={inputClass} placeholder="120/80" value={form.bp} onChange={(e) => setForm({ ...form, bp: e.target.value })} autoCorrect="off" spellCheck="false" />
            ))}
            {field("Temperature (°C)", (
              <input className={inputClass} inputMode="decimal" placeholder="37.0" value={form.temp} onChange={(e) => setForm({ ...form, temp: e.target.value })} autoCorrect="off" spellCheck="false" />
            ))}
            {field("SpO₂ (%)", (
              <input className={inputClass} inputMode="numeric" placeholder="98" value={form.spo2} onChange={(e) => setForm({ ...form, spo2: e.target.value })} autoCorrect="off" spellCheck="false" />
            ))}
          </div>
        </div>

        {field("Preliminary diagnosis", (
          <textarea className={inputClass} rows={2} value={form.diagnosis} onChange={(e) => setForm({ ...form, diagnosis: e.target.value })} autoCorrect="off" spellCheck="false" />
        ))}

        {field("Treatment given", (
          <textarea className={inputClass} rows={2} value={form.treatment} onChange={(e) => setForm({ ...form, treatment: e.target.value })} autoCorrect="off" spellCheck="false" />
        ))}

        <ImageUpload 
          label="Medical Photos" 
          multiple 
          onUploadComplete={(paths) => setForm(prev => ({ ...prev, photo_paths: [...prev.photo_paths, ...paths] }))} 
        />

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
