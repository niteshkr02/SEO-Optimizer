"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Users,
  Search,
  Filter,
  RefreshCw,
  ExternalLink,
  Clock,
  Briefcase,
  FileText,
  Download,
  Copy,
  Check,
  ShieldCheck,
  Key,
  ChevronRight,
  AlertTriangle,
  History,
} from "lucide-react";
import {
  listLeads,
  updateLeadStatus,
  getServiceBrief,
  exportBriefMarkdown,
  getBriefPdfUrl,
  type LeadDTO,
  type LeadStatus,
  type ServiceBriefDTO,
} from "../lib/api/client";

const STATUS_FILTERS: { label: string; value: LeadStatus | "ALL" }[] = [
  { label: "All Leads", value: "ALL" },
  { label: "New", value: "NEW" },
  { label: "Contacted", value: "CONTACTED" },
  { label: "Scoped", value: "SCOPED" },
  { label: "Contracted", value: "CONTRACTED" },
  { label: "Closed", value: "CLOSED" },
];

export function AdminLeadManagementView() {
  const [adminApiKey, setAdminApiKey] = useState("dev-admin-secret-key-change-in-production");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [leads, setLeads] = useState<LeadDTO[]>([]);
  const [totalLeads, setTotalLeads] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Selected lead for detail inspection
  const [selectedLead, setSelectedLead] = useState<LeadDTO | null>(null);
  const [activeTab, setActiveTab] = useState<"details" | "history" | "brief">("details");

  // Status update state
  const [newStatus, setNewStatus] = useState<LeadStatus>("CONTACTED");
  const [statusNotes, setStatusNotes] = useState("");
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Service brief preview
  const [serviceBrief, setServiceBrief] = useState<ServiceBriefDTO | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [copiedMd, setCopiedMd] = useState(false);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await listLeads(
        {
          status: statusFilter === "ALL" ? undefined : statusFilter,
          search: searchQuery.trim() || undefined,
        },
        adminApiKey
      );
      setLeads(res.items);
      setTotalLeads(res.total);
      if (selectedLead) {
        const refreshed = res.items.find((l) => l.id === selectedLead.id);
        if (refreshed) setSelectedLead(refreshed);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to fetch leads. Verify administrative authorization credentials.");
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchQuery, adminApiKey, selectedLead]);

  useEffect(() => {
    fetchLeads();
  }, [statusFilter, adminApiKey]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLeads();
  };

  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLead) return;

    setUpdatingStatus(true);
    try {
      const updated = await updateLeadStatus(
        selectedLead.id,
        {
          newStatus,
          changedBy: "Admin Operator (Web Dashboard)",
          notes: statusNotes.trim() || undefined,
        },
        adminApiKey
      );
      setSelectedLead(updated);
      setStatusNotes("");
      await fetchLeads();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`Status update failed: ${err.message}`);
      }
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleLoadBrief = async (lead: LeadDTO) => {
    setBriefLoading(true);
    try {
      const brief = await getServiceBrief(lead.id, adminApiKey);
      setServiceBrief(brief);
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`Brief generation error: ${err.message}`);
      }
    } finally {
      setBriefLoading(false);
    }
  };

  const handleCopyMarkdownBrief = async () => {
    if (!selectedLead) return;
    try {
      const md = await exportBriefMarkdown(selectedLead.id, adminApiKey);
      await navigator.clipboard.writeText(md);
      setCopiedMd(true);
      setTimeout(() => setCopiedMd(false), 2000);
    } catch {
      alert("Failed to copy Markdown brief.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Authorization Config */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                <Users className="w-5 h-5" />
              </span>
              <h3 className="text-xl font-bold tracking-tight text-white">
                Admin Lead & Consultation Center
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic service-led consultation handoff, status pipeline, and evidence brief exports.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Key className="w-3.5 h-3.5 text-cyan-400" />
              Admin Key:
            </span>
            <input
              type="password"
              value={adminApiKey}
              onChange={(e) => setAdminApiKey(e.target.value)}
              className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 w-48 sm:w-64 focus:outline-none focus:border-cyan-500"
              title="Admin API authorization key"
            />
          </div>
        </div>

        {/* Status Pipeline Filter Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-slate-800/80">
          <div className="flex flex-wrap gap-1.5 p-1 rounded-2xl bg-slate-950 border border-slate-800">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
                  statusFilter === f.value
                    ? "bg-cyan-500 text-slate-950 shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search leads..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 w-48 sm:w-60"
              />
            </div>
            <button
              type="submit"
              className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              title="Refresh leads"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </form>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Grid: Leads Table + Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Leads Table */}
        <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 overflow-hidden space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-bold text-sm text-slate-200">
              Inquiry Pipeline ({totalLeads})
            </h4>
            <span className="text-[11px] text-slate-500">
              Showing {leads.length} records
            </span>
          </div>

          {leads.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No leads match current filters or authorization credentials.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                    <th className="py-2.5 px-3">Client</th>
                    <th className="py-2.5 px-3">Target URL</th>
                    <th className="py-2.5 px-3">Urgency</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {leads.map((lead) => (
                    <tr
                      key={lead.id}
                      onClick={() => {
                        setSelectedLead(lead);
                        setNewStatus(lead.status);
                        setServiceBrief(null);
                        setActiveTab("details");
                      }}
                      className={`cursor-pointer transition hover:bg-slate-800/40 ${
                        selectedLead?.id === lead.id ? "bg-slate-800/60" : ""
                      }`}
                    >
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-200">
                          {lead.customerName}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {lead.businessEmail}
                        </div>
                      </td>
                      <td className="py-3 px-3 font-mono text-cyan-400 text-[11px] max-w-[160px] truncate">
                        {lead.websiteUrl}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            lead.urgency === "CRITICAL"
                              ? "bg-rose-950 text-rose-400 border border-rose-800/80"
                              : lead.urgency === "HIGH"
                              ? "bg-amber-950 text-amber-400 border border-amber-800/80"
                              : "bg-slate-800 text-slate-300"
                          }`}
                        >
                          {lead.urgency}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <StatusBadge status={lead.status} />
                      </td>
                      <td className="py-3 px-3">
                        <ChevronRight className="w-4 h-4 text-slate-500" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: Lead Detail & Brief Actions */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-6">
          {selectedLead ? (
            <div className="space-y-6">
              {/* Detail Header */}
              <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                <div>
                  <h4 className="font-bold text-base text-white">
                    {selectedLead.customerName}
                  </h4>
                  <a
                    href={selectedLead.websiteUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-cyan-400 hover:underline font-mono inline-flex items-center gap-1 mt-0.5"
                  >
                    <span>{selectedLead.websiteUrl}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <StatusBadge status={selectedLead.status} />
              </div>

              {/* Sub-Tabs: Details | History | Brief */}
              <div className="flex gap-1 p-1 rounded-xl bg-slate-950 border border-slate-800 text-xs">
                <button
                  onClick={() => setActiveTab("details")}
                  className={`flex-1 py-1.5 rounded-lg font-medium transition ${
                    activeTab === "details"
                      ? "bg-slate-800 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Details
                </button>
                <button
                  onClick={() => setActiveTab("history")}
                  className={`flex-1 py-1.5 rounded-lg font-medium transition ${
                    activeTab === "history"
                      ? "bg-slate-800 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  History ({selectedLead.statusHistory?.length || 0})
                </button>
                <button
                  onClick={() => {
                    setActiveTab("brief");
                    if (!serviceBrief) handleLoadBrief(selectedLead);
                  }}
                  className={`flex-1 py-1.5 rounded-lg font-medium transition ${
                    activeTab === "brief"
                      ? "bg-slate-800 text-white"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Consultation Brief
                </button>
              </div>

              {/* TAB 1: DETAILS */}
              {activeTab === "details" && (
                <div className="space-y-4 text-xs">
                  <div className="grid grid-cols-2 gap-3 p-3.5 rounded-2xl bg-slate-950 border border-slate-800">
                    <div>
                      <span className="text-slate-500 block">Email:</span>
                      <span className="text-slate-200 font-mono">{selectedLead.businessEmail}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Phone:</span>
                      <span className="text-slate-200 font-mono">{selectedLead.phoneNumber}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Vertical:</span>
                      <span className="text-slate-200">{selectedLead.businessCategory}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block">Location:</span>
                      <span className="text-slate-200">{selectedLead.targetCity}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-slate-500 block">Requested Service:</span>
                      <span className="text-cyan-400 font-semibold">{selectedLead.requestedService}</span>
                    </div>
                    {selectedLead.scanToken && (
                      <div className="col-span-2">
                        <span className="text-slate-500 block">Linked Scan Token:</span>
                        <span className="text-slate-400 font-mono">{selectedLead.scanToken}</span>
                      </div>
                    )}
                  </div>

                  <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 space-y-1">
                    <span className="text-slate-400 font-semibold block">Client Problem Statement:</span>
                    <p className="text-slate-300 leading-relaxed italic">
                      &quot;{selectedLead.problemDescription}&quot;
                    </p>
                  </div>

                  {/* Status Transition Form */}
                  <form onSubmit={handleUpdateStatus} className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3">
                    <h5 className="font-bold text-slate-200 text-xs">Update Workflow Status</h5>
                    <div className="grid grid-cols-2 gap-2">
                      <select
                        value={newStatus}
                        onChange={(e) => setNewStatus(e.target.value as LeadStatus)}
                        className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
                      >
                        <option value="NEW">NEW</option>
                        <option value="CONTACTED">CONTACTED</option>
                        <option value="SCOPED">SCOPED</option>
                        <option value="CONTRACTED">CONTRACTED</option>
                        <option value="CLOSED">CLOSED</option>
                      </select>
                      <button
                        type="submit"
                        disabled={updatingStatus || newStatus === selectedLead.status}
                        className="px-4 py-1.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition disabled:opacity-50"
                      >
                        {updatingStatus ? "Updating..." : "Save Status"}
                      </button>
                    </div>
                    <input
                      type="text"
                      placeholder="Add transition notes (e.g. Scoping call scheduled)..."
                      value={statusNotes}
                      onChange={(e) => setStatusNotes(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </form>
                </div>
              )}

              {/* TAB 2: HISTORY */}
              {activeTab === "history" && (
                <div className="space-y-3">
                  <h5 className="font-bold text-xs text-slate-300">Status Audit History</h5>
                  <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                    {(selectedLead.statusHistory ?? []).map((h) => (
                      <div key={h.id} className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-cyan-400">
                            {h.previousStatus ? `${h.previousStatus} → ` : ""}
                            {h.newStatus}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            {new Date(h.createdAt || Date.now()).toLocaleTimeString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        <div className="text-slate-400 text-[11px]">Changed by: {h.changedBy}</div>
                        {h.notes && <div className="text-slate-300 italic text-[11px]">&quot;{h.notes}&quot;</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: CONSULTATION BRIEF */}
              {activeTab === "brief" && (
                <div className="space-y-4 text-xs">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <span className="font-bold text-slate-200">Consultation Deliverables</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleCopyMarkdownBrief}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center gap-1 text-[11px]"
                        title="Copy Markdown"
                      >
                        {copiedMd ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>Markdown</span>
                      </button>

                      <a
                        href={getBriefPdfUrl(selectedLead.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/80 transition flex items-center gap-1 text-[11px]"
                        title="Download PDF Brief"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>PDF Report</span>
                      </a>
                    </div>
                  </div>

                  {briefLoading ? (
                    <div className="text-center py-8 text-slate-500">Compiling consultation brief...</div>
                  ) : serviceBrief ? (
                    <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                        <span className="text-slate-400 font-semibold block">Audit Scope:</span>
                        <div className="flex justify-between text-slate-300">
                          <span>Health Score:</span>
                          <span className="font-bold text-emerald-400">
                            {serviceBrief.auditScope.overallHealthScore !== null && serviceBrief.auditScope.overallHealthScore !== undefined
                              ? `${serviceBrief.auditScope.overallHealthScore.toFixed(1)}/100`
                              : "Unmeasured"}
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Completeness:</span>
                          <span className="font-bold text-cyan-400">
                            {serviceBrief.auditScope.completenessScore !== null && serviceBrief.auditScope.completenessScore !== undefined
                              ? `${serviceBrief.auditScope.completenessScore.toFixed(1)}%`
                              : "N/A"}
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Verified Critical Issues:</span>
                          <span className="font-bold text-rose-400">{(serviceBrief.criticalIssues ?? []).length}</span>
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <span className="text-slate-400 font-semibold block">Critical Issues Identified:</span>
                        {(serviceBrief.criticalIssues ?? []).length === 0 ? (
                          <div className="text-slate-500 italic">No critical issues identified.</div>
                        ) : (
                          (serviceBrief.criticalIssues ?? []).map((iss) => (
                            <div key={iss.ruleId} className="border-b border-slate-800/60 pb-1.5 last:border-0 last:pb-0">
                              <span className="font-mono text-rose-400 block">{iss.ruleId}</span>
                              <span className="text-slate-400 text-[11px] block">{iss.description}</span>
                            </div>
                          ))
                        )}
                      </div>

                      <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-900/60 text-rose-300 text-[11px]">
                        <strong>Statutory Disclaimer:</strong> {serviceBrief.rankingDisclaimer}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-slate-500">Brief not loaded yet.</div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-20 text-slate-500 text-xs">
              Select a lead from the pipeline to review client specifications and consultation deliverables.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: LeadStatus }) {
  switch (status) {
    case "NEW":
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-950 text-cyan-400 border border-cyan-800/80">
          NEW
        </span>
      );
    case "CONTACTED":
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-950 text-blue-400 border border-blue-800/80">
          CONTACTED
        </span>
      );
    case "SCOPED":
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-950 text-purple-400 border border-purple-800/80">
          SCOPED
        </span>
      );
    case "CONTRACTED":
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/80">
          CONTRACTED
        </span>
      );
    case "CLOSED":
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
          CLOSED
        </span>
      );
    default:
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400">
          {status}
        </span>
      );
  }
}
