import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScanForm } from "../ScanForm";

describe("ScanForm Component", () => {
  it("renders input field and submit button", () => {
    const handleScan = vi.fn();
    render(<ScanForm onScan={handleScan} isLoading={false} />);

    expect(screen.getByPlaceholderText(/https:\/\/yourwebsite\.com/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /run free scan/i })).toBeDefined();
  });

  it("shows error when submitting empty input", async () => {
    const handleScan = vi.fn();
    render(<ScanForm onScan={handleScan} isLoading={false} />);

    const submitBtn = screen.getByRole("button", { name: /run free scan/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/please enter a website url/i)).toBeDefined();
    expect(handleScan).not.toHaveBeenCalled();
  });

  it("shows error when submitting invalid URL", async () => {
    const handleScan = vi.fn();
    render(<ScanForm onScan={handleScan} isLoading={false} />);

    const input = screen.getByPlaceholderText(/https:\/\/yourwebsite\.com/i);
    fireEvent.change(input, { target: { value: "invalid-url-string" } });

    const submitBtn = screen.getByRole("button", { name: /run free scan/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/invalid url format/i)).toBeDefined();
    expect(handleScan).not.toHaveBeenCalled();
  });

  it("submits valid URL and triggers onScan", async () => {
    const handleScan = vi.fn();
    render(<ScanForm onScan={handleScan} isLoading={false} />);

    const input = screen.getByPlaceholderText(/https:\/\/yourwebsite\.com/i);
    fireEvent.change(input, { target: { value: "https://example.com/blog" } });

    const submitBtn = screen.getByRole("button", { name: /run free scan/i });
    fireEvent.click(submitBtn);

    expect(handleScan).toHaveBeenCalledWith("https://example.com/blog");
  });
});

