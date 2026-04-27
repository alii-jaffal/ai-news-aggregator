from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PipelineRunResponse(BaseModel):
    id: str
    trigger_source: str
    requested_hours: int
    requested_top_n: int | None
    profile_slug: str
    send_email: bool
    status: str
    error_message: str | None
    scraping_summary: dict[str, Any]
    processing_summary: dict[str, Any]
    digest_summary: dict[str, Any]
    email_summary: dict[str, Any]
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: float | None


class PipelineRunListResponse(BaseModel):
    items: list[PipelineRunResponse]
    total: int
    limit: int
    offset: int


class NewsletterRunResponse(BaseModel):
    id: str
    pipeline_run_id: str | None
    profile_slug: str
    window_hours: int
    resolved_top_n: int
    subject: str
    greeting: str
    introduction: str
    sent: bool
    article_count: int
    payload_json: dict[str, Any]
    created_at: datetime


class NewsletterRunListResponse(BaseModel):
    items: list[NewsletterRunResponse]
    total: int
    limit: int
    offset: int


class SourceArchiveItemResponse(BaseModel):
    source_type: str
    source_id: str
    title: str
    url: str
    published_at: datetime
    content_richness: str
    content_source_type: str
    enrichment_stage: str
    enrichment_status: str
    failure_reason: str | None
    cleaned_content: str | None
    description: str | None
    transcript: str | None = None
    markdown: str | None = None


class SourceArchiveListResponse(BaseModel):
    items: list[SourceArchiveItemResponse]
    total: int
    limit: int
    offset: int


class StoryArchiveItemResponse(BaseModel):
    story_id: str
    title: str
    story_digest_status: str
    story_digest_failure_reason: str | None
    representative_source_type: str
    representative_source_id: str
    representative_url: str
    representative_published_at: datetime
    source_count: int
    source_types: list[str]
    digest_title: str | None
    digest_summary: str | None
    digest_why_it_matters: str | None


class StoryArchiveListResponse(BaseModel):
    items: list[StoryArchiveItemResponse]
    total: int
    limit: int
    offset: int


class StoryDigestDetailResponse(BaseModel):
    title: str
    summary: str
    why_it_matters: str
    disagreement_notes: str | None
    synthesis_mode: str
    available_source_count: int
    used_source_count: int
    generated_input_hash: str


class StorySourceResponse(BaseModel):
    source_type: str
    source_id: str
    title: str
    url: str
    published_at: datetime
    content_richness: str
    content_source_type: str
    similarity_to_primary: float | None
    is_primary: bool


class StoryArchiveDetailResponse(BaseModel):
    story_id: str
    title: str
    story_digest_status: str
    story_digest_failure_reason: str | None
    story_digest_last_processed_at: datetime | None
    representative_source_type: str
    representative_source_id: str
    representative_url: str
    representative_published_at: datetime
    source_count: int
    source_types: list[str]
    digest: StoryDigestDetailResponse | None
    sources: list[StorySourceResponse]


class FailureSummaryCountsResponse(BaseModel):
    youtube_failed: int
    youtube_unavailable: int
    anthropic_failed: int
    anthropic_unavailable: int
    story_digest_failed: int
    pipeline_failed: int


class FailureItemResponse(BaseModel):
    kind: str
    category: str
    status: str
    title: str
    reference_id: str
    source_type: str
    failure_reason: str | None
    occurred_at: datetime


class FailureSummaryResponse(BaseModel):
    summary: FailureSummaryCountsResponse
    items: list[FailureItemResponse]
    hours: int


class SourceCountsResponse(BaseModel):
    youtube: int
    openai: int
    anthropic: int


class StoryCountsResponse(BaseModel):
    total: int
    multi_source: int
    singleton: int


class DigestCountsResponse(BaseModel):
    completed: int
    pending: int
    failed: int


class DashboardOverviewResponse(BaseModel):
    hours: int
    source_counts: SourceCountsResponse
    story_counts: StoryCountsResponse
    digest_counts: DigestCountsResponse
    failure_summary: FailureSummaryResponse
    latest_pipeline_run: PipelineRunResponse | None
    latest_newsletter_run: NewsletterRunResponse | None


class PipelineRunCreateRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=168)
    top_n: int | None = Field(default=None, ge=1, le=50)
