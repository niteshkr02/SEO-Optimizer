import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { CrawlProgressView } from "../CrawlProgressView";
import type { CrawlJobDTO } from "../../lib/api/client";

describe("CrawlProgressView Component", () => {
  const mockJob: CrawlJobDTO = {
    jobId: "job-12345",
    seedUrl: "https://example.com/",
    baseDomain: "example.com",
    status: "RUNNING",
    progressPercentage: 60.0,
    pagesDiscovered: 15,
    pagesCrawled: 9,
    pagesFailed: 1,
    pagesRemaining: 5,
    currentDepth: 2,
    maxPages: 25,
    maxDepth: 3,
  };

  it("renders progress percentage and counters", () => {
    const handleCancel = vi.fn();
    render(<CrawlProgressView job={mockJob} onCancel={handleCancel} isCancelling={false} />);

    expect(screen.getByText(/Website Crawl in Progress/i)).toBeDefined();
    expect(screen.getByText("60.0%")).toBeDefined();
    expect(screen.getByText("15")).toBeDefined();
    expect(screen.getByText("9")).toBeDefined();
    expect(screen.getByText("5")).toBeDefined();
  });

  it("handles cancel button click", () => {
    const handleCancel = vi.fn();
    render(<CrawlProgressView job={mockJob} onCancel={handleCancel} isCancelling={false} />);

    const cancelBtn = screen.getByRole("button", { name: /stop crawl/i });
    fireEvent.click(cancelBtn);
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });

  it("displays completed status badge when finished", () => {
    const handleCancel = vi.fn();
    const completedJob: CrawlJobDTO = {
      ...mockJob,
      status: "COMPLETED",
      progressPercentage: 100.0,
      pagesRemaining: 0,
    };
    render(<CrawlProgressView job={completedJob} onCancel={handleCancel} isCancelling={false} />);

    expect(screen.getByText("COMPLETED")).toBeDefined();
    expect(screen.queryByRole("button", { name: /stop crawl/i })).toBeNull();
  });
});
