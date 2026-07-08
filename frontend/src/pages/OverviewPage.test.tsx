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
    cancelPipelineRun: vi.fn(),
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
      queue_summary: { queued_runs: 0, running_runs: 0 },
      worker_status: null,
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
      run_type: "full_pipeline",
      requested_stage: null,
      retry_stage_run_id: null,
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
      queued_at: null,
      started_at: null,
      ended_at: null,
      duration_seconds: null,
      stage_runs: [],
    });
    mockedApi.cancelPipelineRun.mockResolvedValue({
      id: "run-1",
      trigger_source: "api",
      run_type: "full_pipeline",
      requested_stage: null,
      retry_stage_run_id: null,
      requested_hours: 24,
      requested_top_n: null,
      profile_slug: "default",
      send_email: false,
      status: "cancelled",
      error_message: "Cancelled from dashboard",
      scraping_summary: {},
      processing_summary: {},
      digest_summary: {},
      email_summary: {},
      queued_at: null,
      started_at: null,
      ended_at: null,
      duration_seconds: null,
      stage_runs: [],
    });
  });

  it("renders overview metrics and posts rerun requests", async () => {
    renderWithProviders(<OverviewPage />);

    expect(await screen.findByText("YouTube items")).toBeInTheDocument();
    expect(screen.getAllByText("2").length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: /run pipeline/i }));

    await waitFor(() => {
      expect(mockedApi.createPipelineRun).toHaveBeenCalledWith({ hours: 24, top_n: null });
    });
  });

  it("cancels an active run from the overview", async () => {
    mockedApi.getOverview.mockResolvedValueOnce({
      hours: 24,
      source_counts: { youtube: 2, openai: 1, anthropic: 0 },
      story_counts: { total: 3, multi_source: 1, singleton: 2 },
      digest_counts: { completed: 2, pending: 1, failed: 0 },
      queue_summary: { queued_runs: 0, running_runs: 1 },
      worker_status: {
        worker_name: "dashboard-worker",
        status: "running",
        current_run_id: "run-1",
        current_stage_name: "scraping",
        last_heartbeat_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      failure_summary: {
        hours: 168,
        summary: {
          youtube_failed: 0,
          youtube_unavailable: 0,
          anthropic_failed: 0,
          anthropic_unavailable: 0,
          story_digest_failed: 0,
          pipeline_failed: 0,
        },
        items: [],
      },
      latest_pipeline_run: {
        id: "run-1",
        trigger_source: "api",
        run_type: "full_pipeline",
        requested_stage: null,
        retry_stage_run_id: null,
        requested_hours: 24,
        requested_top_n: null,
        profile_slug: "default",
        send_email: false,
        status: "running",
        error_message: null,
        scraping_summary: {},
        processing_summary: {},
        digest_summary: {},
        email_summary: {},
        queued_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        ended_at: null,
        duration_seconds: null,
        stage_runs: [],
      },
      latest_newsletter_run: null,
    });

    renderWithProviders(<OverviewPage />);

    await userEvent.click(await screen.findByRole("button", { name: /cancel active run/i }));

    await waitFor(() => {
      expect(mockedApi.cancelPipelineRun).toHaveBeenCalledWith("run-1");
    });
  });
});
