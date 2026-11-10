"use client";

import React, { useState } from "react";
import {
  Globe,
  Layers,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Search,
  Eye,
  X,
  FileText,
  ShieldCheck,
  Clock,
} from "lucide-react";
import type {
  SiteAggregateReportDTO,
  SiteIssueSummaryDTO,
  CrawlPageDTO,
  CrawlPageDetailDTO,
} from "../lib/api/client";
import { getCrawlPageDetail } from "../lib/api/client";
import { FindingsList } from "./FindingsList";

interface MultiPageReportViewProps {
  report: SiteAggregateReportDTO;
  jobId: string;
}

export function MultiPageReportView({ report, jobId }: MultiPageReportViewProps) {
  const [activeSection, setActiveSection] = useState<"ISSUES" | "PAGES">("ISSUES");
  const [expandedIssueRuleId, setExpandedIssueRuleId] = useState<string | null>(null);
  const [inspectingPage, setInspectingPage] = useState<CrawlPageDetailDTO | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [selectedDepth, setSelectedDepth] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");

  const handleInspectPage = async (page: CrawlPageDTO) => {
    setIsLoadingDetail(true);
    try {
      const detail = await getCrawlPageDetail(jobId, page.pageId);
      setInspectingPage(detail);
    } catch {
      // Non-blocking
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const pages = report.crawledPages || [];
  const filteredPages = pages.filter((p) => {
    if (selectedDepth !== "ALL" && p.depth !== parseInt(selectedDepth, 10)) {
      return false;
    }
    if (selectedStatus !== "ALL" && p.status !== selectedStatus) {
      return false;
    }
    return true;
  });

  const getScoreBadgeColor = (score: number | null | undefined) => {
    if (score === null || score === undefined) return "text-slate-400 bg-slate-800 border-slate-700";
    if (score >= 85) return "text-emerald-300 bg-emerald-950/80 border-emerald-800";
    if (score >= 65) return "text-amber-300 bg-amber-950/80 border-amber-800";
    return "text-rose-300 bg-rose-950/80 border-rose-800";
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">CRITICAL</span>;
      case "HIGH":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-950 text-orange-300 border border-orange-800">HIGH</span>;
      case "MEDIUM":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800">MEDIUM</span>;
      case "LOW":
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">LOW</span>;
      case "INFO":
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">INFO</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CRAWLED":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">CRAWLED</span>;
      case "DISALLOWED":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">DISALLOWED</span>;
      case "FAILED":
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950 text-rose-300 border border-rose-800">FAILED</span>;
      case "PENDING":
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">{status}</span>;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Banner: Site-wide Health Score Overview */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-400 text-xs font-semibold">
              <Globe className="w-3.5 h-3.5" />
              <span>Multi-Page Aggregated SEO Report</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
              {report.baseDomain}
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 font-mono break-all">
              Seed: {report.seedUrl}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            {/* Site Health Score Dial */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 sm:p-5 text-center min-w-[140px] shadow-lg">
              <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
                Site Health (S_site)
              </span>
              <span className={`text-3xl sm:text-4xl font-black font-mono block mt-1 ${
                report.overallScore !== null && report.overallScore !== undefined
                  ? report.overallScore >= 85 ? "text-emerald-400" : report.overallScore >= 65 ? "text-amber-400" : "text-rose-400"
                  : "text-slate-500"
              }`}>
                {report.overallScore !== null && report.overallScore !== undefined
                  ? report.overallScore.toFixed(1)
                  : "N/A"}
              </span>
              <span className="text-[10px] text-slate-500 block">out of 100</span>
            </div>

            {/* Completeness Score */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 sm:p-5 text-center min-w-[130px] shadow-lg">
              <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
                Completeness (C_site)
              </span>
              <span className="text-3xl sm:text-4xl font-black font-mono text-cyan-400 block mt-1">
                {report.completenessScore !== null && report.completenessScore !== undefined
                  ? `${report.completenessScore.toFixed(1)}%`
                  : "N/A"}
              </span>
              <span className="text-[10px] text-slate-500 block">inspected evidence</span>
            </div>

            {/* Scope Summary */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl p-4 sm:p-5 space-y-2 min-w-[160px] text-xs shadow-lg">
              <div className="flex justify-between items-center text-slate-300">
                <span>Audited Pages:</span>
                <span className="font-mono font-bold text-white">{report.totalPagesAnalyzed}</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span>Total Failures:</span>
                <span className="font-mono font-bold text-rose-400">{report.totalIssuesIdentified}</span>
              </div>
              <div className="flex justify-between items-center text-slate-300">
                <span>Unique Issues:</span>
                <span className="font-mono font-bold text-amber-400">{report.uniqueIssues?.length || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Category Breakdown Bar */}
        {report.categoryScores && Object.keys(report.categoryScores).length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-6 mt-6 border-t border-slate-800/80">
            {Object.entries(report.categoryScores).map(([cat, scoreDto]) => (
              <div key={cat} className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-3 text-center space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 block uppercase tracking-wider truncate">
                  {cat}
                </span>
                <span className={`text-lg sm:text-xl font-bold font-mono ${
                  scoreDto.score !== null && scoreDto.score !== undefined
                    ? scoreDto.score >= 85 ? "text-emerald-400" : scoreDto.score >= 65 ? "text-amber-400" : "text-rose-400"
                    : "text-slate-500"
                }`}>
                  {scoreDto.score !== null && scoreDto.score !== undefined ? `${scoreDto.score.toFixed(1)}` : "N/A"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* View Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          type="button"
          onClick={() => setActiveSection("ISSUES")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition ${
            activeSection === "ISSUES"
              ? "bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20"
              : "text-slate-400 hover:text-white hover:bg-slate-900"
          }`}
        >
          <AlertCircle className="w-4 h-4" />
          <span>Unique Site Issues ({report.uniqueIssues?.length || 0})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSection("PAGES")}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition ${
            activeSection === "PAGES"
              ? "bg-cyan-500 text-slate-950 shadow-lg shadow-cyan-500/20"
              : "text-slate-400 hover:text-white hover:bg-slate-900"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Crawled Pages ({pages.length})</span>
        </button>
      </div>

      {/* SECTION 1: Unique Issues List */}
      {activeSection === "ISSUES" && (
        <div className="space-y-4">
          <p className="text-xs text-slate-400">
            Deduplicated site-wide SEO issues sorted by severity and impact percentage. Each issue groups all affected pages to avoid diagnostic inflation.
          </p>

          {(!report.uniqueIssues || report.uniqueIssues.length === 0) ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center text-slate-400">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
              <p className="font-semibold text-slate-200">No Technical SEO Failures Found!</p>
              <p className="text-xs text-slate-400">All crawled pages complied with the 20 canonical SEO rules.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {report.uniqueIssues.map((issue) => {
                const isExpanded = expandedIssueRuleId === issue.ruleId;
                return (
                  <div
                    key={issue.ruleId}
                    className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 transition hover:border-slate-700"
                  >
                    <div
                      className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer"
                      onClick={() => setExpandedIssueRuleId(isExpanded ? null : issue.ruleId)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-1">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-cyan-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-slate-500" />
                          )}
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            {getSeverityBadge(issue.severity)}
                            <span className="text-[10px] font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-800">
                              {issue.category}
                            </span>
                            <span className="text-[10px] font-mono text-cyan-400 px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800">
                              {issue.ruleId}
                            </span>
                          </div>
                          <h4 className="text-sm sm:text-base font-bold text-white">
                            {issue.title}
                          </h4>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 text-right shrink-0">
                        <div>
                          <span className="text-xs sm:text-sm font-bold font-mono text-rose-400 block">
                            {issue.failingPagesCount} / {issue.totalPagesAudited} pages
                          </span>
                          <span className="text-[10px] text-slate-400 block font-mono">
                            {issue.impactPercentage.toFixed(1)}% site impact
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Remediation Guidance */}
                    <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 text-xs text-slate-300 space-y-1">
                      <span className="font-semibold text-cyan-400 block">Recommended Resolution:</span>
                      <p>{issue.remediationGuidance}</p>
                    </div>

                    {/* Expanded Sample Evidence and Affected URLs */}
                    {isExpanded && (
                      <div className="pt-3 border-t border-slate-800/80 space-y-3">
                        <div className="space-y-1">
                          <span className="text-xs font-semibold text-slate-300 block">
                            Sample Affected Pages:
                          </span>
                          <ul className="space-y-1">
                            {issue.sampleUrls?.map((url, idx) => (
                              <li key={idx} className="flex items-center gap-2 text-xs text-slate-400 font-mono break-all">
                                <ExternalLink className="w-3 h-3 text-cyan-400 shrink-0" />
                                <span>{url}</span>
                              </li>
                            ))}
                          </ul>
                        </div>

                        {issue.sampleEvidence && issue.sampleEvidence.length > 0 && (
                          <div className="space-y-2 pt-2">
                            <span className="text-xs font-semibold text-slate-300 block">
                              Observed Evidence Snippet:
                            </span>
                            <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 font-mono text-xs text-slate-300 space-y-2">
                              {issue.sampleEvidence.map((ev, i) => {
                                const evRecord = ev as Record<string, unknown>;
                                return (
                                  <div key={i} className="space-y-0.5 border-b border-slate-900 pb-2 last:border-b-0 last:pb-0">
                                    <div className="text-[11px] text-slate-500 break-all">{String(evRecord.url || "")}</div>
                                    <div className="text-rose-300">Observed: {String(evRecord.observedValue || "(none)")}</div>
                                    {Boolean(evRecord.expectedValue) && (
                                      <div className="text-emerald-300">Expected: {String(evRecord.expectedValue)}</div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* SECTION 2: Crawled Pages Table */}
      {activeSection === "PAGES" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
            <div className="flex flex-wrap items-center gap-3">
              <label className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
                <span>Depth:</span>
                <select
                  value={selectedDepth}
                  onChange={(e) => setSelectedDepth(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none"
                >
                  <option value="ALL">All Depths</option>
                  <option value="0">Depth 0 (Seed)</option>
                  <option value="1">Depth 1</option>
                  <option value="2">Depth 2</option>
                  <option value="3">Depth 3</option>
                </select>
              </label>

              <label className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
                <span>Status:</span>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="CRAWLED">Crawled</option>
                  <option value="DISALLOWED">Disallowed (robots.txt)</option>
                  <option value="FAILED">Failed</option>
                </select>
              </label>
            </div>

            <div className="text-xs text-slate-400">
              Showing <span className="font-bold text-white">{filteredPages.length}</span> of {pages.length} discovered pages
            </div>
          </div>

          {/* Table */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3">Page URL</th>
                    <th className="px-3 py-3">Depth</th>
                    <th className="px-3 py-3">Status</th>
                    <th className="px-3 py-3">HTTP</th>
                    <th className="px-3 py-3">Latency</th>
                    <th className="px-3 py-3">Score</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {filteredPages.map((page) => (
                    <tr key={page.pageId} className="hover:bg-slate-800/40 transition">
                      <td className="px-4 py-3 font-sans">
                        <div className="font-semibold text-white break-all max-w-md">
                          {page.title || page.url}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono break-all">
                          {page.url}
                        </div>
                      </td>
                      <td className="px-3 py-3 font-mono text-purple-400">
                        {page.depth}
                      </td>
                      <td className="px-3 py-3">
                        {getStatusBadge(page.status)}
                      </td>
                      <td className="px-3 py-3">
                        {page.httpStatus ? (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            page.httpStatus === 200 ? "bg-emerald-950 text-emerald-300" : "bg-rose-950 text-rose-300"
                          }`}>
                            {page.httpStatus}
                          </span>
                        ) : (
                          <span className="text-slate-500">-</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-slate-400">
                        {page.responseTimeMs ? `${page.responseTimeMs}ms` : "-"}
                      </td>
                      <td className="px-3 py-3 font-bold">
                        {page.overallScore !== null && page.overallScore !== undefined ? (
                          <span className={`px-2 py-0.5 rounded text-[11px] border ${getScoreBadgeColor(page.overallScore)}`}>
                            {page.overallScore.toFixed(0)}
                          </span>
                        ) : (
                          <span className="text-slate-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-sans">
                        {page.status === "CRAWLED" ? (
                          <button
                            type="button"
                            onClick={() => handleInspectPage(page)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-950 text-cyan-300 hover:bg-cyan-900 border border-cyan-800 text-xs font-semibold transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Inspect</span>
                          </button>
                        ) : (
                          <span className="text-slate-500 text-[11px] italic">No findings</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Inspect Page Detail Modal */}
      {inspectingPage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-4xl w-full p-6 sm:p-8 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <span className="text-xs text-cyan-400 font-semibold uppercase tracking-wider block">
                  Individual Page Diagnosis
                </span>
                <h3 className="text-lg sm:text-xl font-bold text-white break-all">
                  {inspectingPage.page.title || inspectingPage.page.url}
                </h3>
                <p className="text-xs text-slate-400 font-mono break-all">
                  {inspectingPage.page.url}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setInspectingPage(null)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scores Overview */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-slate-950 rounded-2xl p-3 border border-slate-800 text-center">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Health Score</span>
                <span className={`text-xl font-extrabold font-mono ${
                  inspectingPage.page.overallScore !== null && inspectingPage.page.overallScore !== undefined
                    ? inspectingPage.page.overallScore >= 85 ? "text-emerald-400" : inspectingPage.page.overallScore >= 65 ? "text-amber-400" : "text-rose-400"
                    : "text-slate-500"
                }`}>
                  {inspectingPage.page.overallScore !== null && inspectingPage.page.overallScore !== undefined
                    ? inspectingPage.page.overallScore.toFixed(1)
                    : "N/A"}
                </span>
              </div>

              <div className="bg-slate-950 rounded-2xl p-3 border border-slate-800 text-center">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Completeness</span>
                <span className="text-xl font-extrabold font-mono text-cyan-400">
                  {inspectingPage.page.completenessScore !== null && inspectingPage.page.completenessScore !== undefined
                    ? `${inspectingPage.page.completenessScore.toFixed(1)}%`
                    : "N/A"}
                </span>
              </div>

              <div className="bg-slate-950 rounded-2xl p-3 border border-slate-800 text-center">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">HTTP Status</span>
                <span className="text-xl font-extrabold font-mono text-white">
                  {inspectingPage.page.httpStatus || "-"}
                </span>
              </div>

              <div className="bg-slate-950 rounded-2xl p-3 border border-slate-800 text-center">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Response Time</span>
                <span className="text-xl font-extrabold font-mono text-slate-300">
                  {inspectingPage.page.responseTimeMs ? `${inspectingPage.page.responseTimeMs}ms` : "-"}
                </span>
              </div>
            </div>

            {/* Findings List Component */}
            <div className="pt-2">
              <h4 className="text-sm font-bold text-white mb-3">
                All 20 Canonical SEO Findings for this Page:
              </h4>
              <FindingsList findings={inspectingPage.findings} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
