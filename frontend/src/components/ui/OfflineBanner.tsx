"use client";

import { useEffect, useState } from "react";
import { pingBackend } from "@/lib/api";

export function OfflineBanner() {
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    async function check() {
      const ok = await pingBackend();
      setBackendDown(!ok);
    }
    check();
    const id = setInterval(check, 15_000);
    return () => clearInterval(id);
  }, []);

  if (!backendDown) return null;

  return (
    <div className="sticky top-0 z-50 bg-yellow-400 text-yellow-900 text-sm font-semibold px-4 py-2 text-center">
      ⚠ Backend unreachable — working in offline mode. Data will sync when connection is restored.
    </div>
  );
}
