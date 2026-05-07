"use client";

import { useState, useRef } from "react";
import { Camera, X, UploadCloud, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface ImageUploadProps {
  onUploadComplete: (paths: string[]) => void;
  multiple?: boolean;
  label?: string;
}

export default function ImageUpload({ onUploadComplete, multiple = false, label = "Upload Images" }: ImageUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [previews, setPreviews] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    const formData = new FormData();
    const newPreviews: string[] = [];

    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
      newPreviews.push(URL.createObjectURL(files[i]));
    }

    setPreviews(prev => [...prev, ...newPreviews]);

    try {
      const response = await apiFetch<{ paths: string[] }>("/uploads", {
        method: "POST",
        body: formData,
      });
      onUploadComplete(response.paths);
    } catch (err) {
      console.error("Upload failed", err);
      alert("Failed to upload images");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <span className="text-sm font-medium text-slate-700 block">{label}</span>
      
      <div className="flex flex-wrap gap-3">
        {previews.map((src, i) => (
          <div key={i} className="relative w-20 h-20 rounded-lg overflow-hidden border border-slate-200 group">
            <img src={src} alt="preview" className="w-full h-full object-cover" />
            <button
              type="button"
              className="absolute top-1 right-1 bg-black/50 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={() => setPreviews(prev => prev.filter((_, idx) => idx !== i))}
            >
              <X size={12} />
            </button>
          </div>
        ))}
        
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="w-20 h-20 rounded-lg border-2 border-dashed border-slate-300 flex flex-col items-center justify-center text-slate-400 hover:border-ocean-400 hover:text-ocean-500 transition-colors disabled:opacity-50"
        >
          {uploading ? (
            <Loader2 size={24} className="animate-spin text-ocean-600" />
          ) : (
            <>
              <Camera size={24} />
              <span className="text-[10px] mt-1 font-medium">Add Photo</span>
            </>
          )}
        </button>
      </div>
      
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        multiple={multiple}
        accept="image/*"
        className="hidden"
      />
    </div>
  );
}
