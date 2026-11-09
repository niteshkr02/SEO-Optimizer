"use client";

import React, { useState } from "react";
import type { ResolutionPlanDTO, ResolutionTask } from "../lib/api/client";
import {
  Wrench,
  CheckCircle2,
  FileCode,
  ShieldCheck,
  UserCheck,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Sparkles,
  GitBranch,
} from "lucide-react";

interface ResolutionPlanViewProps {
  plan: ResolutionPlanDTO;
}

export function ResolutionPlanView({ plan }: ResolutionPlanViewProps) {
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>({
    [plan.tasks?.[0]?.taskId || ""]: true,
  });


  const toggleExpand = (taskId: string) => {
    setExpandedTasks((prev) => ({
      ...prev,
      [taskId]: !prev[taskId],
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header and Summary Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                <Wrench className="w-5 h-5" />
              </span>
              <h3 className="text-xl font-bold tracking-tight text-white">
                Deterministic Resolution Plan
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Prioritized by RICE-inspired Model E21 with Root-Cause Triage (Model E20).
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="px-3 py-1.5 rounded-lg bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 font-semibold">
              {plan.automatedCount} Automated Code Patches
            </span>
            <span className="px-3 py-1.5 rounded-lg bg-amber-950/80 text-amber-300 border border-amber-800/60 font-semibold">
              {plan.humanDecisionCount} Human Decisions Required
            </span>
          </div>
        </div>

        {/* Zero-Trust Notice */}
        <div className="text-xs text-slate-400 bg-slate-950/60 p-3.5 rounded-2xl border border-slate-800 flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Source Code Safety:</strong> Actual repository file paths are marked <code className="text-amber-300">UNKNOWN</code> because this audit evaluated public HTML without server access. Code diffs must be approved by an authorized engineer before merging.
          </p>
        </div>
      </div>

      {/* Task Cards */}
      <div className="space-y-4">
        {(plan.tasks ?? []).map((task) => {
          const isExpanded = !!expandedTasks[task.taskId];

          const isAutomated = task.actionType === "AUTOMATED_CODE_PATCH";

          return (
            <div
              key={task.taskId}
              className="bg-slate-900/60 border border-slate-800/90 rounded-2xl overflow-hidden transition-all hover:border-slate-700"
            >
              {/* Task Header */}
              <div
                onClick={() => toggleExpand(task.taskId)}
                className="p-5 flex items-start justify-between gap-4 cursor-pointer select-none"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                        isAutomated
                          ? "bg-cyan-950/80 text-cyan-300 border-cyan-800/80"
                          : "bg-amber-950/80 text-amber-300 border-amber-800/80"
                      }`}
                    >
                      {isAutomated ? "AUTOMATED PATCH" : "HUMAN DECISION"}
                    </span>

                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      RICE Priority: {task.priorityScore.toFixed(1)}
                    </span>

                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-400">
                      RC Triage: {task.triageScore.toFixed(1)}
                    </span>

                    <span className="text-xs font-mono text-slate-500">
                      {task.ruleId}
                    </span>
                  </div>

                  <h4 className="font-bold text-base text-slate-100">
                    {task.title}
                  </h4>

                  <p className="text-xs text-slate-400 leading-relaxed">
                    {task.proposedChange}
                  </p>
                </div>

                <div className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 transition shrink-0">
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5" />
                  ) : (
                    <ChevronDown className="w-5 h-5" />
                  )}
                </div>
              </div>

              {/* Task Details Accordion */}
              {isExpanded && (
                <div className="px-5 pb-6 pt-2 border-t border-slate-800/80 space-y-4 text-xs">
                  {/* Placement Mapping */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
                    <div>
                      <span className="text-slate-500 font-semibold block mb-0.5">
                        Observed DOM Selector:
                      </span>
                      <code className="text-cyan-300 font-mono text-[11px] bg-slate-900 px-2 py-0.5 rounded block truncate">
                        {task.targetSelector || "Document Root"}
                      </code>
                    </div>

                    <div>
                      <span className="text-slate-500 font-semibold block mb-0.5">
                        Target Source File:
                      </span>
                      <span className="text-amber-400/90 font-mono text-[11px]">
                        {task.targetFilePath}
                      </span>
                    </div>
                  </div>

                  {/* Step-by-Step Procedure */}
                  <div className="space-y-1.5">
                    <span className="font-semibold text-slate-200 block">
                      Implementation Procedure:
                    </span>
                    <ol className="list-decimal list-inside space-y-1 text-slate-300 leading-relaxed pl-1">
                      {(task.procedure ?? []).map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ol>
                  </div>


                  {/* Code Patch Proposal (if present) */}
                  {task.codePatch && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-slate-400">
                        <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                          <GitBranch className="w-4 h-4 text-cyan-400" />
                          <span>Proposed Unified Diff (Reversible Patch)</span>
                        </span>
                        <span className="text-[10px] font-mono bg-slate-800 px-2 py-0.5 rounded text-slate-400">
                          SHA: {task.codePatch.patchHash.slice(0, 12)}
                        </span>
                      </div>

                      <pre className="p-4 rounded-xl bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto border border-slate-800 leading-relaxed">
                        {task.codePatch.diffContent}
                      </pre>

                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-800/40 text-cyan-300 text-[11px]">
                        <UserCheck className="w-4 h-4 shrink-0 text-cyan-400" />
                        <span>
                          <strong>Approval Gate:</strong> Explicit human engineer authorization required before patch application.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Expected Outcome & Rollback */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
                      <span className="font-semibold text-emerald-400 block">
                        Expected Outcome:
                      </span>
                      <p className="text-slate-300 text-[11px]">
                        {task.expectedOutcome}
                      </p>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
                      <span className="font-semibold text-amber-400 block flex items-center gap-1">
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Rollback Instructions:</span>
                      </span>
                      <p className="text-slate-300 text-[11px]">
                        {task.rollbackInstructions}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
