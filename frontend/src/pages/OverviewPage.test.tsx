import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { OverviewPage } from "./OverviewPage";
import { renderWithProviders } from "../test/test-utils";

vi.mock("../api", () => ({
  api: {
    getOverview: vi.fn(),
    createPipelineRun: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe("OverviewPage", () => {
  beforeEach(() => {
    mockedApi.getOverview.mockResolvedValue({
      hours: 24,
      source_counts: { youtube: 2, openai: 1, anthropic: 0 },
      story_counts: { total: 3, multi_source: 1, singleton: 2 },
      digest_counts: { completed: 2, pending: 1, failed: 0 },
      failure_summary: {
        hours: 168,
        summary: {
          youtube_failed: 0,
          youtube_unavailable: 1,
          anthropic_failed: 0,
          anthropic_unavailable: 0,
          story_digest_failed: 0,
          pipeline_failed: 0,
        },
        items: [],
      },
      latest_pipeline_run: null,
      latest_newsletter_run: null,
    });
    mockedApi.createPipelineRun.mockResolvedValue({
      id: "run-1",
      trigger_source: "api",
      requested_hours: 24,
      requested_top_n: null,
      profile_slug: "default",
      send_email: false,
      status: "queued",
      error_message: null,
      scraping_summary: {},
      processing_summary: {},
      digest_summary: {},
      email_summary: {},
      started_at: null,
      ended_at: null,
      duration_seconds: null,
    });
  });

  it("renders overview metrics and posts rerun requests", async () => {
    renderWithProviders(<OverviewPage />);

    expect(await screen.findByText("YouTube items")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /run pipeline/i }));

    await waitFor(() => {
      expect(mockedApi.createPipelineRun).toHaveBeenCalledWith({ hours: 24, top_n: null });
    });
  });
});
