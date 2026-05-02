"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";

export function SetupGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
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
