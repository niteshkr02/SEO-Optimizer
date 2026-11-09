"use client";

import React, { useState } from "react";
import { Navbar } from "../components/Navbar";
import { ScanForm } from "../components/ScanForm";
import { ScoreOverview } from "../components/ScoreOverview";
import { CategoryScores } from "../components/CategoryScores";
import { AuxiliarySummary } from "../components/AuxiliarySummary";
import { FindingsList } from "../components/FindingsList";
import { ResolutionPlanView } from "../components/ResolutionPlanView";
import { VerificationReportView } from "../components/VerificationReportView";
import { ServiceCTA } from "../components/ServiceCTA";
import { AdminLeadManagementView } from "../components/AdminLeadManagementView";
import { Footer } from "../components/Footer";
import {
  executeScan,
  generateResolutionPlan,
  compareVerification,
  exportVerificationMarkdown,
  ScanApiError,
  type AuditReportDTO,
  type ResolutionPlanDTO,
  type VerificationReportDTO,
} from "../lib/api/client";
import {
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Wrench,
  RotateCcw,
  ListFilter,
  Code,
  Loader2,
} from "lucide-react";

export default function HomePage() {
  const [viewMode, setViewMode] = useState<"AUDIT" | "ADMIN">("AUDIT");
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"FINDINGS" | "RESOLUTION" | "VERIFICATION">("FINDINGS");
  const [report, setReport] = useState<AuditReportDTO | null>(null);
  const [resolutionPlan, setResolutionPlan] = useState<ResolutionPlanDTO | null>(null);
  const [verificationReport, setVerificationReport] = useState<VerificationReportDTO | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);

  const handleScan = async (url: string) => {
    setIsLoading(true);
    setError(null);
    setResolutionPlan(null);
    setVerificationReport(null);
    setActiveTab("FINDINGS");

    try {
      const data = await executeScan(url);
      setReport(data);

      // Pre-fetch resolution plan
      try {
        const plan = await generateResolutionPlan(data);
        setResolutionPlan(plan);
      } catch {
        // Non-blocking
      }
    } catch (err: unknown) {
      if (err instanceof ScanApiError) {
        setError({
          code: err.code,
          message: err.message,
        });
      } else {
        setError({
          code: "UNEXPECTED_ERROR",
          message: err instanceof Error ? err.message : "An unexpected error occurred during the scan.",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunVerification = async () => {
    if (!report) return;
    setIsVerifying(true);
    setError(null);

    try {
      // Re-scan target URL to get fresh post-change snapshot
      const postScan = await executeScan(report.finalUrl || report.targetUrl);

      // Compare baseline with post-change
      const verReport = await compareVerification(report, postScan);
      setVerificationReport(verReport);
      setActiveTab("VERIFICATION");
    } catch (err: unknown) {
      if (err instanceof ScanApiError) {
        setError({ code: err.code, message: err.message });
      } else {
        setError({
          code: "VERIFICATION_FAILED",
          message: err instanceof Error ? err.message : "Failed to run verification comparison.",
        });
      }
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
      <Navbar viewMode={viewMode} onViewChange={setViewMode} />

      <main className="flex-1 pb-20">
        {viewMode === "ADMIN" ? (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
            <AdminLeadManagementView />
          </div>
        ) : (
          <>
            {/* Hero Section */}
            <section className="relative pt-12 pb-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center space-y-6">
          <div className="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80">
            <div className="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-cyan-500/20 to-blue-600/20 opacity-30 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem]" />
          </div>

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400 text-xs font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Deterministic • Zero-Trust • 20 Core SEO Rules</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-tight">
            Evidence-Based Technical SEO Diagnosis & Resolution
          </h1>

          <p className="text-sm sm:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Stop guessing why your site underperforms in organic search. Audit your landing page against 20 deterministic rules, inspect verifiable code evidence, and plan exact code fixes.
          </p>

          <div className="pt-4">
            <ScanForm onScan={handleScan} isLoading={isLoading} />
          </div>
        </section>

        {/* Dynamic Scan Content Area */}
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          {/* Error Banner */}
          {error && (
            <div className="bg-rose-950/40 border border-rose-900/60 rounded-3xl p-6 sm:p-8 flex items-start gap-4 text-rose-200 shadow-xl max-w-3xl mx-auto">
              <AlertCircle className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-base text-rose-100">
                    Scan Request Blocked or Failed
                  </h3>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-rose-900/60 text-rose-300">
                    {error.code}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-rose-200/90 leading-relaxed">
                  {error.message}
                </p>
                {error.code === "SSRF_VIOLATION" && (
                  <p className="text-xs text-rose-300/80 bg-rose-900/30 p-2.5 rounded-xl border border-rose-900/50">
                    <strong>Zero-Trust SSRF Defense:</strong> Private IP ranges, cloud metadata addresses (169.254.169.254), internal hostnames, and localhost are strictly prohibited from public scanning.
                  </p>
                )}
                {error.code === "NETWORK_ERROR" && (
                  <p className="text-xs text-rose-300/80 bg-rose-900/30 p-2.5 rounded-xl border border-rose-900/50">
                    <strong>Backend Connection Notice:</strong> Ensure the FastAPI server is running on <code className="text-cyan-300 font-mono">http://localhost:8000</code>.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-12 text-center space-y-4 max-w-xl mx-auto animate-pulse">
              <div className="w-12 h-12 rounded-full border-4 border-cyan-500 border-t-transparent animate-spin mx-auto" />
              <h3 className="text-lg font-bold text-slate-100">
                Auditing Target Webpage
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Executing zero-trust HTTP transport, validating redirect hops, discovering robots.txt and sitemaps, and evaluating 20 deterministic rules...
              </p>
            </div>
          )}

          {/* Audit Results View with Tabs */}
          {report && !isLoading && (
            <div className="space-y-8">
              {/* Score Overview Banner */}
              <ScoreOverview report={report} />

              {/* Navigation View Tabs */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-2 bg-slate-900/80 rounded-2xl border border-slate-800">
                <div className="flex items-center gap-1 w-full sm:w-auto">
                  <button
                    onClick={() => setActiveTab("FINDINGS")}
                    className={`flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition ${
                      activeTab === "FINDINGS"
                        ? "bg-slate-800 text-white shadow-md border border-slate-700"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <ListFilter className="w-4 h-4 text-cyan-400" />
                    <span>Audit Findings ({report.findings?.length ?? 0})</span>
                  </button>

                  <button
                    onClick={() => setActiveTab("RESOLUTION")}
                    className={`flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition ${
                      activeTab === "RESOLUTION"
                        ? "bg-slate-800 text-white shadow-md border border-slate-700"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <Wrench className="w-4 h-4 text-amber-400" />
                    <span>Resolution Plan ({resolutionPlan?.totalIssues ?? 0})</span>
                  </button>

                  {verificationReport && (
                    <button
                      onClick={() => setActiveTab("VERIFICATION")}
                      className={`flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition ${
                        activeTab === "VERIFICATION"
                          ? "bg-slate-800 text-white shadow-md border border-slate-700"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <RotateCcw className="w-4 h-4 text-emerald-400" />
                      <span>Verification (E33)</span>
                    </button>
                  )}
                </div>

                {/* Post-Deployment Re-Verification Button */}
                <button
                  onClick={handleRunVerification}
                  disabled={isVerifying}
                  className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 disabled:opacity-50 transition"
                >
                  {isVerifying ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Re-Crawling & Verifying...</span>
                    </>
                  ) : (
                    <>
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Re-Scan & Verify Fixes</span>
                    </>
                  )}
                </button>
              </div>

              {/* Tab 1: Findings Explorer */}
              {activeTab === "FINDINGS" && (
                <div className="space-y-10">
                  <AuxiliarySummary
                    robotsSummary={report.robotsSummary}
                    sitemapSummary={report.sitemapSummary}
                  />

                  <CategoryScores
                    categoryScores={report.categoryScores}
                    categoryAvailability={report.categoryAvailability}
                  />

                  <FindingsList findings={report.findings} />
                </div>
              )}

              {/* Tab 2: Resolution Plan */}
              {activeTab === "RESOLUTION" && (
                <div>
                  {resolutionPlan ? (
                    <ResolutionPlanView plan={resolutionPlan} />
                  ) : (
                    <div className="p-8 text-center text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
                      Generating resolution plan...
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Verification Report */}
              {activeTab === "VERIFICATION" && verificationReport && (
                <VerificationReportView
                  report={verificationReport}
                  onExportMarkdown={() => exportVerificationMarkdown(verificationReport)}
                />
              )}

              {/* Service CTA */}
              <ServiceCTA
                targetUrl={report.targetUrl}
                scanToken={report.scanToken}
              />
            </div>
          )}

          {/* Initial Idle Information Grid */}
          {!report && !isLoading && !error && (
            <div className="space-y-8 pt-4">
              <div className="text-center space-y-2">
                <h3 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-200">
                  How SEO Optimizer Operates Differently
                </h3>
                <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
                  Built on rigorous mathematical provenance, zero-trust network boundaries, and exact code resolution.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-6 rounded-3xl bg-slate-900/50 border border-slate-800/80 space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-950 border border-cyan-800/60 flex items-center justify-center text-cyan-400">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <h4 className="font-semibold text-base text-slate-100">
                    Deterministic 5-State Findings
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Every check evaluates to <code className="text-cyan-300">PASS</code>, <code className="text-rose-300">FAIL</code>, <code className="text-amber-300">UNKNOWN</code>, <code className="text-purple-300">NOT_APPLICABLE</code>, or <code className="text-slate-400">NOT_TESTED</code>. We never fabricate missing data.
                  </p>
                </div>

                <div className="p-6 rounded-3xl bg-slate-900/50 border border-slate-800/80 space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-950 border border-blue-800/60 flex items-center justify-center text-blue-400">
                    <Code className="w-5 h-5" />
                  </div>
                  <h4 className="font-semibold text-base text-slate-100">
                    Verifiable Code Evidence & Diffs
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Every finding includes typed evidence with observed values, DOM selectors, and reversible Git diff proposals requiring human approval before merge.
                  </p>
                </div>

                <div className="p-6 rounded-3xl bg-slate-900/50 border border-slate-800/80 space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-teal-950 border border-teal-800/60 flex items-center justify-center text-teal-400">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <h4 className="font-semibold text-base text-slate-100">
                    Model E33 Verification Engine
                  </h4>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Compare baseline audits with post-deployment re-scans. Track Issue Resolution Rate (IRR%), score deltas, and detect regressions before they impact organic search.
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>
        </>
      )}
      </main>

      <Footer />
    </div>
  );
}
