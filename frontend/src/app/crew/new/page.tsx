"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { CrewMember } from "@/lib/types";
import Link from "next/link";
import { ArrowLeft, UserPlus } from "lucide-react";

const ROLES = [
  "Captain",
  "Chief Engineer",
  "Medical Person in Charge",
  "Cook",
  "Deck Hand",
  "Engineer",
  "Other",
];

const VESSEL_ID = "vessel-mv-resolute-001";

export default function NewCrewPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("Deck Hand");
  const [dob, setDob] = useState("");
  const [bloodType, setBloodType] = useState("");
  const [allergies, setAllergies] = useState("");
  const [notes, setNotes] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactRelation, setContactRelation] = useState("");
  const [contactPhone, setContactPhone] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const payload: Record<string, unknown> = {
        vessel_id: VESSEL_ID,
        full_name: fullName,
        role,
      };
      if (dob) payload.date_of_birth = dob;
      if (bloodType) payload.blood_type = bloodType;
      if (allergies.trim()) {
        payload.allergies = allergies
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean);
      }
      if (notes.trim()) payload.medical_notes = notes;
      if (contactName || contactPhone) {
        payload.emergency_contact = {
          name: contactName,
          relation: contactRelation,
          phone: contactPhone,
        };
      }

      const member = await apiFetch<CrewMember>("/crew", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      router.push(`/crew/detail?id=${member.crew_id}&new=1`);
    } catch (err) {
      setError((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <Link
        href="/crew"
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 mb-6"
      >
        <ArrowLeft size={14} /> Back to roster
      </Link>

      <div className="flex items-center gap-2 mb-6">
        <UserPlus className="text-ocean-600" size={22} />
        <h1 className="text-2xl font-bold text-slate-900">Add crew member</h1>
      </div>

      <form onSubmit={onSubmit} className="space-y-5 bg-white p-6 rounded-xl border border-slate-200">
        {error && (
          <div className="text-red-700 bg-red-50 border border-red-200 rounded-lg p-3 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <Field label="Full name *" required value={fullName} onChange={setFullName} />
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Role *</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm"
            >
              {ROLES.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Date of birth" type="date" value={dob} onChange={setDob} />
          <Field label="Blood type" value={bloodType} onChange={setBloodType} placeholder="e.g. O+" />
        </div>

        <Field
          label="Allergies"
          value={allergies}
          onChange={setAllergies}
          placeholder="comma-separated, e.g. Penicillin, Shellfish"
        />

        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1">Medical notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Existing conditions, medications, anything Gemma should know"
            className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>

        <fieldset className="border border-slate-200 rounded-lg p-4">
          <legend className="text-xs font-semibold text-slate-600 px-2">Emergency contact</legend>
          <div className="grid grid-cols-3 gap-3 mt-2">
            <Field label="Name" value={contactName} onChange={setContactName} />
            <Field label="Relation" value={contactRelation} onChange={setContactRelation} />
            <Field label="Phone" value={contactPhone} onChange={setContactPhone} />
          </div>
        </fieldset>

        <button
          type="submit"
          disabled={submitting || !fullName.trim()}
          className="bg-ocean-600 hover:bg-ocean-700 disabled:bg-slate-300 text-white px-5 py-2 rounded-lg font-medium"
        >
          {submitting ? "Adding…" : "Add crew member"}
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
