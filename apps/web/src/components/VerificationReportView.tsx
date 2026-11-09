"use client";

import React, { useState } from "react";
import type { VerificationReportDTO, VerificationTransition } from "../lib/api/client";
import { formatScore } from "../lib/utils";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Download,
  Copy,
  Check,
  ArrowRight,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

interface VerificationReportViewProps {
  report: VerificationReportDTO;
  onExportMarkdown?: () => Promise<string>;
}

export function VerificationReportView({
  report,
  onExportMarkdown,
}: VerificationReportViewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyMarkdown = async () => {
    if (onExportMarkdown) {
      try {
        const md = await onExportMarkdown();
        await navigator.clipboard.writeText(md);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        // fallback
      }
    }
  };

  const irrStr =
    report.issueResolutionRate !== null && report.issueResolutionRate !== undefined
      ? `${formatScore(report.issueResolutionRate)}%`
      : "N/A (0 attempted)";

  return (
    <div className="space-y-6">
      {/* Verification Header */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                <ShieldCheck className="w-5 h-5" />
              </span>
              <h3 className="text-xl font-bold tracking-tight text-white">
                Post-Deployment Verification Report
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic before/after audit comparison backing Model E33 Issue Resolution Rate.
            </p>
          </div>

          {onExportMarkdown && (
            <button
              onClick={handleCopyMarkdown}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span>Copied Markdown!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-slate-400" />
                  <span>Copy Markdown Report</span>
                </>
              )}
            </button>
          )}
        </div>

        {/* Verification Metrics Grid (Model E33) */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Issue Resolution Rate
            </span>
            <span className="text-3xl sm:text-4xl font-extrabold text-emerald-400">
              {irrStr}
            </span>
            <span className="text-[10px] text-slate-500 block">
              Model E33 Metric
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Resolved Issues
            </span>
            <span className="text-3xl sm:text-4xl font-extrabold text-slate-100">
              {report.resolvedCount}
              <span className="text-sm font-normal text-slate-500">
                /{report.totalAttempted}
              </span>
            </span>
            <span className="text-[10px] text-slate-500 block">
              FAIL → PASS
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Regressions
            </span>
            <span
              className={`text-3xl sm:text-4xl font-extrabold ${
                report.regressedCount > 0 ? "text-rose-400" : "text-slate-400"
              }`}
            >
              {report.regressedCount}
            </span>
            <span className="text-[10px] text-slate-500 block">
              PASS → FAIL
            </span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
              Score Delta
            </span>
            <div className="flex items-center justify-center gap-1">
              {report.overallScoreDelta.delta && report.overallScoreDelta.delta > 0 ? (
                <TrendingUp className="w-5 h-5 text-emerald-400" />
              ) : (
                <TrendingDown className="w-5 h-5 text-slate-500" />
              )}
              <span className="text-3xl sm:text-4xl font-extrabold text-cyan-400">
                {report.overallScoreDelta.delta
                  ? `${report.overallScoreDelta.delta > 0 ? "+" : ""}${report.overallScoreDelta.delta.toFixed(1)}`
                  : "0.0"}
              </span>
            </div>
            <span className="text-[10px] text-slate-500 block">
              Overall Health Shift
            </span>
          </div>
        </div>
      </div>

      {/* Itemized Comparison Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-6 overflow-hidden">
        <h4 className="font-bold text-sm text-slate-200 mb-4">
          Itemized Finding Transitions
        </h4>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                <th className="py-2.5 px-3">Rule ID</th>
                <th className="py-2.5 px-3">Baseline</th>
                <th className="py-2.5 px-3">Post-Change</th>
                <th className="py-2.5 px-3">Transition</th>
                <th className="py-2.5 px-3">Attempted?</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {(report.findingComparisons ?? []).map((comp) => (
                <tr key={comp.ruleId} className="hover:bg-slate-800/30">

                  <td className="py-3 px-3 font-mono text-slate-300">
                    <div>{comp.ruleId}</div>
                    <div className="text-[10px] text-slate-500">{comp.title}</div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-mono text-slate-400">
                      {comp.previousState}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="font-mono text-slate-200">
                      {comp.currentState}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <TransitionBadge transition={comp.transition} />
                  </td>
                  <td className="py-3 px-3">
                    {comp.wasAttempted ? (
                      <span className="text-cyan-400 font-semibold">Yes</span>
                    ) : (
                      <span className="text-slate-500">No</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function TransitionBadge({ transition }: { transition: VerificationTransition }) {
  switch (transition) {
    case "RESOLVED":
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/80">
          <CheckCircle2 className="w-3 h-3" />
          RESOLVED
        </span>
      );
    case "UNRESOLVED":
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-950 text-rose-400 border border-rose-800/80">
          <XCircle className="w-3 h-3" />
          UNRESOLVED
        </span>
      );
    case "REGRESSED":
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full bg-orange-950 text-orange-400 border border-orange-800/80">
          <AlertTriangle className="w-3 h-3" />
          REGRESSED
        </span>
      );
    case "PERSISTENT_PASS":
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
          PERSISTENT PASS
        </span>
      );
    case "UNKNOWN":
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-950 text-amber-400 border border-amber-800">
          UNKNOWN
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          NOT RECHECKED
        </span>
      );
  }
}
