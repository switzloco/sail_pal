"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { X, ExternalLink, AlertCircle, Info, CheckCircle2 } from "lucide-react";
import Link from "next/link";

type ToastType = "success" | "error" | "info";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  action?: {
    label: string;
    href: string;
  };
}

interface ToastContextType {
  showToast: (message: string, type: ToastType, action?: { label: string; href: string }) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType, action?: { label: string; href: string }) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type, action }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 w-full max-w-md pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`
              pointer-events-auto
              flex items-start gap-4 p-4 rounded-2xl border shadow-2xl backdrop-blur-xl animate-in slide-in-from-right-full fade-in duration-300
              ${toast.type === "error" ? "bg-rose-500/10 border-rose-500/20 text-rose-200" : ""}
              ${toast.type === "success" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-200" : ""}
              ${toast.type === "info" ? "bg-ocean-500/10 border-ocean-500/20 text-ocean-200" : ""}
            `}
          >
            <div className="mt-0.5">
              {toast.type === "error" && <AlertCircle className="text-rose-500" size={20} />}
              {toast.type === "success" && <CheckCircle2 className="text-emerald-500" size={20} />}
              {toast.type === "info" && <Info className="text-ocean-500" size={20} />}
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium leading-relaxed text-white">
                {toast.message}
              </p>
              {toast.action && (
                <Link
                  href={toast.action.href}
                  className={`
                    mt-3 inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg transition-all
                    ${toast.type === "error" ? "bg-rose-500 text-white hover:bg-rose-600" : "bg-ocean-600 text-white hover:bg-ocean-700"}
                  `}
                >
                  {toast.action.label} <ExternalLink size={12} />
                </Link>
              )}
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="p-1 hover:bg-white/10 rounded-lg transition-colors text-white/40 hover:text-white"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}
