"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Anchor, Users, HeartPulse, Wrench, Settings, Sparkles, X } from "lucide-react";
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

export function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const path = usePathname();
  const { data: vessel } = useQuery({ queryKey: ["vessel-info"], queryFn: () => apiFetch<Vessel>("/setup/vessel-info") });

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden" 
          onClick={onClose}
        />
      )}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-ocean-900 text-white flex flex-col transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
      `}>
      <div className="px-5 py-6 border-b border-ocean-800 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="bg-white p-1.5 rounded-lg shrink-0">
            <Image src="/images/logo.png" alt="Logo" width={24} height={24} />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-ocean-500 leading-none mb-1">Vessel Ops AI</p>
            <p className="font-bold text-sm leading-tight truncate w-28">{vessel?.name ?? "MV Resolute"}</p>
          </div>
        </div>
        <button 
          onClick={onClose}
          className="p-2 -mr-2 text-ocean-400 hover:text-white lg:hidden"
          aria-label="Close menu"
        >
          <X size={20} />
        </button>
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
      <div className="px-5 py-6 border-t border-ocean-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-ocean-800 flex items-center justify-center text-ocean-400">
            <Anchor size={16} />
          </div>
          <div>
            <p className="text-xs font-bold text-white">Sail Pal v1.2</p>
            <p className="text-[10px] text-ocean-400 uppercase tracking-tighter">Offline Intelligence</p>
          </div>
        </div>
      </div>
    </aside>
    </>
  );
}
