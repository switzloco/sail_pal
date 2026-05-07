"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { Component } from "@/lib/types";
import Link from "next/link";
import { ArrowLeft, Wrench } from "lucide-react";
import ImageUpload from "@/components/ImageUpload";

const SYSTEMS = [
  { value: "propulsion", label: "Propulsion" },
  { value: "electrical", label: "Electrical" },
  { value: "navigation", label: "Navigation" },
  { value: "hvac", label: "HVAC" },
  { value: "safety", label: "Safety" },
  { value: "hull", label: "Hull" },
];

const VESSEL_ID = "vessel-mv-resolute-001";

export default function NewComponentPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [system, setSystem] = useState("propulsion");
  const [manufacturer, setManufacturer] = useState("");
  const [modelNumber, setModelNumber] = useState("");
  const [serialNumber, setSerialNumber] = useState("");
  const [installDate, setInstallDate] = useState("");
  const [location, setLocation] = useState("");
  const [manualRef, setManualRef] = useState("");
  const [spareParts, setSpareParts] = useState("");
  const [notes, setNotes] = useState("");
  const [photoPath, setPhotoPath] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const payload: Record<string, unknown> = {
        vessel_id: VESSEL_ID,
        name,
        system,
      };
      if (manufacturer) payload.manufacturer = manufacturer;
      if (modelNumber) payload.model_number = modelNumber;
      if (serialNumber) payload.serial_number = serialNumber;
      if (installDate) payload.install_date = installDate;
      if (location) payload.location = location;
      if (manualRef) payload.manual_ref = manualRef;
      if (spareParts.trim()) {
        payload.spare_parts = spareParts
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean);
      }
      if (notes.trim()) payload.notes = notes;
      if (photoPath) payload.photo_path = photoPath;

      const comp = await apiFetch<Component>("/components", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      router.push(`/vessel/detail?id=${comp.component_id}&new=1`);
    } catch (err) {
      setError((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <Link
        href="/vessel"
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft size={14} /> Back to inventory
      </Link>

      <div className="flex items-center gap-2 mb-6">
        <Wrench className="text-ocean-600" size={22} />
        <h1 className="text-2xl font-bold text-slate-900">Add component</h1>
      </div>

      <form onSubmit={onSubmit} className="space-y-5 bg-white p-6 rounded-xl border border-slate-200">
        {error && (
          <div className="text-red-700 bg-red-50 border border-red-200 rounded-lg p-3 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <Field label="Name *" required value={name} onChange={setName} placeholder="e.g. Main Engine" />
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">System *</label>
            <select
              value={system}
              onChange={(e) => setSystem(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              {SYSTEMS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Manufacturer" value={manufacturer} onChange={setManufacturer} placeholder="e.g. MAN B&W" />
          <Field label="Model number" value={modelNumber} onChange={setModelNumber} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Serial number" value={serialNumber} onChange={setSerialNumber} />
          <Field label="Install date" type="date" value={installDate} onChange={setInstallDate} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Location on vessel" value={location} onChange={setLocation} placeholder="e.g. Engine room, port side" />
          <Field label="Manual reference" value={manualRef} onChange={setManualRef} />
        </div>

        <Field
          label="Spare parts on board"
          value={spareParts}
          onChange={setSpareParts}
          placeholder="comma-separated, e.g. fuel filter, gasket set"
        />

        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Anything Gemma should know when diagnosing this component"
            className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>

        <ImageUpload 
          label="Component Photo" 
          onUploadComplete={(paths) => setPhotoPath(paths[0])} 
        />

        <button
          type="submit"
          disabled={submitting || !name.trim()}
          className="bg-ocean-600 hover:bg-ocean-700 disabled:bg-slate-300 text-white px-5 py-2 rounded-lg font-medium"
        >
          {submitting ? "Adding…" : "Add component"}
        </button>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-600 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm"
      />
    </div>
  );
}
