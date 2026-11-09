import React from "react";
import type { RobotsTxtSummaryDTO, SitemapSummaryDTO } from "../lib/api/client";
import { formatScore } from "../lib/utils";
import { FileText, Map, CheckCircle2, XCircle, AlertCircle, HelpCircle } from "lucide-react";

interface AuxiliarySummaryProps {
  robotsSummary?: RobotsTxtSummaryDTO | null;
  sitemapSummary?: SitemapSummaryDTO | null;
}

export function AuxiliarySummary({
  robotsSummary,
  sitemapSummary,
}: AuxiliarySummaryProps) {
  if (!robotsSummary && !sitemapSummary) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Robots.txt Discovery Card */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
            <FileText className="w-4 h-4 text-cyan-400" />
            <span>Robots.txt Discovery</span>
          </div>
          {robotsSummary?.isPresent ? (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3" />
              Found (HTTP {robotsSummary.statusCode})
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-400 bg-rose-950/60 border border-rose-800/60 px-2 py-0.5 rounded-full">
              <XCircle className="w-3 h-3" />
              Not Found ({robotsSummary?.statusCode ? `HTTP ${robotsSummary.statusCode}` : "Unavailable"})
            </span>
          )}
        </div>

        <div className="text-xs space-y-2 text-slate-400">
          <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
            <span>Target Path Crawlability:</span>
            <span className="font-semibold text-slate-200">
              {robotsSummary?.isTargetAllowed === true && "Allowed (Permitted to crawl)"}
              {robotsSummary?.isTargetAllowed === false && "Blocked (Disallowed in robots.txt)"}
              {robotsSummary?.isTargetAllowed === null && "Default (No directives apply)"}
            </span>
          </div>

          <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
            <span>Sitemaps Declared in robots.txt:</span>
            <span className="font-mono text-slate-200">
              {robotsSummary?.sitemapUrls?.length ?? 0} found
            </span>
          </div>


          {robotsSummary?.errorReason && (
            <div className="text-[11px] text-amber-400/90 bg-amber-950/30 p-2 rounded-lg border border-amber-900/40">
              {robotsSummary.errorReason}
            </div>
          )}
        </div>
      </div>

      {/* XML Sitemap Discovery Card */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-200 font-semibold text-sm">
            <Map className="w-4 h-4 text-blue-400" />
            <span>XML Sitemap Discovery & Model E12</span>
          </div>
          {sitemapSummary?.isSitemapFound ? (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3" />
              Discovered
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-400 bg-amber-950/60 border border-amber-800/60 px-2 py-0.5 rounded-full">
              <AlertCircle className="w-3 h-3" />
              Not Found
            </span>
          )}
        </div>

        <div className="text-xs space-y-2 text-slate-400">
          <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
            <span>Discovery Source:</span>
            <span className="font-mono text-slate-200">
              {sitemapSummary?.sitemapSource ?? "NONE"}
            </span>
          </div>

          <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
            <span>Sampled URLs Evaluated:</span>
            <span className="font-mono text-slate-200">
              {sitemapSummary?.totalUrlsSampled ?? 0} URLs
            </span>
          </div>

          <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
            <span>Model E12 Sitemap URL Health:</span>
            <span className="font-semibold text-slate-200">
              {sitemapSummary?.healthScore !== null && sitemapSummary?.healthScore !== undefined
                ? `${formatScore(sitemapSummary.healthScore)}%`
                : "Unavailable (No URLs sampled)"}
            </span>
          </div>

          {sitemapSummary?.errorReason && (
            <div className="text-[11px] text-amber-400/90 bg-amber-950/30 p-2 rounded-lg border border-amber-900/40">
              {sitemapSummary.errorReason}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
