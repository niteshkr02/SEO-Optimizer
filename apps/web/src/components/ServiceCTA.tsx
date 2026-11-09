"use client";

import React, { useState } from "react";
import { CheckCircle2, ShieldAlert, ArrowRight, Sparkles, Briefcase } from "lucide-react";
import { ServiceInquiryModal } from "./ServiceInquiryModal";

interface ServiceCTAProps {
  targetUrl?: string;
  scanToken?: string;
}

export function ServiceCTA({ targetUrl, scanToken }: ServiceCTAProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <section
        id="service-section"
        className="rounded-3xl bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-800 p-8 sm:p-12 relative overflow-hidden shadow-2xl"
      >
        {/* Background glow accent */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

        <div className="max-w-3xl mx-auto space-y-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-cyan-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Professional Implementation Service</span>
          </div>

          <h3 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
            Turn Technical Diagnosis Into Verifiable Code Resolutions
          </h3>

          <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-2xl mx-auto">
            Audit reports tell you what is broken. Our <strong>Technical SEO Implementation Service</strong> implements exact code and metadata fixes in your authorized repository and re-verifies every metric after deployment.
          </p>

          {/* Deliverables Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-left my-6">
            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-2">
              <CheckCircle2 className="w-5 h-5 text-cyan-400" />
              <h4 className="font-semibold text-sm text-slate-200">
                1. Code-Level Remediation
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                We create targeted pull requests fixing canonicals, redirects, schema syntax, and image attributes.
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-2">
              <CheckCircle2 className="w-5 h-5 text-cyan-400" />
              <h4 className="font-semibold text-sm text-slate-200">
                2. Competitor Gap Analysis
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Phase 2 models calculate mathematical keyword, content, and entity gaps against organic ranking competitors.
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 space-y-2">
              <CheckCircle2 className="w-5 h-5 text-cyan-400" />
              <h4 className="font-semibold text-sm text-slate-200">
                3. Post-Deployment Verification
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Every resolved issue is re-scanned and verified with before-and-after cryptographic provenance data.
              </p>
            </div>
          </div>

          {/* Call to Action Button */}
          <div className="max-w-md mx-auto pt-2">
            <button
              onClick={() => setModalOpen(true)}
              className="w-full py-3.5 px-6 rounded-2xl bg-gradient-to-r from-cyan-500 via-teal-500 to-emerald-500 hover:from-cyan-400 hover:via-teal-400 hover:to-emerald-400 text-slate-950 font-extrabold text-sm shadow-xl shadow-cyan-500/20 transition flex items-center justify-center gap-2 transform hover:-translate-y-0.5"
            >
              <Briefcase className="w-4 h-4" />
              <span>Request Technical SEO Consultation</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </button>
            <p className="text-[11px] text-slate-500 mt-2">
              Includes formal Consultation Brief, RICE Prioritization & Model E33 Verification Plan.
            </p>
          </div>

          {/* Mandatory Transparency Notice */}
          <div className="pt-4 border-t border-slate-800/60 text-[11px] text-slate-500 leading-relaxed max-w-xl mx-auto flex items-start justify-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0 text-slate-400 mt-0.5" />
            <span>
              <strong>Commitment to Integrity:</strong> We never promise Page 1 rankings, fixed traffic increases, or guaranteed indexing timelines. Search algorithms evolve continuously; we guarantee verifiable, high-quality technical code compliance.
            </span>
          </div>
        </div>
      </section>

      {/* Inquiry Form Modal */}
      <ServiceInquiryModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        targetUrl={targetUrl}
        scanToken={scanToken}
      />
    </>
  );
}
