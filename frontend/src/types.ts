export interface PipelineRun {
  id: string;
  trigger_source: string;
  requested_hours: number;
  requested_top_n: number | null;
  profile_slug: string;
  send_email: boolean;
  status: string;
  error_message: string | null;
  scraping_summary: Record<string, unknown>;
  processing_summary: Record<string, unknown>;
  digest_summary: Record<string, unknown>;
  email_summary: Record<string, unknown>;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
}

export interface NewsletterRun {
  id: string;
  pipeline_run_id: string | null;
  profile_slug: string;
  window_hours: number;
  resolved_top_n: number;
  subject: string;
  greeting: string;
  introduction: string;
  sent: boolean;
  article_count: number;
  payload_json: {
    introduction?: {
      greeting?: string;
      introduction?: string;
    };
    articles?: Array<{
      digest_id: string;
      rank: number;
      relevance_score: number;
      title: string;
      summary: string;
      url: string;
      article_type: string;
      reasoning?: string | null;
      source_attribution_line?: string | null;
    }>;
    total_ranked?: number;
    top_n?: number;
  };
  created_at: string;
}

export interface SourceArchiveItem {
  source_type: string;
  source_id: string;
  title: string;
  url: string;
  published_at: string;
  content_richness: string;
  content_source_type: string;
  enrichment_stage: string;
  enrichment_status: string;
  failure_reason: string | null;
  cleaned_content: string | null;
  description: string | null;
  transcript?: string | null;
  markdown?: string | null;
}

export interface StoryArchiveItem {
  story_id: string;
  title: string;
  story_digest_status: string;
  story_digest_failure_reason: string | null;
  representative_source_type: string;
  representative_source_id: string;
  representative_url: string;
  representative_published_at: string;
  source_count: number;
  source_types: string[];
  digest_title: string | null;
  digest_summary: string | null;
  digest_why_it_matters: string | null;
}

export interface StoryArchiveDetail {
  story_id: string;
  title: string;
  story_digest_status: string;
  story_digest_failure_reason: string | null;
  story_digest_last_processed_at: string | null;
  representative_source_type: string;
  representative_source_id: string;
  representative_url: string;
  representative_published_at: string;
  source_count: number;
  source_types: string[];
  digest: {
    title: string;
    summary: string;
    why_it_matters: string;
    disagreement_notes: string | null;
    synthesis_mode: string;
    available_source_count: number;
    used_source_count: number;
    generated_input_hash: string;
  } | null;
  sources: Array<{
    source_type: string;
    source_id: string;
    title: string;
    url: string;
    published_at: string;
    content_richness: string;
    content_source_type: string;
    similarity_to_primary: number | null;
    is_primary: boolean;
  }>;
}

export interface FailureSummary {
  summary: {
    youtube_failed: number;
    youtube_unavailable: number;
    anthropic_failed: number;
    anthropic_unavailable: number;
    story_digest_failed: number;
    pipeline_failed: number;
  };
  items: Array<{
    kind: string;
    category: string;
    status: string;
    title: string;
    reference_id: string;
    source_type: string;
    failure_reason: string | null;
    occurred_at: string;
  }>;
  hours: number;
}

export interface DashboardOverview {
  hours: number;
  source_counts: {
    youtube: number;
    openai: number;
    anthropic: number;
  };
  story_counts: {
    total: number;
    multi_source: number;
    singleton: number;
  };
  digest_counts: {
    completed: number;
    pending: number;
    failed: number;
  };
  failure_summary: FailureSummary;
  latest_pipeline_run: PipelineRun | null;
  latest_newsletter_run: NewsletterRun | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
