import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api";
import { ArchivePage } from "./ArchivePage";
import { renderWithProviders } from "../test/test-utils";

vi.mock("../api", () => ({
  api: {
    getStories: vi.fn(),
    getStory: vi.fn(),
    getSources: vi.fn(),
    getSource: vi.fn(),
    getNewsletterRuns: vi.fn(),
    getNewsletterRun: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api);

describe("ArchivePage", () => {
  beforeEach(() => {
    mockedApi.getStories.mockResolvedValue({
      items: [
        {
          story_id: "story-1",
          title: "OpenAI Story",
          story_digest_status: "completed",
          story_digest_failure_reason: null,
          representative_source_type: "openai",
          representative_source_id: "openai-1",
          representative_url: "https://openai.com/story",
          representative_published_at: "2026-04-27T10:00:00Z",
          source_count: 2,
          source_types: ["openai", "youtube"],
          digest_title: "Digest title",
          digest_summary: "Digest summary",
          digest_why_it_matters: "Digest why",
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    mockedApi.getStory.mockResolvedValue({
      story_id: "story-1",
      title: "OpenAI Story",
      story_digest_status: "completed",
      story_digest_failure_reason: null,
      story_digest_last_processed_at: "2026-04-27T10:00:00Z",
      representative_source_type: "openai",
      representative_source_id: "openai-1",
      representative_url: "https://openai.com/story",
      representative_published_at: "2026-04-27T10:00:00Z",
      source_count: 2,
      source_types: ["openai", "youtube"],
      digest: {
        title: "Digest title",
        summary: "Digest summary",
        why_it_matters: "Digest why",
        disagreement_notes: null,
        synthesis_mode: "multi_source",
        available_source_count: 2,
        used_source_count: 2,
        generated_input_hash: "hash",
      },
      sources: [],
    });
    mockedApi.getSources.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    mockedApi.getSource.mockResolvedValue({
      source_type: "openai",
      source_id: "openai-1",
      title: "OpenAI Source",
      url: "https://openai.com/source",
      published_at: "2026-04-27T10:00:00Z",
      content_richness: "summary",
      content_source_type: "rss",
      enrichment_stage: "none",
      enrichment_status: "not_applicable",
      failure_reason: null,
      cleaned_content: "Content",
      description: "Description",
      transcript: null,
      markdown: null,
    });
    mockedApi.getNewsletterRuns.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    mockedApi.getNewsletterRun.mockResolvedValue({
      id: "newsletter-1",
      pipeline_run_id: "run-1",
      profile_slug: "default",
      window_hours: 24,
      resolved_top_n: 5,
      subject: "Daily AI News Digest",
      greeting: "Hey Ali",
      introduction: "Intro",
      sent: false,
      article_count: 1,
      payload_json: { articles: [] },
      created_at: "2026-04-27T10:00:00Z",
    });
  });

  it("refetches stories when the search filter changes", async () => {
    renderWithProviders(<ArchivePage />);

    expect(await screen.findByText("OpenAI Story")).toBeInTheDocument();
    await userEvent.clear(screen.getByPlaceholderText(/search by title/i));
    await userEvent.type(screen.getByPlaceholderText(/search by title/i), "agents");

    await waitFor(() => {
      expect(mockedApi.getStories).toHaveBeenLastCalledWith(
        expect.objectContaining({ q: "agents" })
      );
    });
  });
});
