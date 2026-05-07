"use client";
import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/ui/QueryProvider";
import { Sidebar } from "@/components/ui/Sidebar";
import { OfflineBanner } from "@/components/ui/OfflineBanner";
import { CloudBanner } from "@/components/ui/CloudBanner";
import { SetupGate } from "@/components/setup/SetupGate";
import { useState } from "react";
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
                      <span className="ml-3 font-bold text-sm">Sail Pal</span>
                    </header>
                    <main className="flex-1 p-4 md:p-8 overflow-auto">{children}</main>
                  </div>
                </div>
              </>
            )}
            </SetupGate>
          </ToastProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
