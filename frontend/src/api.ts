import type {
  DashboardOverview,
  FailureSummary,
  NewsletterRun,
  PaginatedResponse,
  PipelineRun,
  SourceArchiveItem,
  StoryArchiveDetail,
  StoryArchiveItem,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export interface ArchiveParams {
  source_type?: string;
  status?: string;
  q?: string;
  start_at?: string;
  end_at?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export const api = {
  getOverview(hours = 24): Promise<DashboardOverview> {
    return fetchJson<DashboardOverview>(`/dashboard/overview?hours=${hours}`);
  },
  getSources(params: ArchiveParams): Promise<PaginatedResponse<SourceArchiveItem>> {
    return fetchJson<PaginatedResponse<SourceArchiveItem>>(
      `/sources${buildQuery(params as Record<string, string | number | undefined>)}`
    );
  },
  getSource(sourceType: string, sourceId: string): Promise<SourceArchiveItem> {
    return fetchJson<SourceArchiveItem>(`/sources/${sourceType}/${sourceId}`);
  },
  getStories(params: ArchiveParams): Promise<PaginatedResponse<StoryArchiveItem>> {
    return fetchJson<PaginatedResponse<StoryArchiveItem>>(
      `/stories${buildQuery(params as Record<string, string | number | undefined>)}`
    );
  },
  getStory(storyId: string): Promise<StoryArchiveDetail> {
    return fetchJson<StoryArchiveDetail>(`/stories/${storyId}`);
  },
  getFailures(hours = 168): Promise<FailureSummary> {
    return fetchJson<FailureSummary>(`/failures?hours=${hours}`);
  },
  getPipelineRuns(limit = 20, offset = 0): Promise<PaginatedResponse<PipelineRun>> {
    return fetchJson<PaginatedResponse<PipelineRun>>(
      `/pipeline-runs${buildQuery({ limit, offset })}`
    );
  },
  getPipelineRun(runId: string): Promise<PipelineRun> {
    return fetchJson<PipelineRun>(`/pipeline-runs/${runId}`);
  },
  createPipelineRun(payload: { hours: number; top_n: number | null }): Promise<PipelineRun> {
    return fetchJson<PipelineRun>("/pipeline-runs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getNewsletterRuns(limit = 20, offset = 0): Promise<PaginatedResponse<NewsletterRun>> {
    return fetchJson<PaginatedResponse<NewsletterRun>>(
      `/newsletter-runs${buildQuery({ limit, offset })}`
    );
  },
  getNewsletterRun(newsletterRunId: string): Promise<NewsletterRun> {
    return fetchJson<NewsletterRun>(`/newsletter-runs/${newsletterRunId}`);
  },
};
