import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/ui/QueryProvider";
import { Sidebar } from "@/components/ui/Sidebar";
import { OfflineBanner } from "@/components/ui/OfflineBanner";
import { SetupGate } from "@/components/setup/SetupGate";

export const metadata: Metadata = {
  title: "Vessel Ops AI",
  description: "Offline AI assistant for maritime medical and engineering operations",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <SetupGate>
            <OfflineBanner />
            <div className="flex min-h-screen">
              <Sidebar />
              <main className="flex-1 p-8 overflow-auto">{children}</main>
            </div>
          </SetupGate>
        </QueryProvider>
      </body>
    </html>
  );
}
