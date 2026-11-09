import React from "react";
import { formatScore, getScoreColorClass } from "../lib/utils";
import type { AuditReportDTO } from "../lib/api/client";
import {
  Activity,
  CheckCircle2,
  Clock,
  ExternalLink,
  Layers,
  AlertTriangle,
  Info,
} from "lucide-react";

interface ScoreOverviewProps {
  report: AuditReportDTO;
}

export function ScoreOverview({ report }: ScoreOverviewProps) {
  const overallColors = getScoreColorClass(report.overallScore);
  const completenessColors = getScoreColorClass(report.completenessScore);

  const formattedDate = report.createdAt
    ? new Date(report.createdAt).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Just now";


  return (
    <div className="space-y-6">
      {/* Prominent Single-Page Audit Disclaimer Banner */}
      <div className="bg-amber-950/30 border border-amber-800/40 rounded-2xl p-4 sm:p-5 flex items-start gap-3.5 text-amber-200">
        <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs sm:text-sm space-y-1">
          <p className="font-semibold text-amber-300">
            Scope Notice: Single-Page Technical Audit
          </p>
          <p className="text-amber-200/80 leading-relaxed">
            This scan audits the specific landing URL submitted along with origin-level root resources (<code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-300">/robots.txt</code> and discovered XML sitemaps). It is intentionally <strong>not</strong> a full-domain crawl.
          </p>
        </div>
      </div>

      {/* Main Score Hero Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur shadow-xl grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
        {/* Overall SEO Health Score (Model E3) */}
        <div className="flex flex-col items-center justify-center p-6 rounded-2xl bg-slate-950/60 border border-slate-800/80 text-center">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Overall SEO Health Score
          </span>
          <div
            className={`text-6xl sm:text-7xl font-extrabold tracking-tight ${overallColors.text}`}
          >
            {formatScore(report.overallScore)}
            <span className="text-2xl font-normal text-slate-600">/100</span>
          </div>
          <p className="text-xs text-slate-400 mt-3">
            {report.overallScore !== null
              ? "Deterministic normalized weighted composite (Model E3)"
              : "Insufficient category data to calculate overall score"}
          </p>
        </div>

        {/* Report Completeness (Model E5) */}
        <div className="flex flex-col items-center justify-center p-6 rounded-2xl bg-slate-950/60 border border-slate-800/80 text-center">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Report Completeness Index
          </span>
          <div
            className={`text-6xl sm:text-7xl font-extrabold tracking-tight ${completenessColors.text}`}
          >
            {formatScore(report.completenessScore)}
            <span className="text-2xl font-normal text-slate-600">%</span>
          </div>
          <p className="text-xs text-slate-400 mt-3">
            {report.completenessScore !== null
              ? "Percentage of applicable checks definitively resolved (Model E5)"
              : "No applicable checks evaluated"}
          </p>
        </div>

        {/* Scan Details & SPA Indicator */}
        <div className="flex flex-col justify-center space-y-3 p-4 text-xs text-slate-300 bg-slate-950/40 rounded-2xl border border-slate-800/60">
          <div>
            <span className="text-slate-500 font-medium">Landing URL:</span>
            <div className="flex items-center gap-1.5 mt-0.5 font-mono text-slate-200 truncate">
              <span className="truncate">{report.finalUrl}</span>
              <a
                href={report.finalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-400 hover:text-cyan-300 shrink-0"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-slate-800/80 pt-2">
            <span className="text-slate-500">HTTP Status:</span>
            <span className="font-mono font-bold text-emerald-400">
              {report.statusCode} OK
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Scan Timestamp:</span>
            <span className="font-mono text-slate-400">{formattedDate}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Scan Token:</span>
            <span className="font-mono text-[10px] text-slate-400 truncate max-w-[140px]">
              {report.scanToken}
            </span>
          </div>

          {report.isSpaDetected && (
            <div className="border-t border-amber-800/40 pt-2 flex items-center gap-2 text-amber-300 bg-amber-950/40 p-2 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>SPA Detected:</strong> Static DOM evaluated; client JS not executed.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
