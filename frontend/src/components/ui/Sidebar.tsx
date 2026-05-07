"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Anchor, Users, HeartPulse, Wrench, Settings, Sparkles, X, Gamepad2, GraduationCap } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Vessel } from "@/lib/types";
import Image from "next/image";

      <nav className="flex-1 py-4 space-y-6">
        <div>
          <p className="px-5 text-[10px] font-bold text-ocean-400 uppercase tracking-widest mb-2">Operations</p>
          {[
            { href: "/", label: "Dashboard", icon: Anchor },
            { href: "/chat", label: "Ask Gemma", icon: Sparkles },
            { href: "/crew", label: "Crew", icon: Users },
            { href: "/health", label: "Health Log", icon: HeartPulse },
            { href: "/vessel", label: "Components", icon: Wrench },
          ].map(({ href, label, icon: Icon }) => {
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
        </div>

        <div>
          <p className="px-5 text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-2">Training & Morale</p>
          {[
            { href: "/study", label: "MPIC Study", icon: GraduationCap },
            { href: "/trivia", label: "Trivia", icon: Gamepad2 },
          ].map(({ href, label, icon: Icon }) => {
            const active = path.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-5 py-3 text-sm font-medium transition-colors ${
                  active
                    ? "bg-indigo-600/50 text-white"
                    : "text-ocean-100 hover:bg-ocean-800 hover:text-white"
                }`}
              >
                <Icon size={18} className={active ? "text-indigo-300" : ""} />
                {label}
              </Link>
            );
          })}
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
      <div className="px-5 py-6 border-t border-ocean-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-ocean-800 flex items-center justify-center text-ocean-400">
            <Anchor size={16} />
          </div>
          <div>
            <p className="text-xs font-bold text-white">Sail Pal v1.2</p>
            <p className="text-xs text-ocean-400 uppercase tracking-tighter">Offline Intelligence</p>
          </div>
        </div>
      </div>
    </aside>
    </>
  );
}
