"use client";

import { useEffect, useState } from "react";
import { fetchSetupStatus } from "@/lib/setup";

export function CloudBanner() {
  const [isCloud, setIsCloud] = useState(false);

  useEffect(() => {
    fetchSetupStatus()
      .then((s) => setIsCloud(s.mode === "cloud"))
      .catch(() => {});
  }, []);

  if (!isCloud) return null;

  return (
    <div className="sticky top-0 z-50 bg-amber-400 text-amber-950 text-sm font-semibold px-4 py-2 text-center flex items-center justify-center gap-2">
      ☁ Cloud preview — AI responses processed by Google (not local). Install Ollama for offline use.
    </div>
  );
}
