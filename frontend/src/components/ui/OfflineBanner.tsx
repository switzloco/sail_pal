import { useEffect, useState } from "react";
import { pingBackend } from "@/lib/api";
import { processQueue, getQueue } from "@/lib/offlineQueue";

export function OfflineBanner() {
  const [backendDown, setBackendDown] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    async function check() {
      const ok = await pingBackend();
      if (ok && backendDown) {
        // Just came back online!
        processQueue().then(count => {
          if (count > 0) console.log(`Synced ${count} items from queue.`);
          setPendingCount(getQueue().length);
        });
      }
      setBackendDown(!ok);
      setPendingCount(getQueue().length);
    }
    check();
    const id = setInterval(check, 10_000); // Check every 10s
    return () => clearInterval(id);
  }, [backendDown]);

  if (!backendDown && pendingCount === 0) return null;

  if (backendDown) {
    return (
      <div className="sticky top-0 z-50 bg-red-600 text-white text-xs font-bold px-4 py-2 text-center shadow-lg animate-in slide-in-from-top duration-300">
        ⚠ Backend unreachable — Working offline. {pendingCount > 0 && `(${pendingCount} changes pending sync)`}
      </div>
    );
  }

  if (pendingCount > 0) {
    return (
      <div className="sticky top-0 z-50 bg-blue-600 text-white text-[10px] font-bold px-4 py-1 text-center shadow-sm">
        Syncing {pendingCount} pending changes...
      </div>
    );
  }

  return null;
}

