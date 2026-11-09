"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Users,
  Search,
  RefreshCw,
  ExternalLink,
  Clock,
  Briefcase,
  FileText,
  Download,
  Copy,
  Check,
  ShieldCheck,
  Lock,
  LogOut,
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
  loginAdmin,
  logoutAdmin,
  checkAdminSession,
  type LeadDTO,
  type LeadStatus,
  type ServiceBriefDTO,
  type AdminSessionResponse,
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
  // Session Authentication State
  const [session, setSession] = useState<AdminSessionResponse | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Pipeline Filter & Data State
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

  // Initial session check on mount
  useEffect(() => {
    let mounted = true;
    checkAdminSession()
      .then((res) => {
        if (mounted) {
          if (res.authenticated) {
            setSession(res);
          }
          setCheckingSession(false);
        }
      })
      .catch(() => {
        if (mounted) setCheckingSession(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginUsername.trim() || !loginPassword) return;

    setLoginLoading(true);
    setLoginError(null);
    try {
      const res = await loginAdmin({
        username: loginUsername.trim(),
        password: loginPassword,
      });
      setSession(res);
      setLoginPassword("");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setLoginError(err.message);
      } else {
        setLoginError("Administrative login failed. Verify credentials.");
      }
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logoutAdmin();
    } finally {
      setSession(null);
      setLeads([]);
      setSelectedLead(null);
      setTotalLeads(0);
    }
  };

  const fetchLeads = useCallback(async () => {
    if (!session?.authenticated) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await listLeads(
        {
          status: statusFilter === "ALL" ? undefined : statusFilter,
          search: searchQuery.trim() || undefined,
        },
        { csrfToken: session.csrf_token ?? undefined }
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
        setErrorMsg("Failed to fetch leads. Verify administrative session.");
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter, searchQuery, session, selectedLead]);

  useEffect(() => {
    if (session?.authenticated) {
      fetchLeads();
    }
  }, [session, statusFilter, fetchLeads]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLeads();
  };

  const handleUpdateStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLead || !session) return;

    setUpdatingStatus(true);
    try {
      const updated = await updateLeadStatus(
        selectedLead.id,
        {
          newStatus,
          changedBy: `Admin Operator (${session.username || "Staff"})`,
          notes: statusNotes.trim() || undefined,
        },
        { csrfToken: session.csrf_token ?? undefined }
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
      const brief = await getServiceBrief(lead.id, {
        csrfToken: session?.csrf_token ?? undefined,
      });
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
      const md = await exportBriefMarkdown(selectedLead.id, {
        csrfToken: session?.csrf_token ?? undefined,
      });
      await navigator.clipboard.writeText(md);
      setCopiedMd(true);
      setTimeout(() => setCopiedMd(false), 2000);
    } catch {
      alert("Failed to copy Markdown brief.");
    }
  };

  // Loading Session State
  if (checkingSession) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-12 text-center text-slate-400">
        <RefreshCw className="w-6 h-6 animate-spin mx-auto text-cyan-400 mb-3" />
        <p className="text-sm">Verifying administrative security session...</p>
      </div>
    );
  }

  // Unauthenticated: Render Hardened Login Form
  if (!session?.authenticated) {
    return (
      <div className="max-w-md mx-auto my-8 bg-slate-900/90 border border-slate-800 rounded-3xl p-8 backdrop-blur shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-cyan-950/80 border border-cyan-800/80 text-cyan-400 flex items-center justify-center mx-auto shadow-inner">
            <Lock className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-white tracking-tight">Admin Authentication</h3>
          <p className="text-xs text-slate-400">
            Sign in to access lead management, consultation briefs, and workflow pipelines.
          </p>
        </div>

        {loginError && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{loginError}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Username</label>
            <input
              type="text"
              required
              value={loginUsername}
              onChange={(e) => setLoginUsername(e.target.value)}
              placeholder="e.g. admin"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Password</label>
            <input
              type="password"
              required
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <button
            type="submit"
            disabled={loginLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs tracking-wide uppercase transition shadow-lg shadow-cyan-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loginLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Authenticating...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Sign In Securely</span>
              </>
            )}
          </button>
        </form>

        <div className="pt-4 border-t border-slate-800/80 text-[11px] text-slate-500 space-y-1">
          <p className="flex items-center gap-1.5 font-medium text-slate-400">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Hardened Security Architecture:
          </p>
          <p>
            Sessions are secured with HttpOnly cookies, bound CSRF protection, and strict origin validation.
            Zero shared API keys are bundled into frontend scripts.
          </p>
        </div>
      </div>
    );
  }

  // Authenticated State: Main Admin Lead Management View
  return (
    <div className="space-y-6">
      {/* Top Banner & Session Status */}
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

          {/* Session Info & Logout */}
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-xl bg-emerald-950/60 border border-emerald-800/80 flex items-center gap-2 text-xs text-emerald-300 font-medium">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Admin: {session.username || "Staff"}</span>
            </div>
            <button
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition"
              title="Sign out of administrative session"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
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
              {loading ? "Loading inquiries..." : "No service inquiries found for the current filter."}
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {leads.map((lead) => {
                const isSelected = selectedLead?.id === lead.id;
                return (
                  <button
                    key={lead.id}
                    onClick={() => {
                      setSelectedLead(lead);
                      setNewStatus(lead.status);
                      handleLoadBrief(lead);
                    }}
                    className={`w-full text-left p-4 rounded-2xl border transition flex items-center justify-between gap-3 ${
                      isSelected
                        ? "bg-slate-800/90 border-cyan-500/80 shadow-md shadow-cyan-950/30"
                        : "bg-slate-950/60 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700"
                    }`}
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-xs text-white truncate">
                          {lead.customerName}
                        </span>
                        <StatusBadge status={lead.status} />
                        <span className="text-[10px] text-slate-400 font-mono">
                          {lead.businessCategory}
                        </span>
                      </div>
                      <p className="text-xs text-cyan-400/90 truncate font-mono">
                        {lead.websiteUrl}
                      </p>
                      <div className="flex items-center gap-3 text-[10px] text-slate-500">
                        <span>{lead.targetCity}</span>
                        <span>•</span>
                        <span>{lead.createdAt ? new Date(lead.createdAt).toLocaleDateString() : ""}</span>
                        <span>•</span>
                        <span className="font-bold uppercase tracking-wider text-slate-400">
                          {lead.urgency}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500 shrink-0" />
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Selected Lead Details & Action Panel */}
        <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-3xl p-6 space-y-6">
          {selectedLead ? (
            <div className="space-y-6">
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h4 className="text-base font-bold text-white">
                    {selectedLead.customerName}
                  </h4>
                  <a
                    href={selectedLead.websiteUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-cyan-400 hover:underline flex items-center gap-1 mt-0.5"
                  >
                    <span>{selectedLead.websiteUrl}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <StatusBadge status={selectedLead.status} />
              </div>

              {/* Sub-tabs: Details / History / Brief Preview */}
              <div className="flex gap-2 p-1 rounded-xl bg-slate-950 border border-slate-800 text-xs">
                <button
                  onClick={() => setActiveTab("details")}
                  className={`flex-1 py-1.5 rounded-lg font-medium transition ${
                    activeTab === "details"
                      ? "bg-slate-800 text-white shadow"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Details
                </button>
                <button
                  onClick={() => setActiveTab("history")}
                  className={`flex-1 py-1.5 rounded-lg font-medium transition flex items-center justify-center gap-1 ${
                    activeTab === "history"
                      ? "bg-slate-800 text-white shadow"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <History className="w-3 h-3" />
                  <span>Audit Trail</span>
                </button>
                <button
                  onClick={() => setActiveTab("brief")}
                  className={`flex-1 py-1.5 rounded-lg font-medium transition flex items-center justify-center gap-1 ${
                    activeTab === "brief"
                      ? "bg-slate-800 text-white shadow"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <FileText className="w-3 h-3" />
                  <span>Service Brief</span>
                </button>
              </div>

              {/* TAB 1: Lead Details & Status Transition */}
              {activeTab === "details" && (
                <div className="space-y-4 text-xs">
                  <div className="grid grid-cols-2 gap-3 p-3 rounded-2xl bg-slate-950/80 border border-slate-800">
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                        Business Email
                      </span>
                      <span className="text-slate-200 font-mono text-[11px] truncate block">
                        {selectedLead.businessEmail}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                        Phone
                      </span>
                      <span className="text-slate-200 font-mono text-[11px] block">
                        {selectedLead.phoneNumber}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                        Target City
                      </span>
                      <span className="text-slate-200 block">{selectedLead.targetCity}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                        Urgency
                      </span>
                      <span className="text-slate-200 font-bold block">{selectedLead.urgency}</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                      Requested Service
                    </span>
                    <p className="text-slate-200 font-medium">{selectedLead.requestedService}</p>
                  </div>

                  <div className="p-3 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase block font-semibold">
                      Problem Description
                    </span>
                    <p className="text-slate-300 leading-relaxed whitespace-pre-wrap">
                      {selectedLead.problemDescription}
                    </p>
                  </div>

                  {/* Status Transition Control */}
                  <form
                    onSubmit={handleUpdateStatus}
                    className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3"
                  >
                    <span className="font-bold text-xs text-slate-200 block">
                      Update Workflow Status
                    </span>
                    <div className="flex gap-2">
                      <select
                        value={newStatus}
                        onChange={(e) => setNewStatus(e.target.value as LeadStatus)}
                        className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 flex-1"
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
                        {updatingStatus ? "Saving..." : "Save Status"}
                      </button>
                    </div>

                    <textarea
                      placeholder="Audit note / reason for status transition..."
                      value={statusNotes}
                      onChange={(e) => setStatusNotes(e.target.value)}
                      rows={2}
                      className="w-full px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                    />
                  </form>
                </div>
              )}

              {/* TAB 2: Immutable Audit Trail */}
              {activeTab === "history" && (
                <div className="space-y-3 max-h-96 overflow-y-auto pr-1 text-xs">
                  {(selectedLead.statusHistory ?? []).map((h) => (
                    <div
                      key={h.id}
                      className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-1"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-cyan-400">
                          {h.previousStatus ? `${h.previousStatus} → ` : ""}
                          {h.newStatus}
                        </span>
                        <span className="text-slate-500 font-mono">
                          {h.createdAt ? new Date(h.createdAt).toLocaleString() : ""}
                        </span>
                      </div>
                      <div className="text-slate-400 text-[11px]">
                        Operator: <span className="text-slate-300 font-medium">{h.changedBy}</span>
                      </div>
                      {h.notes && (
                        <p className="text-slate-300 italic text-[11px] pt-1 border-t border-slate-900">
                          &ldquo;{h.notes}&rdquo;
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 3: Consultation Service Brief & Exports */}
              {activeTab === "brief" && (
                <div className="space-y-4 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200">Consultation Deliverables</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleCopyMarkdownBrief}
                        className="px-2.5 py-1 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 transition"
                        title="Copy Markdown Brief"
                      >
                        {copiedMd ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedMd ? "Copied" : "Markdown"}</span>
                      </button>

                      <a
                        href={getBriefPdfUrl(selectedLead.id)}
                        target="_blank"
                        rel="noreferrer"
                        className="px-2.5 py-1 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold flex items-center gap-1 transition shadow"
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
                            {serviceBrief.auditScope.overallHealthScore !== null &&
                            serviceBrief.auditScope.overallHealthScore !== undefined
                              ? `${serviceBrief.auditScope.overallHealthScore.toFixed(1)}/100`
                              : "Unmeasured"}
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Completeness:</span>
                          <span className="font-bold text-cyan-400">
                            {serviceBrief.auditScope.completenessScore !== null &&
                            serviceBrief.auditScope.completenessScore !== undefined
                              ? `${serviceBrief.auditScope.completenessScore.toFixed(1)}%`
                              : "N/A"}
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Verified Critical Issues:</span>
                          <span className="font-bold text-rose-400">
                            {(serviceBrief.criticalIssues ?? []).length}
                          </span>
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <span className="text-slate-400 font-semibold block">Critical Issues Identified:</span>
                        {(serviceBrief.criticalIssues ?? []).length === 0 ? (
                          <div className="text-slate-500 italic">No critical issues identified.</div>
                        ) : (
                          (serviceBrief.criticalIssues ?? []).map((iss) => (
                            <div
                              key={iss.ruleId}
                              className="border-b border-slate-800/60 pb-1.5 last:border-0 last:pb-0"
                            >
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
