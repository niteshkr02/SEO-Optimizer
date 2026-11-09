import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ServiceInquiryModal } from "../ServiceInquiryModal";
import * as apiClient from "../../lib/api/client";

const mockLeadResult: apiClient.LeadDTO = {
  id: "lead-uuid-12345",
  customerName: "Jane Doe",
  businessEmail: "jane@company.com",
  phoneNumber: "+1 555-0199",
  websiteUrl: "https://company.com",
  businessCategory: "E-Commerce & Retail",
  targetCity: "San Francisco, CA",
  requestedService: "Technical SEO Audit & Code Remediation",
  problemDescription: "Critical canonical loops observed on catalog pages.",
  urgency: "HIGH",
  status: "NEW",
  consentGiven: true,
  consentTimestamp: "2026-11-09T14:00:00Z",
  privacyPolicyVersion: "2026-v1",
  createdAt: "2026-11-09T14:00:00Z",
  updatedAt: "2026-11-09T14:00:00Z",
  statusHistory: [],
};

describe("ServiceInquiryModal Component", () => {
  it("renders when open and pre-fills target URL and scan token", () => {
    render(
      <ServiceInquiryModal
        isOpen={true}
        onClose={vi.fn()}
        targetUrl="https://company.com"
        scanToken="token-xyz-123"
      />
    );

    expect(screen.getByText("Request Technical SEO Consultation")).toBeDefined();
    const urlInput = screen.getByDisplayValue("https://company.com") as HTMLInputElement;
    expect(urlInput).toBeDefined();
    expect(screen.getByText(/I authorize SEO Optimizer technical engineers/i)).toBeDefined();
  });

  it("blocks submission and shows error if consent is not checked", async () => {
    render(
      <ServiceInquiryModal
        isOpen={true}
        onClose={vi.fn()}
        targetUrl="https://company.com"
      />
    );

    fireEvent.change(screen.getByPlaceholderText(/Sarah Jenkins/i), {
      target: { value: "Jane Doe" },
    });
    fireEvent.change(screen.getByPlaceholderText(/name@company.com/i), {
      target: { value: "jane@company.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/\+1 555-0199/i), {
      target: { value: "+1 555-0199" },
    });
    fireEvent.change(screen.getByPlaceholderText(/San Francisco/i), {
      target: { value: "San Francisco, CA" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Detail observed indexing/i), {
      target: { value: "Critical canonical loops observed on catalog pages." },
    });

    const submitBtn = screen.getByText("Submit Service Inquiry");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Explicit contact and privacy consent is required/i)).toBeDefined();
    });
  });

  it("submits valid inquiry and displays success confirmation card", async () => {
    const submitSpy = vi.spyOn(apiClient, "submitLeadInquiry").mockResolvedValue(mockLeadResult);

    render(
      <ServiceInquiryModal
        isOpen={true}
        onClose={vi.fn()}
        targetUrl="https://company.com"
        scanToken="token-xyz"
      />
    );

    fireEvent.change(screen.getByPlaceholderText(/Sarah Jenkins/i), {
      target: { value: "Jane Doe" },
    });
    fireEvent.change(screen.getByPlaceholderText(/name@company.com/i), {
      target: { value: "jane@company.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/\+1 555-0199/i), {
      target: { value: "+1 555-0199" },
    });
    fireEvent.change(screen.getByPlaceholderText(/San Francisco/i), {
      target: { value: "San Francisco, CA" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Detail observed indexing/i), {
      target: { value: "Critical canonical loops observed on catalog pages." },
    });

    // Check consent
    const consentBox = screen.getByRole("checkbox");
    fireEvent.click(consentBox);

    const submitBtn = screen.getByText("Submit Service Inquiry");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(submitSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText("Consultation Inquiry Received")).toBeDefined();
      expect(screen.getByText("lead-uuid-12345")).toBeDefined();
    });
  });
});

