import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ResolutionPlanView } from "../ResolutionPlanView";
import type { ResolutionPlanDTO } from "../../lib/api/client";

const mockPlan: ResolutionPlanDTO = {
  scanToken: "token-plan-123",
  targetUrl: "https://example.com",
  totalIssues: 2,
  automatedCount: 1,
  humanDecisionCount: 1,
  createdAt: "2026-11-09T14:00:00Z",
  tasks: [
    {
      taskId: "task-title-1",
      ruleId: "title-presence",
      category: "INDEXABILITY",
      severity: "HIGH",
      actionType: "AUTOMATED_CODE_PATCH",
      priorityScore: 24.0,
      triageScore: 88.0,
      title: "Add Missing <title> Tag",
      description: "Page lacks title tag.",
      targetSelector: "head > title",
      targetFilePath: "UNKNOWN (Requires Repository Access)",
      proposedChange: "Insert <title> in <head>.",
      procedure: ["Open header template.", "Insert <title> tag."],
      expectedOutcome: "Audit rule title-presence evaluates to PASS.",
      risks: ["SERP snippet text updates."],
      rollbackInstructions: "Remove inserted title tag.",
      codePatch: {
        patchId: "patch-1",
        findingId: "title-presence",
        affectedFile: "UNKNOWN (Requires Repository Access)",
        diffContent: "--- a/index.html\n+++ b/index.html\n@@ -1 +1 @@\n+<title>Title</title>",
        patchHash: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        requiresApproval: true,
        approvalStatus: "PENDING_REVIEW",
      },
    },
    {
      taskId: "task-https-2",
      ruleId: "https-enforced",
      category: "CRAWLABILITY",
      severity: "HIGH",
      actionType: "HUMAN_DECISION_REQUIRED",
      priorityScore: 16.0,
      triageScore: 92.5,
      title: "Enforce HTTPS Protocol and TLS Encryption",
      description: "Page served over HTTP.",
      targetSelector: "Web server TLS / SSL configuration",
      targetFilePath: "UNKNOWN (Requires Repository Access)",
      proposedChange: "Install SSL certificate.",
      procedure: ["Install SSL cert on server.", "Configure 301 redirect."],
      expectedOutcome: "HTTP redirects to HTTPS.",
      risks: ["Mixed content."],
      rollbackInstructions: "Revert web server config.",
      codePatch: null,
    },
  ],
};

describe("ResolutionPlanView Component", () => {
  it("renders tasks with RICE priority and triage scores", () => {
    render(<ResolutionPlanView plan={mockPlan} />);

    expect(screen.getByText("Add Missing <title> Tag")).toBeDefined();
    expect(screen.getByText(/RICE Priority: 24.0/i)).toBeDefined();
    expect(screen.getByText(/RC Triage: 88.0/i)).toBeDefined();
    expect(screen.getByText("Enforce HTTPS Protocol and TLS Encryption")).toBeDefined();
  });

  it("displays UNKNOWN for source file paths", () => {
    render(<ResolutionPlanView plan={mockPlan} />);
    expect(screen.getAllByText("UNKNOWN (Requires Repository Access)")).toBeDefined();
  });

  it("displays code patch unified diff and approval notice", () => {
    render(<ResolutionPlanView plan={mockPlan} />);

    expect(screen.getByText(/Proposed Unified Diff/i)).toBeDefined();
    expect(screen.getByText(/Explicit human engineer authorization required/i)).toBeDefined();
    expect(screen.getByText(/--- a\/index.html/i)).toBeDefined();
  });
});

