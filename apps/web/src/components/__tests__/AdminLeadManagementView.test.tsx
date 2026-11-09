import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AdminLeadManagementView } from "../AdminLeadManagementView";
import * as apiClient from "../../lib/api/client";

const mockLead: apiClient.LeadDTO = {
  id: "lead-admin-123",
  customerName: "Robert Vance",
  businessEmail: "robert@vance-refrigeration.com",
  phoneNumber: "+1 555-888-7777",
  websiteUrl: "https://vance-refrigeration.com",
  businessCategory: "Local & Home Services",
  targetCity: "Scranton, PA",
  requestedService: "Technical SEO Audit & Code Remediation",
  problemDescription: "Local organic search rankings dropped significantly.",
  urgency: "HIGH",
  status: "NEW",
  consentGiven: true,
  consentTimestamp: "2026-11-09T14:00:00Z",
  privacyPolicyVersion: "2026-v1",
  createdAt: "2026-11-09T14:00:00Z",
  updatedAt: "2026-11-09T14:00:00Z",
  statusHistory: [
    {
      id: "hist-1",
      leadId: "lead-admin-123",
      previousStatus: null,
      newStatus: "NEW",
      changedBy: "Public Form",
      notes: "Initial submission",
      createdAt: "2026-11-09T14:00:00Z",
    },
  ],
};

const mockBrief: apiClient.ServiceBriefDTO = {
  briefId: "brief-admin-999",
  leadId: "lead-admin-123",
  generatedAt: "2026-11-09T14:30:00Z",
  clientDetails: {
    customerName: "Robert Vance",
    businessEmail: "robert@vance-refrigeration.com",
    phoneNumber: "+1 555-888-7777",
    websiteUrl: "https://vance-refrigeration.com",
    businessCategory: "Local & Home Services",
    targetCity: "Scranton, PA",
    requestedService: "Technical SEO Audit",
    urgency: "HIGH",
    problemDescription: "Local organic search rankings dropped significantly.",
  },
  auditScope: {
    hasAuditReport: true,
    scanToken: "token-vance-123",
    scanTimestamp: "2026-11-09T14:00:00Z",
    targetUrl: "https://vance-refrigeration.com",
    statusCode: 200,
    overallHealthScore: 82.5,
    completenessScore: 100.0,
    totalChecksEvaluated: 20,
    failingChecksCount: 2,
    warningChecksCount: 0,
    passedChecksCount: 18,
  },
  criticalIssues: [
    {
      ruleId: "title-presence",
      category: "INDEXABILITY",
      severity: "HIGH",
      title: "Title Presence",
      description: "Missing title tag",
      observedValue: "None",
      expectedValue: "Non-empty title",
      rawSnippet: null,
      targetElement: "head > title",
      remediationGuidance: "Add title tag to head.",
    },
  ],
  proposedSolutions: [],
  implementationPriorities: [],
  verificationSummary: null,
  unknownAndUnavailableDisclosures: ["Competitor data unavailable."],
  rankingDisclaimer: "Google ranking and search engine placement are not guaranteed.",
};

describe("AdminLeadManagementView Component", () => {
  it("renders pipeline filters and displays loaded leads", async () => {
    vi.spyOn(apiClient, "listLeads").mockResolvedValue({
      items: [mockLead],
      total: 1,
      limit: 50,
      offset: 0,
    });

    render(<AdminLeadManagementView />);

    expect(screen.getByText("Admin Lead & Consultation Center")).toBeDefined();
    expect(screen.getByText("All Leads")).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("Robert Vance")).toBeDefined();
      expect(screen.getByText("https://vance-refrigeration.com")).toBeDefined();
    });
  });

  it("selects a lead and allows updating status", async () => {
    vi.spyOn(apiClient, "listLeads").mockResolvedValue({
      items: [mockLead],
      total: 1,
      limit: 50,
      offset: 0,
    });
    const updateSpy = vi.spyOn(apiClient, "updateLeadStatus").mockResolvedValue({
      ...mockLead,
      status: "CONTACTED",
    });

    render(<AdminLeadManagementView />);

    await waitFor(() => {
      expect(screen.getByText("Robert Vance")).toBeDefined();
    });

    // Click on lead row
    fireEvent.click(screen.getByText("Robert Vance"));

    // Verify detail panel opens
    expect(screen.getByText("Update Workflow Status")).toBeDefined();

    // Change status from NEW to CONTACTED
    const statusSelect = screen.getByDisplayValue("NEW");
    fireEvent.change(statusSelect, { target: { value: "CONTACTED" } });

    // Submit status update
    const saveBtn = screen.getByText("Save Status");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        "lead-admin-123",
        expect.objectContaining({ newStatus: "CONTACTED" }),
        expect.any(String)
      );
    });
  });

  it("loads and displays consultation brief with statutory disclaimer", async () => {
    vi.spyOn(apiClient, "listLeads").mockResolvedValue({
      items: [mockLead],
      total: 1,
      limit: 50,
      offset: 0,
    });
    vi.spyOn(apiClient, "getServiceBrief").mockResolvedValue(mockBrief);

    render(<AdminLeadManagementView />);

    await waitFor(() => {
      expect(screen.getByText("Robert Vance")).toBeDefined();
    });

    fireEvent.click(screen.getByText("Robert Vance"));

    // Switch to Consultation Brief tab
    const briefTab = screen.getByText(/Consultation Brief/i);
    fireEvent.click(briefTab);

    await waitFor(() => {
      expect(screen.getByText("Consultation Deliverables")).toBeDefined();
      expect(screen.getByText("82.5/100")).toBeDefined();
      expect(screen.getByText(/Google ranking and search engine placement are not guaranteed/i)).toBeDefined();
    });
  });
});
