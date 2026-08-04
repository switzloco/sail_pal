"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Anchor, Users, HeartPulse, Settings, Sparkles, X, Package, BookOpen, Share2, ClipboardList } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, getApiBase } from "@/lib/api";
import type { Vessel } from "@/lib/types";
import Image from "next/image";

// The app is deliberately pared back to two pillars: Medical and Inventory.
// /study (MPIC Study) and /trivia still exist and still work if you navigate
// to them directly — they are just no longer part of the primary experience.
const NAV_SECTIONS = [
  {
    title: "Medical",
    items: [
      { href: "/health", label: "Health Log", icon: HeartPulse },
      { href: "/crew", label: "Crew", icon: Users },
    ],
  },
  {
    title: "Inventory",
    items: [
      { href: "/vessel", label: "Components & Spares", icon: Package },
      { href: "/maintenance", label: "Maintenance Log", icon: ClipboardList },
    ],
  },
] as const;

const SHARE_URL = "https://vessel-ops-494701.web.app/";
const SHARE_TEXT = "Vessel Ops AI — offline-first maritime medical & engineering assistant, powered by Gemma. Try it free:";

async function handleShare() {
  const payload = { title: "Vessel Ops AI", text: SHARE_TEXT, url: SHARE_URL };
  if (typeof navigator !== "undefined" && "share" in navigator) {
    try {
      await navigator.share(payload);
      return;
    } catch {
      // User cancelled or share unsupported — fall through to clipboard.
    }
  }
  if (typeof navigator !== "undefined" && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(`${SHARE_TEXT}\n${SHARE_URL}`);
      alert("Share link copied to clipboard!");
    } catch {
      window.prompt("Copy this link:", SHARE_URL);
    }
  } else {
    window.prompt("Copy this link:", SHARE_URL);
  }
}

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
              <p className="text-xs uppercase tracking-widest text-ocean-500 leading-none mb-1">Vessel Ops AI</p>
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

        <nav className="flex-1 py-4 space-y-6">
          <div>
            <Link
              href="/chat"
              className={`flex items-center gap-3 mx-3 mb-4 px-4 py-3 rounded-xl text-sm font-bold transition-colors ${
                path.startsWith("/chat")
                  ? "bg-ocean-500 text-white"
                  : "bg-ocean-700/60 text-white hover:bg-ocean-700"
              }`}
            >
              <Sparkles size={18} />
              Ask Gemma
            </Link>
            <Link
              href="/"
              className={`flex items-center gap-3 px-5 py-3 text-sm font-medium transition-colors ${
                path === "/" ? "bg-ocean-700 text-white" : "text-ocean-100 hover:bg-ocean-800 hover:text-white"
              }`}
            >
              <Anchor size={18} />
              Dashboard
            </Link>
          </div>

          {NAV_SECTIONS.map(({ title, items }) => (
            <div key={title}>
              <p className="px-5 text-[10px] font-bold text-ocean-400 uppercase tracking-widest mb-2">{title}</p>
              {items.map(({ href, label, icon: Icon }) => {
                const active = path.startsWith(href);
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
            </div>
          ))}

          <div>
            <p className="px-5 text-[10px] font-bold text-ocean-400 uppercase tracking-widest mb-2">Reference</p>
            <a
              href={`${getApiBase()}/api/setup/who-manual`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-5 py-3 text-sm font-medium text-ocean-100 hover:bg-ocean-800 hover:text-white transition-colors"
            >
              <BookOpen size={18} />
              WHO Medical Manual
            </a>
            <button
              onClick={handleShare}
              className="w-full flex items-center gap-3 px-5 py-3 text-sm font-medium text-ocean-100 hover:bg-ocean-800 hover:text-white transition-colors text-left"
            >
              <Share2 size={18} />
              Share Vessel Ops AI
            </button>
          </div>

          <div>
            <p className="px-5 text-[10px] font-bold text-ocean-400 uppercase tracking-widest mb-2">System</p>
            {[
              { href: "/settings", label: "Settings", icon: Settings },
            ].map(({ href, label, icon: Icon }) => {
              const active = path.startsWith(href);
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
          </div>
        </nav>

        <div className="px-5 py-4 border-t border-ocean-800">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-lg bg-ocean-800 flex items-center justify-center text-ocean-400">
              <Anchor size={16} />
            </div>
            <div>
              <p className="text-[10px] font-bold text-ocean-500 uppercase tracking-widest leading-none mb-1">Status</p>
              <p className="text-xs font-bold text-green-400">Vessel Online</p>
            </div>
          </div>
          <div className="flex gap-3 text-[10px] text-ocean-500">
            <Link href="/terms" className="hover:text-ocean-300 transition-colors">Terms</Link>
            <span>·</span>
            <Link href="/privacy" className="hover:text-ocean-300 transition-colors">Privacy</Link>
          </div>
        </div>
      </aside>
    </>
  );
}
