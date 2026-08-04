"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch, authHeaders, getUploadUrl } from "@/lib/api";
import type { Component } from "@/lib/types";
import { CardSkeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { Wrench, Plus, Upload, Search, Package, Sparkles } from "lucide-react";
import { useMemo, useRef, useState } from "react";

const SYSTEM_LABELS: Record<string, string> = {
  propulsion: "Propulsion",
  electrical: "Electrical",
  navigation: "Navigation",
  hvac: "HVAC",
  safety: "Safety",
  hull: "Hull",
};

export default function InventoryPage() {
  const [isUploading, setIsUploading] = useState(false);
  const [search, setSearch] = useState("");
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
      const res = await fetch(`${API_BASE}/ai/upload-manual`, {
        method: "POST",
        headers: await authHeaders(),
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

  // Search spans spares too — "do we have an impeller" is the question this
  // page exists to answer, and impellers live in spare_parts, not in a name.
  const filtered = useMemo(() => {
    if (!components) return undefined;
    const q = search.trim().toLowerCase();
    if (!q) return components;
    return components.filter((c) =>
      [c.name, c.manufacturer, c.model_number, c.serial_number, c.location, ...(c.spare_parts ?? [])]
        .filter(Boolean)
        .some((field) => String(field).toLowerCase().includes(q))
    );
  }, [components, search]);

  const spareCount = components?.reduce((n, c) => n + (c.spare_parts?.length ?? 0), 0) ?? 0;

  const grouped = filtered?.reduce((acc, c) => {
    (acc[c.system] = acc[c.system] || []).push(c);
    return acc;
  }, {} as Record<string, Component[]>);

  return (
    <div className="max-w-3xl">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
        <div>
          <div className="flex items-center gap-2">
            <Package className="text-ocean-600" size={22} />
            <h1 className="text-2xl font-bold text-slate-900">Inventory</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            {components ? `${components.length} components · ${spareCount} spares held` : "Loading…"}
          </p>
        </div>
        <div className="flex gap-2">
          <input type="file" accept=".pdf" ref={fileInputRef} onChange={handleUpload} className="hidden" />
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
            <Plus size={16} /> Add
          </Link>
        </div>
      </div>

      <p className="text-xs text-slate-500 bg-ocean-50 border border-ocean-100 rounded-lg px-3 py-2 mb-5 flex items-start gap-2">
        <Sparkles size={14} className="text-ocean-500 mt-0.5 shrink-0" />
        <span>
          Gemma reads this inventory on every question, so it knows what&apos;s aboard before it
          recommends a repair. <Link href="/chat" className="font-semibold text-ocean-700 hover:underline">Ask it something</Link>.
        </span>
      </p>

      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search components, part numbers, locations, spares…"
          className="w-full bg-white border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ocean-500"
        />
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      )}

      {filtered?.length === 0 && (
        <p className="text-sm text-slate-500 py-8 text-center">
          {search ? `Nothing aboard matches “${search}”.` : "No components recorded yet."}
        </p>
      )}

      {grouped &&
        Object.entries(grouped).map(([system, items]) => (
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
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={getUploadUrl(c.photo_path)}
                      alt={c.name}
                      className="w-10 h-10 rounded-lg object-cover shrink-0 border border-slate-100"
                    />
                  ) : (
                    <Wrench size={18} className="text-slate-400 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 truncate">{c.name}</p>
                    <p className="text-sm text-slate-500 truncate">
                      {[c.manufacturer, c.location].filter(Boolean).join(" · ") || "No details recorded"}
                    </p>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-1 rounded-full shrink-0 uppercase tracking-wide ${
                      c.spare_parts?.length
                        ? "bg-green-50 text-green-700"
                        : "bg-slate-100 text-slate-400"
                    }`}
                  >
                    {c.spare_parts?.length
                      ? `${c.spare_parts.length} spare${c.spare_parts.length === 1 ? "" : "s"}`
                      : "No spares"}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        ))}
    </div>
  );
}
