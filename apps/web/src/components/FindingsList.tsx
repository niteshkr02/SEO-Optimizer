"use client";

import React, { useState } from "react";
import type { Finding, RuleCategory, RuleState, IssueSeverity } from "../lib/api/client";
import {
  CheckCircle2,
  XCircle,
  HelpCircle,
  MinusCircle,
  Slash,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Info,
  SlidersHorizontal,
  Wrench,
} from "lucide-react";

interface FindingsListProps {
  findings?: Finding[];
}

export function FindingsList({ findings = [] }: FindingsListProps) {
  const [selectedState, setSelectedState] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [expandedFindings, setExpandedFindings] = useState<Record<string, boolean>>({});

  const toggleExpand = (ruleId: string) => {
    setExpandedFindings((prev) => ({
      ...prev,
      [ruleId]: !prev[ruleId],
    }));
  };

  const filteredFindings = findings.filter((f) => {
    if (selectedState !== "ALL" && f.state !== selectedState) return false;
    if (selectedCategory !== "ALL" && f.category !== selectedCategory) return false;
    return true;
  });

  const stateCounts = findings.reduce(
    (acc, f) => {
      acc[f.state] = (acc[f.state] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6">
      {/* Header and Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h3 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>Deterministic Findings & Evidence</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
              {findings.length} Rules Audited
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Zero-trust deterministic audits with immutable evidence and data provenance.
          </p>
        </div>

        {/* State Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          <button
            onClick={() => setSelectedState("ALL")}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              selectedState === "ALL"
                ? "bg-slate-200 text-slate-900"
                : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
            }`}
          >
            All ({findings.length})
          </button>
          <button
            onClick={() => setSelectedState("FAIL")}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              selectedState === "FAIL"
                ? "bg-rose-500 text-white shadow-md shadow-rose-500/20"
                : "bg-slate-900 text-rose-400 hover:bg-slate-800 border border-rose-900/40"
            }`}
          >
            Fail ({stateCounts["FAIL"] || 0})
          </button>
          <button
            onClick={() => setSelectedState("PASS")}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              selectedState === "PASS"
                ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/20"
                : "bg-slate-900 text-emerald-400 hover:bg-slate-800 border border-emerald-900/40"
            }`}
          >
            Pass ({stateCounts["PASS"] || 0})
          </button>
          <button
            onClick={() => setSelectedState("UNKNOWN")}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              selectedState === "UNKNOWN"
                ? "bg-amber-500 text-slate-950 font-bold"
                : "bg-slate-900 text-amber-400 hover:bg-slate-800 border border-amber-900/40"
            }`}
          >
            Unknown ({stateCounts["UNKNOWN"] || 0})
          </button>
          <button
            onClick={() => setSelectedState("NOT_APPLICABLE")}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              selectedState === "NOT_APPLICABLE"
                ? "bg-purple-600 text-white"
                : "bg-slate-900 text-purple-400 hover:bg-slate-800 border border-purple-900/40"
            }`}
          >
            N/A ({stateCounts["NOT_APPLICABLE"] || 0})
          </button>
          <button
            onClick={() => setSelectedState("NOT_TESTED")}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              selectedState === "NOT_TESTED"
                ? "bg-slate-500 text-white"
                : "bg-slate-900 text-slate-400 hover:bg-slate-800 border border-slate-700"
            }`}
          >
            Not Tested ({stateCounts["NOT_TESTED"] || 0})
          </button>
        </div>
      </div>

      {/* Findings Cards List */}
      <div className="space-y-3">
        {filteredFindings.length === 0 ? (
          <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
            No findings match the selected filter criteria.
          </div>
        ) : (
          filteredFindings.map((finding) => {
            const isExpanded = !!expandedFindings[finding.ruleId];
            return (
              <div
                key={finding.ruleId}
                className={`rounded-2xl border transition-all ${
                  finding.state === "FAIL"
                    ? "bg-rose-950/20 border-rose-900/40 hover:border-rose-800/60"
                    : finding.state === "PASS"
                    ? "bg-slate-900/50 border-slate-800/80 hover:border-slate-700"
                    : finding.state === "UNKNOWN"
                    ? "bg-amber-950/20 border-amber-900/40"
                    : "bg-slate-900/30 border-slate-800/50"
                }`}
              >
                {/* Summary Header */}
                <div
                  onClick={() => toggleExpand(finding.ruleId)}
                  className="p-4 sm:p-5 flex items-start justify-between gap-4 cursor-pointer select-none"
                >
                  <div className="flex items-start gap-3.5">
                    <div className="mt-0.5">
                      <StateIcon state={finding.state} />
                    </div>

                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-sm sm:text-base text-slate-100">
                          {finding.title}
                        </span>
                        <StateBadge state={finding.state} />
                        <SeverityBadge severity={finding.severity} />
                        <span className="text-[11px] font-mono text-slate-500 bg-slate-800/80 px-2 py-0.5 rounded">
                          {finding.ruleId}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        {finding.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-slate-400 shrink-0">
                    <span className="text-xs font-mono font-semibold hidden sm:inline text-slate-500">
                      Weight: {finding.weight}
                    </span>
                    <button
                      type="button"
                      aria-label="Toggle details"
                      className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                    >
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5" />
                      ) : (
                        <ChevronDown className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Expanded Details / Remediation / Evidence */}
                {isExpanded && (
                  <div className="px-4 sm:px-5 pb-5 pt-2 border-t border-slate-800/80 space-y-4 text-xs">
                    {/* Remediation Guidance */}
                    {finding.remediationGuidance && (
                      <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 flex items-start gap-3">
                        <Wrench className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          <span className="font-semibold text-slate-200 block">
                            Recommended Correction:
                          </span>
                          <p className="text-slate-300 leading-relaxed">
                            {finding.remediationGuidance}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Verifiable Evidence Drawer */}
                    {finding.evidence && (
                      <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-3 font-mono">
                        <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
                          <span className="font-semibold text-slate-300">
                            VERIFIABLE EVIDENCE & PROVENANCE
                          </span>
                          <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-cyan-400">
                            {finding.evidence.provenance}
                          </span>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
                          <div>
                            <span className="text-slate-500 block">Observed Value:</span>
                            <span className="text-slate-200 break-all">
                              {finding.evidence.observedValue ?? "None observed"}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-500 block">Expected Value:</span>
                            <span className="text-emerald-400 break-all">
                              {finding.evidence.expectedValue ?? "None specified"}
                            </span>
                          </div>
                        </div>

                        {finding.evidence.targetElement && (
                          <div className="text-[11px]">
                            <span className="text-slate-500 block">DOM Selector:</span>
                            <code className="text-cyan-300 bg-slate-900 px-2 py-0.5 rounded">
                              {finding.evidence.targetElement}
                            </code>
                          </div>
                        )}

                        {finding.evidence.rawSnippet && (
                          <div className="text-[11px] space-y-1">
                            <span className="text-slate-500 block">Raw Snippet:</span>
                            <pre className="p-2.5 rounded bg-slate-900 text-slate-300 text-[10px] overflow-x-auto max-h-36 border border-slate-800">
                              {finding.evidence.rawSnippet}
                            </pre>
                          </div>
                        )}

                        {finding.evidence.contextData &&
                          Object.keys(finding.evidence.contextData).length > 0 && (
                            <div className="text-[11px] space-y-1">
                              <span className="text-slate-500 block">Context Data:</span>
                              <pre className="p-2.5 rounded bg-slate-900 text-slate-400 text-[10px] overflow-x-auto max-h-32 border border-slate-800">
                                {JSON.stringify(finding.evidence.contextData, null, 2)}
                              </pre>
                            </div>
                          )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function StateIcon({ state }: { state: RuleState }) {
  switch (state) {
    case "PASS":
      return <CheckCircle2 className="w-5 h-5 text-emerald-400" />;
    case "FAIL":
      return <XCircle className="w-5 h-5 text-rose-400" />;
    case "UNKNOWN":
      return <HelpCircle className="w-5 h-5 text-amber-400" />;
    case "NOT_APPLICABLE":
      return <Slash className="w-5 h-5 text-purple-400" />;
    case "NOT_TESTED":
      return <MinusCircle className="w-5 h-5 text-slate-500" />;
    default:
      return <HelpCircle className="w-5 h-5 text-slate-400" />;
  }
}

function StateBadge({ state }: { state: RuleState }) {
  switch (state) {
    case "PASS":
      return (
        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/80">
          PASS
        </span>
      );
    case "FAIL":
      return (
        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-rose-950/80 text-rose-400 border border-rose-800/80">
          FAIL
        </span>
      );
    case "UNKNOWN":
      return (
        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-amber-950/80 text-amber-400 border border-amber-800/80">
          UNKNOWN
        </span>
      );
    case "NOT_APPLICABLE":
      return (
        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-purple-950/80 text-purple-400 border border-purple-800/80">
          NOT APPLICABLE
        </span>
      );
    case "NOT_TESTED":
      return (
        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          NOT TESTED
        </span>
      );
    default:
      return null;
  }
}

function SeverityBadge({ severity }: { severity: IssueSeverity }) {
  switch (severity) {
    case "CRITICAL":
      return (
        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300 border border-rose-700/60">
          CRITICAL
        </span>
      );
    case "HIGH":
      return (
        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-orange-950 text-orange-400 border border-orange-800/60">
          HIGH
        </span>
      );
    case "MEDIUM":
      return (
        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800/60">
          MEDIUM
        </span>
      );
    case "LOW":
      return (
        <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          LOW
        </span>
      );
    default:
      return null;
  }
}
