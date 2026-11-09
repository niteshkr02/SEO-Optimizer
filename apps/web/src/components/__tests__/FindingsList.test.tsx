import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { FindingsList } from "../FindingsList";
import type { Finding } from "../../lib/api/client";

const mockFindings: Finding[] = [
  {
    ruleId: "http-status-200",
    category: "CRAWLABILITY",
    title: "HTTP Status 200 OK",
    description: "The requested page responds with HTTP 200.",
    state: "PASS",
    severity: "CRITICAL",
    weight: 10,
    evidence: {
      observedValue: "HTTP 200",
      expectedValue: "HTTP 200",
      provenance: "DIRECT_OBSERVATION",
    },
    remediationGuidance: "Ensure canonical pages return 200 OK.",
  },
  {
    ruleId: "title-presence",
    category: "INDEXABILITY",
    title: "Page Title Tag Presence",
    description: "The page must have a non-empty title tag.",
    state: "FAIL",
    severity: "HIGH",
    weight: 9,
    evidence: {
      observedValue: "No title tag found",
      expectedValue: "Non-empty <title>",
      provenance: "DIRECT_OBSERVATION",
      targetElement: "head > title",
    },
    remediationGuidance: "Add a descriptive <title> tag.",
  },
  {
    ruleId: "robots-txt-present",
    category: "CRAWLABILITY",
    title: "Robots.txt Presence & Accessibility",
    description: "The website should have /robots.txt.",
    state: "UNKNOWN",
    severity: "MEDIUM",
    weight: 6,
    evidence: {
      observedValue: "Robots.txt check timed out",
      expectedValue: "HTTP 200 on /robots.txt",
      provenance: "DIRECT_OBSERVATION",
    },
    remediationGuidance: "Check firewall or server timeout.",
  },
];

describe("FindingsList Component", () => {
  it("renders all findings and 5-state badges", () => {
    render(<FindingsList findings={mockFindings} />);

    expect(screen.getByText("HTTP Status 200 OK")).toBeDefined();
    expect(screen.getByText("Page Title Tag Presence")).toBeDefined();
    expect(screen.getByText("Robots.txt Presence & Accessibility")).toBeDefined();

    expect(screen.getByText("PASS")).toBeDefined();
    expect(screen.getByText("FAIL")).toBeDefined();
    expect(screen.getByText("UNKNOWN")).toBeDefined();
  });

  it("filters findings when state filter is clicked", () => {
    render(<FindingsList findings={mockFindings} />);

    const failFilterBtn = screen.getByRole("button", { name: /Fail \(1\)/i });
    fireEvent.click(failFilterBtn);

    expect(screen.getByText("Page Title Tag Presence")).toBeDefined();
    expect(screen.queryByText("HTTP Status 200 OK")).toBeNull();
  });

  it("expands evidence drawer when finding card is clicked", () => {
    render(<FindingsList findings={mockFindings} />);

    expect(screen.queryByText("VERIFIABLE EVIDENCE & PROVENANCE")).toBeNull();

    const titleCard = screen.getByText("Page Title Tag Presence");
    fireEvent.click(titleCard);

    expect(screen.getByText("VERIFIABLE EVIDENCE & PROVENANCE")).toBeDefined();
    expect(screen.getByText("No title tag found")).toBeDefined();
    expect(screen.getByText("head > title")).toBeDefined();
    expect(screen.getByText("Add a descriptive <title> tag.")).toBeDefined();
  });
});

