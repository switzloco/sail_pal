"use client";

import { useState } from "react";
import { SetupWizard } from "./SetupWizard";

export function SetupGate({ children }: { children: React.ReactNode }) {
  // Start optimistically assuming setup is complete to avoid flash on returning visits.
  // SetupWizard will call onComplete immediately if status is already green.
  const [ready, setReady] = useState(false);
  const [checked, setChecked] = useState(false);

  function handleComplete() {
    setReady(true);
    setChecked(true);
  }

  if (ready) return <>{children}</>;

  // Render wizard (it calls onComplete on its own if everything is already set up)
  return (
    <>
      <SetupWizard onComplete={handleComplete} />
      {/* Keep children mounted but hidden so Next.js doesn't re-fetch on reveal */}
      <div className="hidden">{checked ? null : children}</div>
    </>
  );
}
