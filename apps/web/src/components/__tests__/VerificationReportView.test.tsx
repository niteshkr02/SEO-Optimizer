import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { VerificationReportView } from "../VerificationReportView";
import type { VerificationReportDTO } from "../../lib/api/client";

const mockReport: VerificationReportDTO = {
  verificationId: "verif-12345",
  targetUrl: "https://example.com",
  baselineScanToken: "scan-base-123",
  postChangeScanToken: "scan-recheck-456",
  verifiedAt: "2026-11-09T14:30:00Z",
  totalAttempted: 2,
  resolvedCount: 1,
  unresolvedCount: 1,
  regressedCount: 1,
  unknownCount: 0,
  notRecheckedCount: 0,
  issueResolutionRate: 50.0,
  overallScoreDelta: {
    baselineScore: 65.0,
    postChangeScore: 78.5,
    delta: 13.5,
  },
  completenessDelta: {
    baselineScore: 100.0,
    postChangeScore: 100.0,
    delta: 0.0,
  },
  categoryDeltas: {
    INDEXABILITY: {
      baselineScore: 50.0,
      postChangeScore: 80.0,
      delta: 30.0,
    },
  },
  findingComparisons: [
    {
      ruleId: "title-presence",
      category: "INDEXABILITY",
      title: "Add Missing <title> Tag",
      previousState: "FAIL",
      currentState: "PASS",
      transition: "RESOLVED",
      wasAttempted: true,
    },
    {
      ruleId: "meta-description-presence",
      category: "INDEXABILITY",
      title: "Missing Meta Description",
      previousState: "FAIL",
      currentState: "FAIL",
      transition: "UNRESOLVED",
      wasAttempted: true,
    },
    {
      ruleId: "viewport-mobile",
      category: "DOCUMENT",
      title: "Mobile Viewport Tag",
      previousState: "PASS",
      currentState: "FAIL",
      transition: "REGRESSED",
      wasAttempted: false,
    },
  ],
  rulesetVersion: "1.0.0",
  scoringModelVersion: "1.0.0",
};

describe("VerificationReportView Component", () => {
  it("renders Model E33 Issue Resolution Rate and count metrics", () => {
    render(<VerificationReportView report={mockReport} />);

    expect(screen.getByText("Post-Deployment Verification Report")).toBeDefined();
    expect(screen.getByText("50%")).toBeDefined();
    expect(screen.getByText("Model E33 Metric")).toBeDefined();
    expect(screen.getByText("+13.5")).toBeDefined();
  });

  it("renders itemized finding transitions with transition badges", () => {
    render(<VerificationReportView report={mockReport} />);

    expect(screen.getByText("title-presence")).toBeDefined();
    expect(screen.getByText("RESOLVED")).toBeDefined();
    expect(screen.getByText("UNRESOLVED")).toBeDefined();
    expect(screen.getByText("REGRESSED")).toBeDefined();
  });

  it("handles null Issue Resolution Rate gracefully when 0 attempted", () => {
    const zeroAttemptedReport: VerificationReportDTO = {
      ...mockReport,
      totalAttempted: 0,
      resolvedCount: 0,
      issueResolutionRate: null,
    };

    render(<VerificationReportView report={zeroAttemptedReport} />);
    expect(screen.getByText("N/A (0 attempted)")).toBeDefined();
  });

  it("calls onExportMarkdown and copies markdown to clipboard", async () => {
    const exportMarkdownMock = vi.fn().mockResolvedValue("# Verification Report Markdown");
    const writeTextMock = vi.fn().mockResolvedValue(undefined);

    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    render(
      <VerificationReportView
        report={mockReport}
        onExportMarkdown={exportMarkdownMock}
      />
    );

    const copyBtn = screen.getByText("Copy Markdown Report");
    expect(copyBtn).toBeDefined();

    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(exportMarkdownMock).toHaveBeenCalledTimes(1);
      expect(writeTextMock).toHaveBeenCalledWith("# Verification Report Markdown");
    });
  });
});
