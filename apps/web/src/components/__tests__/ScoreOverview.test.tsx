import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { ScoreOverview } from "../ScoreOverview";
import type { AuditReportDTO } from "../../lib/api/client";

const baseReport: AuditReportDTO = {
  scanToken: "test-token-12345",
  targetUrl: "https://example.com",
  finalUrl: "https://example.com/canonical",
  statusCode: 200,
  status: "COMPLETED",
  overallScore: 88.0,
  completenessScore: 95.0,
  categoryScores: {},
  categoryAvailability: {},
  findings: [],
  isSpaDetected: false,
  rulesetVersion: "1.0.0",
  scoringModelVersion: "1.0.0",
  createdAt: "2026-11-09T12:00:00Z",
};

describe("ScoreOverview Component", () => {
  it("renders scores and single-page audit disclaimer", () => {
    render(<ScoreOverview report={baseReport} />);

    expect(screen.getByText(/Scope Notice: Single-Page Technical Audit/i)).toBeDefined();
    expect(screen.getByText("88")).toBeDefined();
    expect(screen.getByText("95")).toBeDefined();
    expect(screen.getByText(/https:\/\/example\.com\/canonical/i)).toBeDefined();
  });

  it("displays SPA warning when isSpaDetected is true", () => {
    const spaReport: AuditReportDTO = {
      ...baseReport,
      isSpaDetected: true,
    };

    render(<ScoreOverview report={spaReport} />);
    expect(screen.getByText(/SPA Detected:/i)).toBeDefined();
  });
});

