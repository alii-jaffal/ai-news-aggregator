import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { RunsPage } from "./RunsPage";
import { renderWithProviders } from "../test/test-utils";

vi.mock("../api", () => ({
  api: {
    getPipelineRuns: vi.fn(),
    getPipelineRun: vi.fn(),
    cancelPipelineRun: vi.fn(),
    retryStageRun: vi.fn(),
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
          run_type: "full_pipeline",
          requested_stage: null,
          retry_stage_run_id: null,
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
          queued_at: "2026-04-27T09:59:58Z",
          started_at: "2026-04-27T10:00:00Z",
          ended_at: "2026-04-27T10:00:05Z",
          duration_seconds: 5,
          stage_runs: [],
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockedApi.getPipelineRun.mockResolvedValue({
      id: "run-1",
      trigger_source: "api",
      run_type: "full_pipeline",
      requested_stage: null,
      retry_stage_run_id: null,
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
      queued_at: "2026-04-27T09:59:58Z",
      started_at: "2026-04-27T10:00:00Z",
      ended_at: "2026-04-27T10:00:05Z",
      duration_seconds: 5,
      stage_runs: [],
    });
  });

  it("renders recorded run details", async () => {
    renderWithProviders(<RunsPage />);

    expect(await screen.findByText("api")).toBeInTheDocument();
    expect(await screen.findByText("Scraping summary")).toBeInTheDocument();
  });

  it("queues a retry for a failed stage", async () => {
    mockedApi.getPipelineRun.mockResolvedValueOnce({
      id: "run-1",
      trigger_source: "api",
      run_type: "full_pipeline",
      requested_stage: null,
      retry_stage_run_id: null,
      requested_hours: 24,
      requested_top_n: null,
      profile_slug: "default",
      send_email: false,
      status: "failed",
      error_message: "digest failed",
      scraping_summary: {},
      processing_summary: {},
      digest_summary: { failed: 1 },
      email_summary: {},
      queued_at: "2026-04-27T09:59:58Z",
      started_at: "2026-04-27T10:00:00Z",
      ended_at: "2026-04-27T10:00:05Z",
      duration_seconds: 5,
      stage_runs: [
        {
          id: "stage-1",
          pipeline_run_id: "run-1",
          stage_name: "story_digests",
          status: "failed",
          summary_json: { failed: 1 },
          error_message: "digest failed",
          retry_of_stage_run_id: null,
          started_at: "2026-04-27T10:00:01Z",
          ended_at: "2026-04-27T10:00:04Z",
          duration_seconds: 3,
        },
      ],
    });
    mockedApi.retryStageRun.mockResolvedValue({
      id: "run-2",
      trigger_source: "api",
      run_type: "single_stage",
      requested_stage: "story_digests",
      retry_stage_run_id: "stage-1",
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
      queued_at: "2026-04-27T10:10:00Z",
      started_at: null,
      ended_at: null,
      duration_seconds: null,
      stage_runs: [],
    });

    renderWithProviders(<RunsPage />);

    await userEvent.click(await screen.findByRole("button", { name: /retry stage/i }));

    await waitFor(() => {
      expect(mockedApi.retryStageRun).toHaveBeenCalledWith("run-1", "stage-1");
    });
  });
});
