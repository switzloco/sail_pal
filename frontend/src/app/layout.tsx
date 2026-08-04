"use client";
import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/ui/QueryProvider";
import { Sidebar } from "@/components/ui/Sidebar";
import { OfflineBanner } from "@/components/ui/OfflineBanner";
import { CloudBanner } from "@/components/ui/CloudBanner";
import { SetupGate } from "@/components/setup/SetupGate";
import { AuthGate } from "@/components/auth/AuthGate";
import { isTauri } from "@/lib/platform";
import { useState, useEffect } from "react";
import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { ToastProvider } from "@/components/ui/Toast";

// Metadata must be in a separate Server Component or metadata.ts in Next.js 13+ App Router
// export const metadata: Metadata = {
//   title: "Sail Pal",
//   description: "Offline AI assistant for maritime medical and engineering operations",
// };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();

  // Register service worker for offline PWA support — web only.
  //
  // In Tauri the WebView serves the bundle from the local asset protocol;
  // there is no offline edge case. Worse, a SW registered against
  // tauri://localhost survives app upgrades: it keeps serving the old
  // cached index.html, which references chunk hashes that no longer exist
  // in the new install, blanking the screen. So on Tauri we actively
  // unregister any stale SW and clear its caches.
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    if (isTauri()) {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((reg) => reg.unregister());
      });
      if ("caches" in window) {
        caches.keys().then((keys) => keys.forEach((k) => caches.delete(k)));
      }
      return;
    }
    navigator.serviceWorker
      .register("/sw.js")
      .then((reg) => console.log("SW registered, scope:", reg.scope))
      .catch((err) => console.warn("SW registration failed:", err));
  }, []);

  const isWelcomePage = pathname?.startsWith("/welcome");

  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#0369a1" />
      </head>
      <body>
        <QueryProvider>
          <ToastProvider>
            <AuthGate>
            <SetupGate>
            {isWelcomePage ? (
              <main className="min-h-screen bg-slate-50">{children}</main>
            ) : (
              <>
                <OfflineBanner />
                <CloudBanner />
                <div className="flex min-h-screen relative">
                  <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
                  <div className="flex-1 flex flex-col min-w-0">
                    <header className="lg:hidden h-14 bg-ocean-900 text-white flex items-center px-4 shrink-0">
                      <button 
                        onClick={() => setSidebarOpen(true)}
                        className="p-2 hover:bg-ocean-800 rounded-lg"
                      >
                        <Menu size={20} />
                      </button>
                      <span className="ml-3 font-bold text-sm">Vessel Ops AI</span>
                    </header>
                    <main className="flex-1 p-4 md:p-8 overflow-auto">{children}</main>
                  </div>
                </div>
              </>
            )}
            </SetupGate>
            </AuthGate>
          </ToastProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
