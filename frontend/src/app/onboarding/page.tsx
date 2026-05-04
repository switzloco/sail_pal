"use client";

import React, { useState, useEffect } from "react";
import { isMobile } from "@/lib/network";
import Link from "next/link";

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [deviceType, setDeviceType] = useState<"mobile" | "desktop">("desktop");

  useEffect(() => {
    setDeviceType(isMobile() ? "mobile" : "desktop");
  }, []);

  return (
    <div className="min-h-screen bg-[#05070a] text-white flex flex-col items-center justify-center p-6 font-sans">
      <div className="max-w-md w-full bg-[#0c1016] border border-white/5 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
        {/* Decorative Background */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-blue-600/10 blur-[100px] rounded-full" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-emerald-600/10 blur-[100px] rounded-full" />

        {step === 1 && (
          <div className="space-y-6 relative">
            <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center border border-blue-500/30 mb-8">
              <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Vessel Ops AI</h1>
            <p className="text-white/60 leading-relaxed">
              Welcome aboard. This is a <strong>Local-First</strong> application. It is designed to work in the middle of the ocean with zero internet.
            </p>
            <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-xl">
              <p className="text-amber-200/80 text-sm">
                If you are connected to the internet now, you can use the <strong>Cloud Test Mode</strong>, but for production, you must connect to the boat&apos;s server.
              </p>
            </div>
            <button
              onClick={() => setStep(2)}
              className="w-full bg-white text-black font-bold py-4 rounded-xl hover:bg-white/90 transition-all shadow-xl shadow-white/5"
            >
              Get Started
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6 relative">
            <h2 className="text-2xl font-bold">Network Setup</h2>
            <p className="text-white/60 text-sm">
              You are currently on a <strong>{deviceType}</strong> device.
            </p>
            
            <div className="space-y-4">
              <div className="p-4 bg-white/5 border border-white/10 rounded-xl">
                <h3 className="font-bold text-white/90 mb-1">1. Connect to Wi-Fi</h3>
                <p className="text-xs text-white/50">Ensure you are on the local boat network (e.g., &apos;MV-RESOLUTE-WIFI&apos;).</p>
              </div>
              <div className="p-4 bg-white/5 border border-white/10 rounded-xl">
                <h3 className="font-bold text-white/90 mb-1">2. Target Server</h3>
                <p className="text-xs text-white/50">Point your browser to the server IP: <code>192.168.1.100</code></p>
              </div>
              <div className="p-4 bg-white/5 border border-white/10 rounded-xl">
                <h3 className="font-bold text-white/90 mb-1">3. Offline Ready</h3>
                <p className="text-xs text-white/50">Once paired, the app will store everything locally on the hub.</p>
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                onClick={() => setStep(1)}
                className="flex-1 bg-white/5 text-white/70 font-bold py-4 rounded-xl border border-white/10 hover:bg-white/10 transition-all"
              >
                Back
              </button>
              <Link href="/" className="flex-[2]">
                <button className="w-full bg-blue-600 text-white font-bold py-4 rounded-xl hover:bg-blue-500 transition-all shadow-xl shadow-blue-600/20">
                  Launch App
                </button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
