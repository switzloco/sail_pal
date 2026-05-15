"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch, getApiKey, getUploadUrl } from "@/lib/api";
import type { Component } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { Wrench, Plus, Upload } from "lucide-react";
import { useRef, useState } from "react";

const SYSTEM_LABELS: Record<string, string> = {
  propulsion: "Propulsion",
  electrical: "Electrical",
  navigation: "Navigation",
  hvac: "HVAC",
  safety: "Safety",
  hull: "Hull",
};

export default function VesselPage() {
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: components, isLoading } = useQuery({
    queryKey: ["components"],
    queryFn: () => apiFetch<Component[]>("/components"),
  });

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const file = e.target.files[0];
    
    const formData = new FormData();
    formData.append("category", "engine_manuals");
    formData.append("file", file);

    setIsUploading(true);
    try {
      const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000") + "/api";
      const key = getApiKey();
      const res = await fetch(`${API_BASE}/ai/upload-manual`, {
        method: "POST",
        headers: key ? { "x-api-key": key } : {},
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      alert("Manual processed and ingested into RAG Engine successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to upload manual.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const grouped = components?.reduce((acc, c) => {
    (acc[c.system] = acc[c.system] || []).push(c);
    return acc;
  }, {} as Record<string, Component[]>);

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Component Inventory</h1>
        <div className="flex gap-2">
          <input 
            type="file" 
            accept=".pdf" 
            ref={fileInputRef} 
            onChange={handleUpload} 
            className="hidden" 
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="inline-flex items-center gap-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium px-3 py-2 rounded-lg disabled:opacity-50"
          >
            <Upload size={16} /> {isUploading ? "Processing..." : "Upload Manual"}
          </button>
          <Link
            href="/vessel/new"
            className="inline-flex items-center gap-1 bg-ocean-600 hover:bg-ocean-700 text-white text-sm font-medium px-3 py-2 rounded-lg"
          >
            <Plus size={16} /> Add component
          </Link>
        </div>
      </div>

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
                href={`/vessel/detail?id=${c.component_id}`}
                className="flex items-center gap-4 bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md transition-shadow"
              >
                {c.photo_path ? (
                  <img src={getUploadUrl(c.photo_path)} alt={c.name} className="w-10 h-10 rounded-lg object-cover shrink-0 border border-slate-100" />
                ) : (
                  <Wrench size={18} className="text-slate-400 shrink-0" />
                )}
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
