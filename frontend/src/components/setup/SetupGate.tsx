"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { isTauri } from "@/lib/platform";
import { setMode } from "@/lib/setup";

export function SetupGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Desktop .exe users are here to run offline. Skip the welcome wizard
    // entirely: mark onboarded, fire-and-forget setMode("local"), render
    // the app. If Ollama isn't ready, the main UI surfaces that — much
    // better than hiding the app behind a setup page.
    if (isTauri()) {
      if (localStorage.getItem("vessel_ops_onboarded") !== "true") {
        localStorage.setItem("vessel_ops_onboarded", "true");
        setMode("local").catch(() => {
          // Cloud-mode forced or backend not up yet — non-fatal.
        });
      }
      setReady(true);
      return;
    }

    const onboarded = localStorage.getItem("vessel_ops_onboarded");
    if (onboarded === "true" || pathname?.startsWith("/welcome")) {
      setReady(true);
    } else {
      router.push("/welcome");
    }
  }, [pathname, router]);

  if (!ready) return null;

  return <>{children}</>;
}
