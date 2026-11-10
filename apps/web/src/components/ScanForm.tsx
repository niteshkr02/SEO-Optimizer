"use client";

import React, { useState } from "react";
import { Search, Loader2, AlertCircle, ArrowRight, Globe, Layers, Compass } from "lucide-react";

interface ScanFormProps {
  onScan: (url: string) => Promise<void>;
  onCrawl?: (url: string, maxPages: number, maxDepth: number) => Promise<void>;
  isLoading: boolean;
}

export function ScanForm({ onScan, onCrawl, isLoading }: ScanFormProps) {
  const [mode, setMode] = useState<"SINGLE" | "MULTI">("SINGLE");
  const [urlInput, setUrlInput] = useState("");
  const [maxPages, setMaxPages] = useState<number>(10);
  const [maxDepth, setMaxDepth] = useState<number>(2);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmed = urlInput.trim();
    if (!trimmed) {
      setValidationError("Please enter a website URL to audit.");
      return;
    }

    let parsedUrl: URL;
    try {
      parsedUrl = new URL(trimmed);
    } catch {
      setValidationError("Invalid URL format. Please include protocol, e.g. https://example.com");
      return;
    }

    if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
      setValidationError("Only HTTP and HTTPS URLs are supported for scanning.");
      return;
    }

    if (!parsedUrl.hostname.includes(".")) {
      setValidationError("Please provide a fully qualified domain name (e.g. example.com).");
      return;
    }

    if (mode === "MULTI" && onCrawl) {
      await onCrawl(trimmed, maxPages, maxDepth);
    } else {
      await onScan(trimmed);
    }
  };

  const handleQuickFill = (demoUrl: string) => {
    setUrlInput(demoUrl);
    setValidationError(null);
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-4">
      {/* Mode Switcher */}
      {onCrawl && (
        <div className="flex justify-center">
          <div className="inline-flex items-center p-1 rounded-2xl bg-slate-900 border border-slate-800 text-xs font-semibold shadow-inner">
            <button
              type="button"
              onClick={() => setMode("SINGLE")}
              disabled={isLoading}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-xl transition ${
                mode === "SINGLE"
                  ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Single-Page Scan</span>
            </button>
            <button
              type="button"
              onClick={() => setMode("MULTI")}
              disabled={isLoading}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-xl transition ${
                mode === "MULTI"
                  ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-md"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Multi-Page Crawl (Phase 2)</span>
            </button>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative flex flex-col sm:flex-row items-stretch gap-2 bg-slate-900/90 p-2 rounded-2xl border border-slate-800 shadow-2xl focus-within:border-cyan-500/80 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all">
          <div className="relative flex-1 flex items-center">
            <div className="absolute left-4 pointer-events-none text-slate-500">
              <Globe className="w-5 h-5" />
            </div>
            <input
              type="text"
              value={urlInput}
              onChange={(e) => {
                setUrlInput(e.target.value);
                if (validationError) setValidationError(null);
              }}
              placeholder={mode === "MULTI" ? "https://yourwebsite.com (Seed Root)" : "https://yourwebsite.com/landing-page"}
              disabled={isLoading}
              className="w-full pl-12 pr-4 py-3 bg-transparent text-slate-100 placeholder-slate-500 text-sm sm:text-base focus:outline-none disabled:opacity-50"
              aria-label="Website URL to audit"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-sm sm:text-base shadow-lg shadow-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition shrink-0"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Auditing...</span>
              </>
            ) : (
              <>
                <span>{mode === "MULTI" ? "Run Multi-Page Crawl" : "Run Free Scan"}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

        {/* Crawl Settings Options Drawer */}
        {mode === "MULTI" && (
          <div className="flex flex-wrap items-center justify-between gap-4 p-3 bg-slate-900/60 rounded-xl border border-slate-800/80 text-xs text-slate-300">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 font-medium">
                <span className="text-slate-400">Page Ceiling:</span>
                <select
                  value={maxPages}
                  onChange={(e) => setMaxPages(parseInt(e.target.value, 10))}
                  disabled={isLoading}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-cyan-400 font-mono focus:outline-none"
                >
                  <option value={5}>5 pages</option>
                  <option value={10}>10 pages</option>
                  <option value={25}>25 pages</option>
                  <option value={50}>50 pages</option>
                </select>
              </label>

              <label className="flex items-center gap-2 font-medium">
                <span className="text-slate-400">Max Depth:</span>
                <select
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(parseInt(e.target.value, 10))}
                  disabled={isLoading}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-purple-400 font-mono focus:outline-none"
                >
                  <option value={1}>1 (Seed only)</option>
                  <option value={2}>2 (Seed + Direct Links)</option>
                  <option value={3}>3 (Seed + 2 Hops)</option>
                </select>
              </label>
            </div>

            <span className="text-[11px] text-slate-400">
              Same-origin boundary enforced with RFC 9309 robots.txt compliance
            </span>
          </div>
        )}

        {validationError && (
          <div className="flex items-center gap-2 text-rose-400 text-xs sm:text-sm bg-rose-950/40 border border-rose-900/50 px-4 py-2.5 rounded-xl">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{validationError}</span>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 px-2 gap-2">
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Try sample:</span>
            <button
              type="button"
              onClick={() => handleQuickFill("https://example.com")}
              className="text-cyan-400 hover:underline hover:text-cyan-300 transition"
            >
              https://example.com
            </button>
            <span className="text-slate-600">•</span>
            <button
              type="button"
              onClick={() => handleQuickFill("https://wikipedia.org")}
              className="text-cyan-400 hover:underline hover:text-cyan-300 transition"
            >
              https://wikipedia.org
            </button>
          </div>
          <span className="text-slate-500">Protected by Zero-Trust SSRF Guard</span>
        </div>
      </form>
    </div>
  );
}

