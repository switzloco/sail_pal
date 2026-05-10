"use client";

import React, { useEffect, useState } from "react";
import { getBackendStatus } from "@/lib/network";
import { fetchSetupStatus } from "@/lib/setup";

export const NetworkStatus = () => {
  const [isLocalOnline, setIsLocalOnline] = useState<boolean | null>(null);
  const [isInternetOnline, setIsInternetOnline] = useState<boolean>(true);
  const [isModelReady, setIsModelReady] = useState<boolean | null>(null);

  useEffect(() => {
    const checkStatus = async () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
      const status = await getBackendStatus(apiUrl);
      setIsLocalOnline(status);
      setIsInternetOnline(navigator.onLine);

      if (status) {
        try {
          const setupStatus = await fetchSetupStatus();
          setIsModelReady(setupStatus.model_ready);
        } catch (e) {
          setIsModelReady(false);
        }
      } else {
         setIsModelReady(null);
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 10000);
    window.addEventListener("online", () => setIsInternetOnline(true));
    window.addEventListener("offline", () => setIsInternetOnline(false));

    return () => {
      clearInterval(interval);
      window.removeEventListener("online", () => setIsInternetOnline(true));
      window.removeEventListener("offline", () => setIsInternetOnline(false));
    };
  }, []);

  return (
    <div className="fixed top-4 right-4 z-50 flex items-center gap-3 bg-black/40 backdrop-blur-md px-4 py-2 rounded-full border border-white/10 shadow-2xl">
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${
            isLocalOnline ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-rose-500"
          }`}
        />
        <span className="text-[10px] font-bold tracking-widest uppercase text-white/70">
          Local: {isLocalOnline ? "Connected" : "Disconnected"}
        </span>
      </div>
      <div className="w-[1px] h-3 bg-white/10" />
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${
            isInternetOnline ? "bg-sky-500" : "bg-amber-500"
          }`}
        />
        <span className="text-[10px] font-bold tracking-widest uppercase text-white/70">
          Net: {isInternetOnline ? "Online" : "Offline"}
        </span>
      </div>
      {isLocalOnline && isInternetOnline && (
        <>
          <div className="w-[1px] h-3 bg-white/10" />
          <div className="flex items-center gap-2">
             <span
              className={`w-2 h-2 rounded-full ${
                isModelReady ? "bg-green-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.6)]"
              }`}
            />
            <span className={`text-[10px] font-bold tracking-widest uppercase ${isModelReady ? 'text-green-400' : 'text-yellow-400'}`}>
              {isModelReady ? "Ready for Sea" : "Missing Model"}
            </span>
          </div>
        </>
      )}
    </div>
  );
};
