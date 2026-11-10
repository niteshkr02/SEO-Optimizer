import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MultiPageReportView } from "../MultiPageReportView";
import type { SiteAggregateReportDTO } from "../../lib/api/client";

describe("MultiPageReportView Component", () => {
  const mockReport: SiteAggregateReportDTO = {
    jobId: "job-abcde",
    seedUrl: "https://example.com/",
    baseDomain: "example.com",
    overallScore: 82.5,
    completenessScore: 95.0,
    totalPagesAnalyzed: 5,
    totalIssuesIdentified: 3,
    categoryScores: {
      CRAWLABILITY: {
        category: "CRAWLABILITY",
        score: 90.0,
        completeness: 100.0,
        applicableChecks: 4,
        evaluatedChecks: 4,
      },
    },
    uniqueIssues: [
      {
        ruleId: "meta-description-presence",
        category: "DOCUMENT",
        severity: "HIGH",
        title: "Missing Meta Description",
        failingPagesCount: 2,
        totalPagesAudited: 5,
        impactPercentage: 40.0,
        sampleUrls: ["https://example.com/about", "https://example.com/contact"],
        sampleEvidence: [
          {
            url: "https://example.com/about",
            observedValue: "None",
            expectedValue: "Non-empty meta description tag",
          },
        ],
        remediationGuidance: "Add a descriptive meta description between 50 and 160 characters.",
      },
    ],
    crawledPages: [
      {
        pageId: "p1",
        jobId: "job-abcde",
        url: "https://example.com/",
        normalizedUrl: "https://example.com/",
        depth: 0,
        discoveryMethod: "SEED",
        status: "CRAWLED",
        httpStatus: 200,
        responseTimeMs: 80,
        overallScore: 90.0,
        title: "Example Home",
      },
      {
        pageId: "p2",
        jobId: "job-abcde",
        url: "https://example.com/about",
        normalizedUrl: "https://example.com/about",
        depth: 1,
        discoveryMethod: "HTML_LINK",
        status: "CRAWLED",
        httpStatus: 200,
        responseTimeMs: 65,
        overallScore: 75.0,
        title: "About Us",
      },
    ],
  };

  it("renders site-wide health score and domain", () => {
    render(<MultiPageReportView report={mockReport} jobId="job-abcde" />);

    expect(screen.getByText("example.com")).toBeDefined();
    expect(screen.getByText("82.5")).toBeDefined();
    expect(screen.getByText("95.0%")).toBeDefined();
    expect(screen.getByText("Missing Meta Description")).toBeDefined();
    expect(screen.getByText(/40.0% site impact/i)).toBeDefined();
  });

  it("switches to crawled pages table tab and displays pages", () => {
    render(<MultiPageReportView report={mockReport} jobId="job-abcde" />);

    const pagesTab = screen.getByRole("button", { name: /crawled pages/i });
    fireEvent.click(pagesTab);

    expect(screen.getByText("Example Home")).toBeDefined();
    expect(screen.getByText("About Us")).toBeDefined();
    expect(screen.getAllByRole("button", { name: /inspect/i }).length).toBe(2);
  });
});
