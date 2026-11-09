import React from "react";
import { ShieldCheck, Cpu, Code2 } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-900 bg-slate-950/80 text-slate-500 text-xs py-12 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-400">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span className="font-semibold text-slate-300">SEO Optimizer Platform</span>
            <span>—</span>
            <span>Evidence-Based Technical SEO & Resolution</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400 font-mono text-[11px]">
            <div className="flex items-center gap-1">
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>FastAPI Backend (Python 3.12+)</span>
            </div>
            <span>•</span>
            <div className="flex items-center gap-1">
              <Code2 className="w-3.5 h-3.5 text-blue-400" />
              <span>Next.js App Router (TypeScript)</span>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-slate-900/80 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px]">
          <p>© {new Date().getFullYear()} SEO Optimizer. All rights reserved. Zero-trust deterministic engine.</p>
          <p className="text-slate-600">
            All 36 mathematical models documented in Architecture Catalog E1–E36.
          </p>
        </div>
      </div>
    </footer>
  );
}

