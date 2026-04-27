import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { RunsPage } from "./RunsPage";
import { renderWithProviders } from "../test/test-utils";

vi.mock("../api", () => ({
  api: {
    getPipelineRuns: vi.fn(),
    getPipelineRun: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe("RunsPage", () => {
  beforeEach(() => {
    mockedApi.getPipelineRuns.mockResolvedValue({
      items: [
        {
          id: "run-1",
          trigger_source: "api",
          requested_hours: 24,
          requested_top_n: null,
          profile_slug: "default",
          send_email: false,
          status: "completed",
          error_message: null,
          scraping_summary: { youtube: 1 },
          processing_summary: { youtube: { processed: 1 } },
          digest_summary: { processed: 1 },
          email_summary: { success: true, sent: false },
          started_at: "2026-04-27T10:00:00Z",
          ended_at: "2026-04-27T10:00:05Z",
          duration_seconds: 5,
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockedApi.getPipelineRun.mockResolvedValue({
      id: "run-1",
      trigger_source: "api",
      requested_hours: 24,
      requested_top_n: null,
      profile_slug: "default",
      send_email: false,
      status: "completed",
      error_message: null,
      scraping_summary: { youtube: 1 },
      processing_summary: { youtube: { processed: 1 } },
      digest_summary: { processed: 1 },
      email_summary: { success: true, sent: false },
      started_at: "2026-04-27T10:00:00Z",
      ended_at: "2026-04-27T10:00:05Z",
      duration_seconds: 5,
    });
  });

  it("renders recorded run details", async () => {
    renderWithProviders(<RunsPage />);

    expect(await screen.findByText("api")).toBeInTheDocument();
    expect(await screen.findByText("Scraping summary")).toBeInTheDocument();
  });
});
