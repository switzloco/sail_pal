"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Anchor, Users, HeartPulse, Wrench, Settings, Sparkles } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Vessel } from "@/lib/types";
import Image from "next/image";

const NAV = [
  { href: "/", label: "Dashboard", icon: Anchor },
  { href: "/chat", label: "Ask Gemma", icon: Sparkles },
  { href: "/crew", label: "Crew", icon: Users },
  { href: "/health", label: "Health Log", icon: HeartPulse },
  { href: "/vessel", label: "Components", icon: Wrench },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const path = usePathname();
  const { data: vessel } = useQuery({ queryKey: ["vessel-info"], queryFn: () => apiFetch<Vessel>("/setup/vessel-info") });

  return (
    <aside className="w-56 shrink-0 bg-ocean-900 text-white flex flex-col min-h-screen">
      <div className="px-5 py-6 border-b border-ocean-800 flex items-center gap-3">
        <div className="bg-white p-1.5 rounded-lg shrink-0">
          <Image src="/images/logo.png" alt="Logo" width={24} height={24} />
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-widest text-ocean-500 leading-none mb-1">Vessel Ops AI</p>
          <p className="font-bold text-sm leading-tight truncate w-28">{vessel?.name ?? "MV Resolute"}</p>
        </div>
      </div>
      <nav className="flex-1 py-4">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-5 py-3 text-sm font-medium transition-colors ${
                active
                  ? "bg-ocean-700 text-white"
                  : "text-ocean-100 hover:bg-ocean-800 hover:text-white"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="px-5 py-4 border-t border-ocean-800 text-xs text-ocean-300">
        <p className="font-semibold text-ocean-100">Powered by Gemma</p>
        <p className="text-ocean-400 mt-0.5">Google DeepMind · Offline-ready</p>
      </div>
    </aside>
  );
}
