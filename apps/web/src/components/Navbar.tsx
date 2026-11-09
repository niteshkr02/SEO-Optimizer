import React from "react";
import { ShieldCheck, Terminal, Users, Search } from "lucide-react";

interface NavbarProps {
  viewMode?: "AUDIT" | "ADMIN";
  onViewChange?: (mode: "AUDIT" | "ADMIN") => void;
}

export function Navbar({ viewMode = "AUDIT", onViewChange }: NavbarProps) {
  return (
    <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">SEO Optimizer</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                Phase 1 Live
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Evidence-Based Technical SEO & Code Resolution
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-medium">
          {onViewChange && (
            <div className="flex items-center p-1 rounded-xl bg-slate-900 border border-slate-800">
              <button
                onClick={() => onViewChange("AUDIT")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
                  viewMode === "AUDIT"
                    ? "bg-slate-800 text-cyan-300 font-semibold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Search className="w-3.5 h-3.5" />
                <span>Public Audit</span>
              </button>

              <button
                onClick={() => onViewChange("ADMIN")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
                  viewMode === "ADMIN"
                    ? "bg-slate-800 text-cyan-300 font-semibold shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Admin Leads</span>
              </button>
            </div>
          )}

          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>FastAPI + Next.js Engine</span>
          </div>
        </div>
      </div>
    </header>
  );
}
