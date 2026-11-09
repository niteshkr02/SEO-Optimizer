"use client";

import React, { useState } from "react";
import { Search, Loader2, AlertCircle, ArrowRight, Globe } from "lucide-react";

interface ScanFormProps {
  onScan: (url: string) => Promise<void>;
  isLoading: boolean;
}

export function ScanForm({ onScan, isLoading }: ScanFormProps) {
  const [urlInput, setUrlInput] = useState("");
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

    await onScan(trimmed);
  };

  const handleQuickFill = (demoUrl: string) => {
    setUrlInput(demoUrl);
    setValidationError(null);
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
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
              placeholder="https://yourwebsite.com/landing-page"
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
                <span>Run Free Scan</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>

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

