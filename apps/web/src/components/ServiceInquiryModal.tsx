"use client";

import React, { useState } from "react";
import {
  X,
  Send,
  CheckCircle2,
  AlertCircle,
  Shield,
  HelpCircle,
  Briefcase,
  Globe,
  MapPin,
  Clock,
  Phone,
  Mail,
  User,
} from "lucide-react";
import {
  submitLeadInquiry,
  type LeadDTO,
  type LeadSubmissionRequest,
  type LeadUrgency,
} from "../lib/api/client";

interface ServiceInquiryModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetUrl?: string;
  scanToken?: string;
  onSuccess?: (lead: LeadDTO) => void;
}

const BUSINESS_CATEGORIES = [
  "E-Commerce & Retail",
  "B2B SaaS & Tech",
  "Local & Home Services",
  "Healthcare & Medical",
  "Financial & Legal Services",
  "Real Estate & Property",
  "Publishing & Media",
  "Other Enterprise",
];

const REQUESTED_SERVICES = [
  "Technical SEO Audit & Code Remediation",
  "Core Web Vitals & Page Speed Optimization",
  "Website Migration & Architecture Overhaul",
  "Competitor Content & Keyword Gap Resolution",
  "Ongoing Technical SEO Engineering Retainer",
];

export function ServiceInquiryModal({
  isOpen,
  onClose,
  targetUrl = "",
  scanToken,
  onSuccess,
}: ServiceInquiryModalProps) {
  const [customerName, setCustomerName] = useState("");
  const [businessEmail, setBusinessEmail] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState(targetUrl);
  const [businessCategory, setBusinessCategory] = useState(BUSINESS_CATEGORIES[0]);
  const [targetCity, setTargetCity] = useState("");
  const [requestedService, setRequestedService] = useState(REQUESTED_SERVICES[0]);
  const [problemDescription, setProblemDescription] = useState("");
  const [urgency, setUrgency] = useState<LeadUrgency>("MEDIUM");
  const [consentGiven, setConsentGiven] = useState(false);
  const [honeypot, setHoneypot] = useState("");

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [submittedLead, setSubmittedLead] = useState<LeadDTO | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!consentGiven) {
      setErrorMsg("Explicit contact and privacy consent is required.");
      return;
    }

    if (!websiteUrl.trim().startsWith("http://") && !websiteUrl.trim().startsWith("https://")) {
      setErrorMsg("Website URL must start with http:// or https://");
      return;
    }

    setLoading(true);

    const payload: LeadSubmissionRequest = {
      customerName: customerName.trim(),
      businessEmail: businessEmail.trim(),
      phoneNumber: phoneNumber.trim(),
      websiteUrl: websiteUrl.trim(),
      businessCategory,
      targetCity: targetCity.trim(),
      requestedService,
      problemDescription: problemDescription.trim(),
      urgency,
      consentGiven,
      privacyPolicyVersion: "2026-v1",
      scanToken: scanToken || undefined,
      honeypot: honeypot.trim() || undefined,
    };

    try {
      const res = await submitLeadInquiry(payload);
      setSubmittedLead(res);
      if (onSuccess) {
        onSuccess(res);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to submit inquiry. Please verify your details.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl my-8">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {submittedLead ? (
          <div className="text-center py-6 space-y-4">
            <div className="inline-flex p-3 rounded-2xl bg-emerald-950 text-emerald-400 border border-emerald-800/60 mb-2">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <h3 className="text-2xl font-bold text-white tracking-tight">
              Consultation Inquiry Received
            </h3>
            <p className="text-sm text-slate-300 max-w-lg mx-auto">
              Thank you, <strong className="text-white">{submittedLead.customerName}</strong>. Our senior technical SEO engineering team has received your brief for{" "}
              <strong className="text-cyan-400 font-mono">{submittedLead.websiteUrl}</strong>.
            </p>

            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 text-left text-xs space-y-2 max-w-md mx-auto">
              <div className="flex justify-between">
                <span className="text-slate-500">Inquiry Reference:</span>
                <span className="font-mono text-slate-300">{submittedLead.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Service:</span>
                <span className="text-slate-300">{submittedLead.requestedService}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Urgency:</span>
                <span className="text-amber-400 font-bold">{submittedLead.urgency}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className="text-emerald-400 font-bold">{submittedLead.status}</span>
              </div>
            </div>

            <p className="text-xs text-slate-500 italic max-w-md mx-auto">
              An engineer will analyze your deterministic audit evidence and follow up directly via email ({submittedLead.businessEmail}) or phone ({submittedLead.phoneNumber}).
            </p>

            <div className="pt-4">
              <button
                onClick={onClose}
                className="px-6 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition"
              >
                Close & Return to Audit
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-xl bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                  <Briefcase className="w-5 h-5" />
                </span>
                <h3 className="text-xl font-bold text-white tracking-tight">
                  Request Technical SEO Consultation
                </h3>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Engage senior SEO engineers to resolve code defects, verify ranking factors, and implement deterministic fixes.
              </p>
            </div>

            {/* Error Notification */}
            {errorMsg && (
              <div className="p-3.5 rounded-2xl bg-rose-950/60 border border-rose-800/80 flex items-start gap-3 text-rose-300 text-xs">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-rose-400" />
                <div>
                  <strong className="font-semibold">Submission Error:</strong> {errorMsg}
                </div>
              </div>
            )}

            {/* Honeypot field (hidden from legitimate users) */}
            <div className="hidden" aria-hidden="true" tabIndex={-1}>
              <label htmlFor="website_hp">Leave this empty</label>
              <input
                id="website_hp"
                type="text"
                name="website_hp"
                value={honeypot}
                onChange={(e) => setHoneypot(e.target.value)}
                autoComplete="off"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Customer Name */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-cyan-400" />
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="e.g. Sarah Jenkins"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-600 text-xs focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              {/* Business Email */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-cyan-400" />
                  Business Email *
                </label>
                <input
                  type="email"
                  required
                  value={businessEmail}
                  onChange={(e) => setBusinessEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-600 text-xs focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              {/* Phone Number */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-cyan-400" />
                  Phone (with Country Code) *
                </label>
                <input
                  type="tel"
                  required
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+1 555-0199"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-600 text-xs focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              {/* Website URL */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Globe className="w-3.5 h-3.5 text-cyan-400" />
                  Website URL *
                </label>
                <input
                  type="url"
                  required
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-600 text-xs font-mono focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              {/* Business Category */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-cyan-400" />
                  Business Vertical *
                </label>
                <select
                  value={businessCategory}
                  onChange={(e) => setBusinessCategory(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-cyan-500 transition"
                >
                  {BUSINESS_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {/* Target City */}
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                  Target City / Location *
                </label>
                <input
                  type="text"
                  required
                  value={targetCity}
                  onChange={(e) => setTargetCity(e.target.value)}
                  placeholder="e.g. San Francisco, CA or London"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-600 text-xs focus:outline-none focus:border-cyan-500 transition"
                />
              </div>

              {/* Requested Service */}
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-cyan-400" />
                  Requested SEO Service *
                </label>
                <select
                  value={requestedService}
                  onChange={(e) => setRequestedService(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-cyan-500 transition"
                >
                  {REQUESTED_SERVICES.map((srv) => (
                    <option key={srv} value={srv}>
                      {srv}
                    </option>
                  ))}
                </select>
              </div>

              {/* Urgency */}
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-cyan-400" />
                  Implementation Urgency *
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as LeadUrgency[]).map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setUrgency(lvl)}
                      className={`py-2 px-3 rounded-xl text-xs font-semibold border transition ${
                        urgency === lvl
                          ? "bg-cyan-950 text-cyan-300 border-cyan-500 shadow-sm"
                          : "bg-slate-950/60 text-slate-400 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Problem Description */}
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
                  Problem Statement & Objectives (min. 10 chars) *
                </label>
                <textarea
                  required
                  rows={3}
                  value={problemDescription}
                  onChange={(e) => setProblemDescription(e.target.value)}
                  placeholder="Detail observed indexing drops, crawl errors, canonical duplicates, or speed bottlenecks..."
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-600 text-xs focus:outline-none focus:border-cyan-500 transition"
                />
              </div>
            </div>

            {/* Explicit Consent Checkbox */}
            <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-start gap-3">
              <input
                id="consent"
                type="checkbox"
                checked={consentGiven}
                onChange={(e) => setConsentGiven(e.target.checked)}
                className="mt-0.5 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-slate-900"
              />
              <label htmlFor="consent" className="text-[11px] text-slate-300 leading-relaxed">
                I authorize SEO Optimizer technical engineers to review my website audit data and contact me regarding resolution consulting. I understand that <strong className="text-white">Google search rankings are not guaranteed</strong>, and I accept the terms of the Privacy Policy (Notice v2026-v1).
              </label>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-2">
              <div className="flex items-center gap-1 text-[11px] text-slate-500">
                <Shield className="w-3.5 h-3.5 text-emerald-400" />
                <span>Zero spam guarantee. Encrypted storage.</span>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-400 hover:to-emerald-400 text-slate-950 font-bold text-xs transition disabled:opacity-50"
                >
                  {loading ? (
                    <span>Submitting...</span>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Submit Service Inquiry</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
