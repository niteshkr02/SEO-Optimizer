"use client";

import React from "react";
import { Loader2, StopCircle, Globe, Layers, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import type { CrawlJobDTO } from "../lib/api/client";

interface CrawlProgressViewProps {
  job: CrawlJobDTO;
  onCancel: () => Promise<void>;
  isCancelling: boolean;
}

export function CrawlProgressView({ job, onCancel, isCancelling }: CrawlProgressViewProps) {
  const isRunning = job.status === "RUNNING" || job.status === "QUEUED";
  const isFinished = job.status === "COMPLETED" || job.status === "PARTIAL";

  const getStatusBadge = () => {
    switch (job.status) {
      case "RUNNING":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800 animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            CRAWLING SITE
          </span>
        );
      case "QUEUED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <Clock className="w-3.5 h-3.5" />
            QUEUED
          </span>
        );
      case "COMPLETED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5" />
            COMPLETED
          </span>
        );
      case "PARTIAL":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5" />
            CEILING REACHED (PARTIAL)
          </span>
        );
      case "CANCELLED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            <StopCircle className="w-3.5 h-3.5" />
            CANCELLED
          </span>
        );
      case "FAILED":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800">
            <AlertTriangle className="w-3.5 h-3.5" />
            FAILED
          </span>
        );
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-6 shadow-2xl max-w-4xl mx-auto backdrop-blur">
      {/* Header with Title and Cancel button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h3 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <Globe className="w-5 h-5 text-cyan-400" />
              Website Crawl in Progress
            </h3>
            {getStatusBadge()}
          </div>
          <p className="text-xs sm:text-sm text-slate-400 font-mono break-all">
            {job.seedUrl}
          </p>
        </div>

        {isRunning && (
          <button
            type="button"
            onClick={onCancel}
            disabled={isCancelling}
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/80 text-xs sm:text-sm font-semibold transition disabled:opacity-50"
          >
            {isCancelling ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Cancelling...</span>
              </>
            ) : (
              <>
                <StopCircle className="w-4 h-4" />
                <span>Stop Crawl</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs font-semibold text-slate-300">
          <span>Overall Crawl Progress</span>
          <span className="font-mono text-cyan-400">{job.progressPercentage.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-slate-950 rounded-full h-3 overflow-hidden border border-slate-800">
          <div
            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.min(100, Math.max(0, job.progressPercentage))}%` }}
          />
        </div>
      </div>

      {/* Metric Counters Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-2">
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 text-center space-y-1">
          <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Discovered</span>
          <span className="text-xl sm:text-2xl font-extrabold text-cyan-400 font-mono">
            {job.pagesDiscovered}
          </span>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 text-center space-y-1">
          <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Audited</span>
          <span className="text-xl sm:text-2xl font-extrabold text-emerald-400 font-mono">
            {job.pagesCrawled}
          </span>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 text-center space-y-1">
          <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Pending</span>
          <span className="text-xl sm:text-2xl font-extrabold text-amber-400 font-mono">
            {job.pagesRemaining}
          </span>
        </div>

        <div className="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 text-center space-y-1">
          <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Max Depth</span>
          <span className="text-xl sm:text-2xl font-extrabold text-purple-400 font-mono">
            {job.currentDepth} <span className="text-xs text-slate-500">/ {job.maxDepth}</span>
          </span>
        </div>

        <div className="col-span-2 sm:col-span-1 bg-slate-950/60 border border-slate-800/80 rounded-2xl p-4 text-center space-y-1">
          <span className="text-[11px] font-medium text-slate-400 block uppercase tracking-wider">Failed</span>
          <span className={`text-xl sm:text-2xl font-extrabold font-mono ${job.pagesFailed > 0 ? "text-rose-400" : "text-slate-400"}`}>
            {job.pagesFailed}
          </span>
        </div>
      </div>

      {/* Realtime Status Subtext */}
      {isRunning && (
        <div className="flex items-center justify-center gap-2 text-xs text-slate-400 pt-1">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
          <span>Polite BFS crawl in progress (RFC 9309 compliance & rate limiting enforced)...</span>
        </div>
      )}
    </div>
  );
}
