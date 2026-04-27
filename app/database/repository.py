from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from sqlalchemy import or_, tuple_
from sqlalchemy.orm import Session

from app.content_normalization import (
    NormalizedSourceItem,
    clean_markdown_text,
    clean_transcript_text,
    select_normalized_content,
)
from app.story_clustering import build_source_key
from app.story_digesting import (
    StoryDigestJob,
    StoryDigestSource,
    build_story_digest_input_hash,
    format_source_attribution_line,
)

from .connection import get_session
from .models import (
    AnthropicArticle,
    NewsletterRun,
    OpenAIArticle,
    PipelineRun,
    Story,
    StoryDigest,
    StorySourceLink,
    UserProfile,
    YouTubeVideo,
)


class Repository:
    def __init__(self, session: Optional[Session] = None):
        self._owns_session = session is None
        self.session = session or get_session()

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def get_user_profile_by_slug(self, slug: str) -> Optional[UserProfile]:
        return self.session.query(UserProfile).filter_by(slug=slug).first()

    def list_user_profiles(self) -> List[UserProfile]:
        return (
            self.session.query(UserProfile)
            .order_by(UserProfile.is_active.desc(), UserProfile.slug.asc())
            .all()
        )

    def get_active_user_profile(self) -> Optional[UserProfile]:
        return self.session.query(UserProfile).filter_by(is_active=True).first()

    def upsert_user_profile(
        self,
        *,
        slug: str,
        name: str,
        title: str,
        background: str,
        expertise_level: str,
        interests: Sequence[str],
        preferred_source_types: Sequence[str],
        preferences: Dict[str, Any],
        newsletter_top_n: int,
        is_active: Optional[bool] = None,
    ) -> UserProfile:
        profile = self.get_user_profile_by_slug(slug)
        if profile is None:
            profile = UserProfile(id=str(uuid4()), slug=slug)
            self.session.add(profile)

        profile.name = name
        profile.title = title
        profile.background = background
        profile.expertise_level = expertise_level
        profile.interests = list(interests)
        profile.preferred_source_types = list(preferred_source_types)
        profile.preferences = dict(preferences)
        profile.newsletter_top_n = newsletter_top_n

        if is_active is True:
            (
                self.session.query(UserProfile)
                .filter(UserProfile.slug != slug, UserProfile.is_active.is_(True))
                .update({"is_active": False}, synchronize_session=False)
            )
            profile.is_active = True
        elif is_active is False:
            profile.is_active = False
        elif self.get_active_user_profile() is None:
            profile.is_active = True

        self.session.commit()
        return profile

    def set_active_user_profile(self, slug: str) -> Optional[UserProfile]:
        profile = self.get_user_profile_by_slug(slug)
        if profile is None:
            return None

        (
            self.session.query(UserProfile)
            .filter(UserProfile.is_active.is_(True))
            .update({"is_active": False}, synchronize_session=False)
        )
        profile.is_active = True
        self.session.commit()
        return profile

    def has_active_pipeline_run(self) -> bool:
        return (
            self.session.query(PipelineRun.id)
            .filter(PipelineRun.status.in_(("queued", "running")))
            .first()
            is not None
        )

    def create_pipeline_run(
        self,
        *,
        trigger_source: str,
        requested_hours: int,
        requested_top_n: int | None,
        profile_slug: str,
        send_email: bool,
        status: str = "queued",
    ) -> PipelineRun:
        pipeline_run = PipelineRun(
            id=str(uuid4()),
            trigger_source=trigger_source,
            requested_hours=requested_hours,
            requested_top_n=requested_top_n,
            profile_slug=profile_slug,
            send_email=send_email,
            status=status,
            scraping_summary={},
            processing_summary={},
            digest_summary={},
            email_summary={},
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(pipeline_run)
        self.session.commit()
        return pipeline_run

    def get_pipeline_run(self, run_id: str) -> Optional[PipelineRun]:
        return self.session.query(PipelineRun).filter_by(id=run_id).first()

    def mark_pipeline_run_running(self, run_id: str) -> Optional[PipelineRun]:
        pipeline_run = self.get_pipeline_run(run_id)
        if pipeline_run is None:
            return None

        pipeline_run.status = "running"
        if pipeline_run.started_at is None:
            pipeline_run.started_at = datetime.now(timezone.utc)
        self.session.commit()
        return pipeline_run

    def update_pipeline_run_progress(
        self,
        run_id: str,
        *,
        scraping_summary: Dict[str, Any] | None = None,
        processing_summary: Dict[str, Any] | None = None,
        digest_summary: Dict[str, Any] | None = None,
        email_summary: Dict[str, Any] | None = None,
    ) -> Optional[PipelineRun]:
        pipeline_run = self.get_pipeline_run(run_id)
        if pipeline_run is None:
            return None

        if scraping_summary is not None:
            pipeline_run.scraping_summary = scraping_summary
        if processing_summary is not None:
            pipeline_run.processing_summary = processing_summary
        if digest_summary is not None:
            pipeline_run.digest_summary = digest_summary
        if email_summary is not None:
            pipeline_run.email_summary = email_summary

        self.session.commit()
        return pipeline_run

    def complete_pipeline_run(
        self,
        run_id: str,
        *,
        scraping_summary: Dict[str, Any],
        processing_summary: Dict[str, Any],
        digest_summary: Dict[str, Any],
        email_summary: Dict[str, Any],
    ) -> Optional[PipelineRun]:
        pipeline_run = self.get_pipeline_run(run_id)
        if pipeline_run is None:
            return None

        ended_at = datetime.now(timezone.utc)
        started_at = self._coerce_datetime(pipeline_run.started_at) or ended_at
        pipeline_run.status = "completed"
        pipeline_run.error_message = None
        pipeline_run.scraping_summary = scraping_summary
        pipeline_run.processing_summary = processing_summary
        pipeline_run.digest_summary = digest_summary
        pipeline_run.email_summary = email_summary
        pipeline_run.ended_at = ended_at
        pipeline_run.duration_seconds = (ended_at - started_at).total_seconds()
        self.session.commit()
        return pipeline_run

    def fail_pipeline_run(
        self,
        run_id: str,
        *,
        error_message: str,
        scraping_summary: Dict[str, Any] | None = None,
        processing_summary: Dict[str, Any] | None = None,
        digest_summary: Dict[str, Any] | None = None,
        email_summary: Dict[str, Any] | None = None,
    ) -> Optional[PipelineRun]:
        pipeline_run = self.get_pipeline_run(run_id)
        if pipeline_run is None:
            return None

        ended_at = datetime.now(timezone.utc)
        started_at = self._coerce_datetime(pipeline_run.started_at) or ended_at
        pipeline_run.status = "failed"
        pipeline_run.error_message = error_message
        if scraping_summary is not None:
            pipeline_run.scraping_summary = scraping_summary
        if processing_summary is not None:
            pipeline_run.processing_summary = processing_summary
        if digest_summary is not None:
            pipeline_run.digest_summary = digest_summary
        if email_summary is not None:
            pipeline_run.email_summary = email_summary
        pipeline_run.ended_at = ended_at
        pipeline_run.duration_seconds = (ended_at - started_at).total_seconds()
        self.session.commit()
        return pipeline_run

    def list_pipeline_runs(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        query = self.session.query(PipelineRun).order_by(PipelineRun.started_at.desc(), PipelineRun.id)
        total = query.count()
        rows = query.offset(offset).limit(limit).all()
        return {
            "items": [self._serialize_pipeline_run(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_pipeline_run_detail(self, run_id: str) -> Optional[Dict[str, Any]]:
        pipeline_run = self.get_pipeline_run(run_id)
        if pipeline_run is None:
            return None
        return self._serialize_pipeline_run(pipeline_run)

    def create_newsletter_run(
        self,
        *,
        pipeline_run_id: str | None,
        profile_slug: str,
        window_hours: int,
        resolved_top_n: int,
        subject: str,
        greeting: str,
        introduction: str,
        sent: bool,
        article_count: int,
        payload_json: Dict[str, Any],
    ) -> NewsletterRun:
        newsletter_run = NewsletterRun(
            id=str(uuid4()),
            pipeline_run_id=pipeline_run_id,
            profile_slug=profile_slug,
            window_hours=window_hours,
            resolved_top_n=resolved_top_n,
            subject=subject,
            greeting=greeting,
            introduction=introduction,
            sent=sent,
            article_count=article_count,
            payload_json=payload_json,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(newsletter_run)
        self.session.commit()
        return newsletter_run

    def mark_newsletter_run_sent(self, newsletter_run_id: str, sent: bool = True) -> Optional[NewsletterRun]:
        newsletter_run = self.session.query(NewsletterRun).filter_by(id=newsletter_run_id).first()
        if newsletter_run is None:
            return None

        newsletter_run.sent = sent
        self.session.commit()
        return newsletter_run

    def list_newsletter_runs(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        query = self.session.query(NewsletterRun).order_by(NewsletterRun.created_at.desc(), NewsletterRun.id)
        total = query.count()
        rows = query.offset(offset).limit(limit).all()
        return {
            "items": [self._serialize_newsletter_run(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_newsletter_run_detail(self, newsletter_run_id: str) -> Optional[Dict[str, Any]]:
        newsletter_run = self.session.query(NewsletterRun).filter_by(id=newsletter_run_id).first()
        if newsletter_run is None:
            return None
        return self._serialize_newsletter_run(newsletter_run)

    @staticmethod
    def _build_normalized_source_item(
        *,
        source_type: str,
        source_id: str,
        url: str,
        raw_title: str,
        raw_summary: str,
        cleaned_content: str,
        published_at: datetime,
        content_richness: str,
        content_source_type: str,
    ) -> NormalizedSourceItem:
        return NormalizedSourceItem(
            source_type=source_type,
            source_id=source_id,
            url=url,
            raw_title=raw_title,
            raw_summary=raw_summary or "",
            cleaned_content=cleaned_content,
            published_at=published_at,
            content_length=len(cleaned_content),
            content_richness=content_richness,
            content_source_type=content_source_type,
        )

    @staticmethod
    def _build_story_digest_source(
        *,
        source_type: str,
        source_id: str,
        url: str,
        raw_title: str,
        cleaned_content: str,
        published_at: datetime,
        content_richness: str,
        content_source_type: str,
        similarity_to_primary: float | None = None,
        is_primary: bool = False,
    ) -> StoryDigestSource:
        return StoryDigestSource(
            source_type=source_type,
            source_id=source_id,
            url=url,
            raw_title=raw_title,
            cleaned_content=cleaned_content,
            published_at=published_at,
            content_richness=content_richness,
            content_source_type=content_source_type,
            similarity_to_primary=similarity_to_primary,
            is_primary=is_primary,
        )

    @staticmethod
    def _normalize_datetime(value: datetime) -> float:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()

    @staticmethod
    def _coerce_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _matches_search(title: str, query: str | None) -> bool:
        if not query:
            return True
        return query.lower() in title.lower()

    @staticmethod
    def _paginate_items(items: List[Dict[str, Any]], limit: int, offset: int) -> Dict[str, Any]:
        total = len(items)
        paged_items = items[offset : offset + limit]
        return {
            "items": paged_items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _serialize_pipeline_run(self, run: PipelineRun) -> Dict[str, Any]:
        return {
            "id": run.id,
            "trigger_source": run.trigger_source,
            "requested_hours": run.requested_hours,
            "requested_top_n": run.requested_top_n,
            "profile_slug": run.profile_slug,
            "send_email": run.send_email,
            "status": run.status,
            "error_message": run.error_message,
            "scraping_summary": run.scraping_summary or {},
            "processing_summary": run.processing_summary or {},
            "digest_summary": run.digest_summary or {},
            "email_summary": run.email_summary or {},
            "started_at": self._coerce_datetime(run.started_at),
            "ended_at": self._coerce_datetime(run.ended_at),
            "duration_seconds": run.duration_seconds,
        }

    def _serialize_newsletter_run(self, run: NewsletterRun) -> Dict[str, Any]:
        return {
            "id": run.id,
            "pipeline_run_id": run.pipeline_run_id,
            "profile_slug": run.profile_slug,
            "window_hours": run.window_hours,
            "resolved_top_n": run.resolved_top_n,
            "subject": run.subject,
            "greeting": run.greeting,
            "introduction": run.introduction,
            "sent": run.sent,
            "article_count": run.article_count,
            "payload_json": run.payload_json,
            "created_at": self._coerce_datetime(run.created_at),
        }

    def _serialize_source_archive_item(
        self,
        *,
        source_type: str,
        source_id: str,
        title: str,
        url: str,
        published_at: datetime,
        content_richness: str,
        content_source_type: str,
        enrichment_stage: str,
        enrichment_status: str,
        failure_reason: str | None,
        cleaned_content: str | None,
        description: str | None,
        transcript: str | None = None,
        markdown: str | None = None,
    ) -> Dict[str, Any]:
        return {
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "url": url,
            "published_at": self._coerce_datetime(published_at),
            "content_richness": content_richness,
            "content_source_type": content_source_type,
            "enrichment_stage": enrichment_stage,
            "enrichment_status": enrichment_status,
            "failure_reason": failure_reason,
            "cleaned_content": cleaned_content,
            "description": description,
            "transcript": transcript,
            "markdown": markdown,
        }

    def _collect_normalized_source_items(
        self,
        *,
        hours: Optional[int] = None,
    ) -> List[NormalizedSourceItem]:
        articles: List[NormalizedSourceItem] = []
        cutoff_time = None
        if hours is not None:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        youtube_query = self.session.query(YouTubeVideo).filter(
            YouTubeVideo.cleaned_content.isnot(None),
            YouTubeVideo.cleaned_content != "",
        )
        if cutoff_time is not None:
            youtube_query = youtube_query.filter(YouTubeVideo.published_at >= cutoff_time)

        for video in youtube_query.all():
            articles.append(
                self._build_normalized_source_item(
                    source_type="youtube",
                    source_id=video.video_id,
                    url=video.url,
                    raw_title=video.title,
                    raw_summary=video.description or "",
                    cleaned_content=video.cleaned_content,
                    published_at=video.published_at,
                    content_richness=video.content_richness,
                    content_source_type=video.content_source_type,
                )
            )

        openai_query = self.session.query(OpenAIArticle).filter(
            OpenAIArticle.cleaned_content.isnot(None),
            OpenAIArticle.cleaned_content != "",
        )
        if cutoff_time is not None:
            openai_query = openai_query.filter(OpenAIArticle.published_at >= cutoff_time)

        for article in openai_query.all():
            articles.append(
                self._build_normalized_source_item(
                    source_type="openai",
                    source_id=article.guid,
                    url=article.url or "",
                    raw_title=article.title,
                    raw_summary=article.description or "",
                    cleaned_content=article.cleaned_content,
                    published_at=article.published_at,
                    content_richness=article.content_richness,
                    content_source_type=article.content_source_type,
                )
            )

        anthropic_query = self.session.query(AnthropicArticle).filter(
            AnthropicArticle.cleaned_content.isnot(None),
            AnthropicArticle.cleaned_content != "",
        )
        if cutoff_time is not None:
            anthropic_query = anthropic_query.filter(AnthropicArticle.published_at >= cutoff_time)

        for article in anthropic_query.all():
            articles.append(
                self._build_normalized_source_item(
                    source_type="anthropic",
                    source_id=article.guid,
                    url=article.url,
                    raw_title=article.title,
                    raw_summary=article.description or "",
                    cleaned_content=article.cleaned_content,
                    published_at=article.published_at,
                    content_richness=article.content_richness,
                    content_source_type=article.content_source_type,
                )
            )

        articles.sort(
            key=lambda item: self._normalize_datetime(item.published_at),
            reverse=True,
        )
        return articles

    def create_youtube_video(
        self,
        video_id: str,
        title: str,
        url: str,
        channel_id: str,
        published_at: datetime,
        description: str = "",
        transcript: Optional[str] = None,
    ) -> Optional[YouTubeVideo]:
        existing = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if existing:
            return None

        normalized = select_normalized_content(description=description, transcript=transcript)
        transcript_text = clean_transcript_text(transcript)

        video = YouTubeVideo(
            video_id=video_id,
            title=title,
            url=url,
            channel_id=channel_id,
            published_at=published_at,
            description=description,
            transcript=transcript,
            cleaned_content=normalized.cleaned_content,
            transcript_status="completed" if transcript else "pending",
            transcript_length=len(transcript_text) if transcript_text else None,
            transcript_failure_reason=None,
            content_richness=normalized.content_richness,
            content_source_type=normalized.content_source_type,
        )
        self.session.add(video)
        self.session.commit()
        return video

    def create_openai_article(
        self,
        guid: str,
        title: str,
        url: str,
        published_at: datetime,
        description: str = "",
        category: Optional[str] = None,
    ) -> Optional[OpenAIArticle]:
        existing = self.session.query(OpenAIArticle).filter_by(guid=guid).first()
        if existing:
            return None

        normalized = select_normalized_content(description=description)

        article = OpenAIArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            cleaned_content=normalized.cleaned_content,
            category=category,
            content_length=normalized.content_length,
            content_richness=normalized.content_richness,
            content_source_type=normalized.content_source_type,
        )
        self.session.add(article)
        self.session.commit()
        return article

    def create_anthropic_article(
        self,
        guid: str,
        title: str,
        url: str,
        published_at: datetime,
        description: str = "",
        category: Optional[str] = None,
    ) -> Optional[AnthropicArticle]:
        existing = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if existing:
            return None

        normalized = select_normalized_content(description=description)

        article = AnthropicArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            cleaned_content=normalized.cleaned_content,
            category=category,
            markdown_status="pending",
            markdown_length=None,
            markdown_failure_reason=None,
            content_richness=normalized.content_richness,
            content_source_type=normalized.content_source_type,
        )
        self.session.add(article)
        self.session.commit()
        return article

    def bulk_create_youtube_videos(self, videos: List[dict]) -> int:
        if not videos:
            return 0

        incoming_ids = {v["video_id"] for v in videos}
        existing_ids = {
            row[0]
            for row in self.session.query(YouTubeVideo.video_id)
            .filter(YouTubeVideo.video_id.in_(incoming_ids))
            .all()
        }

        new_videos = []
        for video_payload in videos:
            if video_payload["video_id"] in existing_ids:
                continue

            normalized = select_normalized_content(
                description=video_payload.get("description"),
                transcript=video_payload.get("transcript"),
            )
            transcript_text = clean_transcript_text(video_payload.get("transcript"))
            new_videos.append(
                YouTubeVideo(
                    video_id=video_payload["video_id"],
                    title=video_payload["title"],
                    url=video_payload["url"],
                    channel_id=video_payload.get("channel_id", ""),
                    published_at=video_payload["published_at"],
                    description=video_payload.get("description", ""),
                    transcript=video_payload.get("transcript"),
                    cleaned_content=normalized.cleaned_content,
                    transcript_status="completed" if video_payload.get("transcript") else "pending",
                    transcript_length=len(transcript_text) if transcript_text else None,
                    transcript_failure_reason=None,
                    content_richness=normalized.content_richness,
                    content_source_type=normalized.content_source_type,
                )
            )

        if new_videos:
            self.session.add_all(new_videos)
            self.session.commit()

        return len(new_videos)

    def bulk_create_openai_articles(self, articles: List[dict]) -> int:
        if not articles:
            return 0

        incoming_ids = {a["guid"] for a in articles}
        existing_ids = {
            row[0]
            for row in self.session.query(OpenAIArticle.guid)
            .filter(OpenAIArticle.guid.in_(incoming_ids))
            .all()
        }

        new_articles = []
        for article_payload in articles:
            if article_payload["guid"] in existing_ids:
                continue

            normalized = select_normalized_content(description=article_payload.get("description"))
            new_articles.append(
                OpenAIArticle(
                    guid=article_payload["guid"],
                    title=article_payload["title"],
                    url=article_payload["url"],
                    published_at=article_payload["published_at"],
                    description=article_payload.get("description", ""),
                    cleaned_content=normalized.cleaned_content,
                    category=article_payload.get("category"),
                    content_length=normalized.content_length,
                    content_richness=normalized.content_richness,
                    content_source_type=normalized.content_source_type,
                )
            )

        if new_articles:
            self.session.add_all(new_articles)
            self.session.commit()

        return len(new_articles)

    def bulk_create_anthropic_articles(self, articles: List[dict]) -> int:
        if not articles:
            return 0

        incoming_ids = {a["guid"] for a in articles}
        existing_ids = {
            row[0]
            for row in self.session.query(AnthropicArticle.guid)
            .filter(AnthropicArticle.guid.in_(incoming_ids))
            .all()
        }

        new_articles = []
        for article_payload in articles:
            if article_payload["guid"] in existing_ids:
                continue

            normalized = select_normalized_content(description=article_payload.get("description"))
            new_articles.append(
                AnthropicArticle(
                    guid=article_payload["guid"],
                    title=article_payload["title"],
                    url=article_payload["url"],
                    published_at=article_payload["published_at"],
                    description=article_payload.get("description", ""),
                    cleaned_content=normalized.cleaned_content,
                    category=article_payload.get("category"),
                    markdown_status="pending",
                    markdown_length=None,
                    markdown_failure_reason=None,
                    content_richness=normalized.content_richness,
                    content_source_type=normalized.content_source_type,
                )
            )

        if new_articles:
            self.session.add_all(new_articles)
            self.session.commit()

        return len(new_articles)

    def get_recent_normalized_source_items(self, hours: int) -> List[NormalizedSourceItem]:
        return self._collect_normalized_source_items(hours=hours)

    def get_anthropic_articles_pending_markdown(
        self, limit: Optional[int] = None
    ) -> List[AnthropicArticle]:
        query = self.session.query(AnthropicArticle).filter(
            AnthropicArticle.markdown_status == "pending"
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def mark_anthropic_markdown_completed(self, guid: str, markdown: str) -> bool:
        article = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if not article:
            return False

        normalized = select_normalized_content(description=article.description, markdown=markdown)
        markdown_text = clean_markdown_text(markdown)

        article.markdown = markdown
        article.cleaned_content = normalized.cleaned_content
        article.markdown_status = "completed"
        article.markdown_length = len(markdown_text) if markdown_text else None
        article.markdown_failure_reason = None
        article.content_richness = normalized.content_richness
        article.content_source_type = normalized.content_source_type
        self.session.commit()
        return True

    def mark_anthropic_markdown_unavailable(
        self, guid: str, reason: str = "no_markdown_extracted"
    ) -> bool:
        article = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if not article:
            return False

        normalized = select_normalized_content(description=article.description)

        article.markdown = None
        article.cleaned_content = normalized.cleaned_content
        article.markdown_status = "unavailable"
        article.markdown_length = None
        article.markdown_failure_reason = reason
        article.content_richness = normalized.content_richness
        article.content_source_type = normalized.content_source_type
        self.session.commit()
        return True

    def mark_anthropic_markdown_failed(self, guid: str, reason: str) -> bool:
        article = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if not article:
            return False

        normalized = select_normalized_content(description=article.description)

        article.cleaned_content = normalized.cleaned_content
        article.markdown_status = "failed"
        article.markdown_length = None
        article.markdown_failure_reason = reason
        article.content_richness = normalized.content_richness
        article.content_source_type = normalized.content_source_type
        self.session.commit()
        return True

    def get_youtube_videos_pending_transcript(
        self, limit: Optional[int] = None
    ) -> List[YouTubeVideo]:
        query = self.session.query(YouTubeVideo).filter(YouTubeVideo.transcript_status == "pending")
        if limit:
            query = query.limit(limit)
        return query.all()

    def mark_youtube_transcript_completed(self, video_id: str, transcript: str) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if not video:
            return False

        normalized = select_normalized_content(description=video.description, transcript=transcript)
        transcript_text = clean_transcript_text(transcript)

        video.transcript = transcript
        video.cleaned_content = normalized.cleaned_content
        video.transcript_status = "completed"
        video.transcript_length = len(transcript_text) if transcript_text else None
        video.transcript_failure_reason = None
        video.content_richness = normalized.content_richness
        video.content_source_type = normalized.content_source_type
        self.session.commit()
        return True

    def mark_youtube_transcript_unavailable(
        self, video_id: str, reason: str = "transcript_not_available"
    ) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if not video:
            return False

        normalized = select_normalized_content(description=video.description)

        video.transcript = None
        video.cleaned_content = normalized.cleaned_content
        video.transcript_status = "unavailable"
        video.transcript_length = None
        video.transcript_failure_reason = reason
        video.content_richness = normalized.content_richness
        video.content_source_type = normalized.content_source_type
        self.session.commit()
        return True

    def mark_youtube_transcript_failed(self, video_id: str, reason: str) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if not video:
            return False

        normalized = select_normalized_content(description=video.description)

        video.cleaned_content = normalized.cleaned_content
        video.transcript_status = "failed"
        video.transcript_length = None
        video.transcript_failure_reason = reason
        video.content_richness = normalized.content_richness
        video.content_source_type = normalized.content_source_type
        self.session.commit()
        return True

    def get_story_link_context(self, hours: int) -> Dict[str, Dict[str, Any]]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = (
            self.session.query(StorySourceLink, Story)
            .join(Story, Story.id == StorySourceLink.story_id)
            .filter(StorySourceLink.published_at >= cutoff_time)
            .all()
        )

        context: Dict[str, Dict[str, Any]] = {}
        for link, story in rows:
            context[build_source_key(link.source_type, link.source_id)] = {
                "story_id": link.story_id,
                "story_created_at": story.created_at,
            }
        return context

    def _get_story_source_links(
        self,
        story_ids: Sequence[str],
    ) -> Dict[str, List[StorySourceLink]]:
        if not story_ids:
            return {}

        links = (
            self.session.query(StorySourceLink)
            .filter(StorySourceLink.story_id.in_(story_ids))
            .all()
        )

        grouped_links: Dict[str, List[StorySourceLink]] = {}
        for link in links:
            grouped_links.setdefault(link.story_id, []).append(link)

        for story_id, story_links in grouped_links.items():
            grouped_links[story_id] = sorted(
                story_links,
                key=lambda link: (
                    not link.is_primary,
                    -(
                        link.similarity_to_primary
                        if link.similarity_to_primary is not None
                        else -1.0
                    ),
                    -self._normalize_datetime(link.published_at),
                    build_source_key(link.source_type, link.source_id),
                ),
            )

        return grouped_links

    def _get_story_digest_source_map(
        self,
        source_refs: Sequence[tuple[str, str]],
        link_context: Optional[Dict[str, StorySourceLink]] = None,
    ) -> Dict[str, StoryDigestSource]:
        source_map: Dict[str, StoryDigestSource] = {}
        refs_by_type: Dict[str, List[str]] = {"youtube": [], "openai": [], "anthropic": []}
        for source_type, source_id in source_refs:
            refs_by_type.setdefault(source_type, []).append(source_id)

        if refs_by_type["youtube"]:
            for video in (
                self.session.query(YouTubeVideo)
                .filter(YouTubeVideo.video_id.in_(refs_by_type["youtube"]))
                .all()
            ):
                source_key = build_source_key("youtube", video.video_id)
                link = link_context.get(source_key) if link_context else None
                source_map[source_key] = self._build_story_digest_source(
                    source_type="youtube",
                    source_id=video.video_id,
                    url=video.url,
                    raw_title=video.title,
                    cleaned_content=video.cleaned_content or "",
                    published_at=video.published_at,
                    content_richness=video.content_richness,
                    content_source_type=video.content_source_type,
                    similarity_to_primary=link.similarity_to_primary if link else None,
                    is_primary=link.is_primary if link else False,
                )

        if refs_by_type["openai"]:
            for article in (
                self.session.query(OpenAIArticle)
                .filter(OpenAIArticle.guid.in_(refs_by_type["openai"]))
                .all()
            ):
                source_key = build_source_key("openai", article.guid)
                link = link_context.get(source_key) if link_context else None
                source_map[source_key] = self._build_story_digest_source(
                    source_type="openai",
                    source_id=article.guid,
                    url=article.url or "",
                    raw_title=article.title,
                    cleaned_content=article.cleaned_content or "",
                    published_at=article.published_at,
                    content_richness=article.content_richness,
                    content_source_type=article.content_source_type,
                    similarity_to_primary=link.similarity_to_primary if link else None,
                    is_primary=link.is_primary if link else False,
                )

        if refs_by_type["anthropic"]:
            for article in (
                self.session.query(AnthropicArticle)
                .filter(AnthropicArticle.guid.in_(refs_by_type["anthropic"]))
                .all()
            ):
                source_key = build_source_key("anthropic", article.guid)
                link = link_context.get(source_key) if link_context else None
                source_map[source_key] = self._build_story_digest_source(
                    source_type="anthropic",
                    source_id=article.guid,
                    url=article.url,
                    raw_title=article.title,
                    cleaned_content=article.cleaned_content or "",
                    published_at=article.published_at,
                    content_richness=article.content_richness,
                    content_source_type=article.content_source_type,
                    similarity_to_primary=link.similarity_to_primary if link else None,
                    is_primary=link.is_primary if link else False,
                )

        return source_map

    def upsert_story_clusters(self, story_payloads: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        if not story_payloads:
            return {
                "stories_created": 0,
                "stories_updated": 0,
                "links_created": 0,
                "links_updated": 0,
            }

        flattened_links = [
            {**link, "story_id": payload["story_id"]}
            for payload in story_payloads
            for link in payload["links"]
        ]
        source_refs = [(link["source_type"], link["source_id"]) for link in flattened_links]

        existing_links: List[StorySourceLink] = []
        if source_refs:
            existing_links = (
                self.session.query(StorySourceLink)
                .filter(
                    tuple_(
                        StorySourceLink.source_type,
                        StorySourceLink.source_id,
                    ).in_(source_refs)
                )
                .all()
            )

        existing_links_by_key = {
            build_source_key(link.source_type, link.source_id): link for link in existing_links
        }
        orphan_candidate_story_ids = {link.story_id for link in existing_links}
        source_map = self._get_story_digest_source_map(source_refs)

        for link in existing_links:
            self.session.delete(link)
        if existing_links:
            self.session.flush()

        story_ids = [payload["story_id"] for payload in story_payloads]
        existing_stories = {
            story.id: story
            for story in self.session.query(Story).filter(Story.id.in_(story_ids)).all()
        }

        stories_created = 0
        stories_updated = 0
        for payload in story_payloads:
            story = existing_stories.get(payload["story_id"])
            member_sources = [
                source_map[build_source_key(link["source_type"], link["source_id"])]
                for link in payload["links"]
                if build_source_key(link["source_type"], link["source_id"]) in source_map
            ]
            digest_input_hash = build_story_digest_input_hash(
                payload["representative_source_type"],
                payload["representative_source_id"],
                member_sources,
            ) if member_sources else None

            if story is None:
                story = Story(id=payload["story_id"])
                self.session.add(story)
                stories_created += 1
                story.story_digest_status = "pending"
                story.story_digest_failure_reason = None
            else:
                stories_updated += 1
                if story.story_digest_input_hash != digest_input_hash:
                    story.story_digest_status = "pending"
                    story.story_digest_failure_reason = None

            story.title = payload["title"]
            story.representative_source_type = payload["representative_source_type"]
            story.representative_source_id = payload["representative_source_id"]
            story.representative_published_at = payload["representative_published_at"]
            story.cluster_version = payload["cluster_version"]
            story.window_start = payload["window_start"]
            story.window_end = payload["window_end"]
            story.story_digest_input_hash = digest_input_hash

        links_created = 0
        links_updated = 0
        for payload in story_payloads:
            for link_payload in payload["links"]:
                source_key = build_source_key(
                    link_payload["source_type"],
                    link_payload["source_id"],
                )
                if source_key in existing_links_by_key:
                    links_updated += 1
                else:
                    links_created += 1

                self.session.add(
                    StorySourceLink(
                        story_id=payload["story_id"],
                        source_type=link_payload["source_type"],
                        source_id=link_payload["source_id"],
                        published_at=link_payload["published_at"],
                        similarity_to_primary=link_payload["similarity_to_primary"],
                        is_primary=link_payload["is_primary"],
                    )
                )

        self.session.flush()

        for story_id in set(story_ids):
            story = self.session.query(Story).filter_by(id=story_id).first()
            if story is not None:
                story.source_count = (
                    self.session.query(StorySourceLink)
                    .filter(StorySourceLink.story_id == story_id)
                    .count()
                )

        self.session.commit()

        remaining_links_by_story = {
            row[0]
            for row in self.session.query(StorySourceLink.story_id)
            .filter(StorySourceLink.story_id.in_(orphan_candidate_story_ids))
            .all()
        }
        orphan_story_ids = orphan_candidate_story_ids - remaining_links_by_story
        if orphan_story_ids:
            (
                self.session.query(StoryDigest)
                .filter(StoryDigest.story_id.in_(orphan_story_ids))
                .delete(synchronize_session=False)
            )
            (
                self.session.query(Story)
                .filter(Story.id.in_(orphan_story_ids))
                .delete(synchronize_session=False)
            )
            self.session.commit()

        return {
            "stories_created": stories_created,
            "stories_updated": stories_updated,
            "links_created": links_created,
            "links_updated": links_updated,
        }

    def get_stories_pending_story_digest(
        self,
        limit: Optional[int] = None,
    ) -> List[StoryDigestJob]:
        query = (
            self.session.query(Story)
            .filter(Story.story_digest_status == "pending")
            .order_by(Story.representative_published_at.desc())
        )
        if limit:
            query = query.limit(limit)

        stories = query.all()
        if not stories:
            return []

        story_ids = [story.id for story in stories]
        links_by_story = self._get_story_source_links(story_ids)
        source_refs = [
            (link.source_type, link.source_id)
            for story_links in links_by_story.values()
            for link in story_links
        ]
        link_map = {
            build_source_key(link.source_type, link.source_id): link
            for story_links in links_by_story.values()
            for link in story_links
        }
        source_map = self._get_story_digest_source_map(source_refs, link_map)

        jobs: List[StoryDigestJob] = []
        for story in stories:
            story_links = links_by_story.get(story.id, [])
            members = [
                source_map[build_source_key(link.source_type, link.source_id)]
                for link in story_links
                if build_source_key(link.source_type, link.source_id) in source_map
            ]
            if not members:
                continue

            input_hash = story.story_digest_input_hash or build_story_digest_input_hash(
                story.representative_source_type,
                story.representative_source_id,
                members,
            )
            jobs.append(
                StoryDigestJob(
                    story_id=story.id,
                    story_title=story.title,
                    representative_source_type=story.representative_source_type,
                    representative_source_id=story.representative_source_id,
                    source_count=story.source_count,
                    story_digest_input_hash=input_hash,
                    members=members,
                )
            )

        return jobs

    def get_current_story_digest(self, story_id: str) -> Optional[StoryDigest]:
        row = (
            self.session.query(StoryDigest, Story)
            .join(Story, Story.id == StoryDigest.story_id)
            .filter(StoryDigest.story_id == story_id)
            .first()
        )
        if not row:
            return None

        story_digest, story = row
        if story_digest.generated_input_hash != story.story_digest_input_hash:
            return None
        return story_digest

    def upsert_story_digest(
        self,
        *,
        story_id: str,
        title: str,
        summary: str,
        why_it_matters: str,
        disagreement_notes: Optional[str],
        synthesis_mode: str,
        available_source_count: int,
        used_source_count: int,
        generated_input_hash: str,
    ) -> StoryDigest:
        story = self.session.query(Story).filter_by(id=story_id).first()
        if story is None:
            raise ValueError(f"Story {story_id} does not exist")

        story_digest = self.session.query(StoryDigest).filter_by(story_id=story_id).first()
        if story_digest is None:
            story_digest = StoryDigest(story_id=story_id)
            self.session.add(story_digest)

        story_digest.title = title
        story_digest.summary = summary
        story_digest.why_it_matters = why_it_matters
        story_digest.disagreement_notes = disagreement_notes
        story_digest.synthesis_mode = synthesis_mode
        story_digest.available_source_count = available_source_count
        story_digest.used_source_count = used_source_count
        story_digest.generated_input_hash = generated_input_hash

        story.story_digest_status = "completed"
        story.story_digest_failure_reason = None
        story.story_digest_last_processed_at = datetime.now(timezone.utc)

        self.session.commit()
        return story_digest

    def mark_story_digest_failed(self, story_id: str, reason: str) -> bool:
        story = self.session.query(Story).filter_by(id=story_id).first()
        if story is None:
            return False

        story.story_digest_status = "failed"
        story.story_digest_failure_reason = reason
        story.story_digest_last_processed_at = datetime.now(timezone.utc)
        self.session.commit()
        return True

    def get_recent_story_digest_candidates(self, hours: int = 24) -> List[Dict[str, Any]]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        rows = (
            self.session.query(Story, StoryDigest)
            .join(StoryDigest, StoryDigest.story_id == Story.id)
            .filter(Story.representative_published_at >= cutoff_time)
            .filter(Story.story_digest_status == "completed")
            .filter(StoryDigest.generated_input_hash == Story.story_digest_input_hash)
            .order_by(Story.representative_published_at.desc())
            .all()
        )
        if not rows:
            return []

        story_ids = [story.id for story, _ in rows]
        links_by_story = self._get_story_source_links(story_ids)
        source_refs = [
            (link.source_type, link.source_id)
            for story_links in links_by_story.values()
            for link in story_links
        ]
        link_map = {
            build_source_key(link.source_type, link.source_id): link
            for story_links in links_by_story.values()
            for link in story_links
        }
        source_map = self._get_story_digest_source_map(source_refs, link_map)

        candidates: List[Dict[str, Any]] = []
        for story, story_digest in rows:
            story_links = links_by_story.get(story.id, [])
            source_types: List[str] = []
            for link in story_links:
                if link.source_type not in source_types:
                    source_types.append(link.source_type)

            representative = source_map.get(
                build_source_key(
                    story.representative_source_type,
                    story.representative_source_id,
                )
            )
            if representative is None:
                continue

            created_at = (
                story_digest.updated_at
                or story_digest.created_at
                or story.representative_published_at
            )
            candidates.append(
                {
                    "id": f"story:{story.id}",
                    "story_id": story.id,
                    "title": story_digest.title,
                    "summary": story_digest.summary,
                    "why_it_matters": story_digest.why_it_matters,
                    "disagreement_notes": story_digest.disagreement_notes,
                    "url": representative.url,
                    "article_type": "story",
                    "story_source_count": story.source_count,
                    "source_types": source_types,
                    "synthesis_mode": story_digest.synthesis_mode,
                    "source_attribution_line": format_source_attribution_line(
                        source_types=source_types,
                        available_source_count=story_digest.available_source_count,
                        synthesis_mode=story_digest.synthesis_mode,
                    ),
                    "created_at": created_at,
                }
            )

        candidates.sort(
            key=lambda candidate: self._normalize_datetime(candidate["created_at"]),
            reverse=True,
        )
        return candidates

    def list_source_archive(
        self,
        *,
        source_type: str | None = None,
        status: str | None = None,
        q: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []

        if source_type in (None, "youtube"):
            query = self.session.query(YouTubeVideo)
            if start_at is not None:
                query = query.filter(YouTubeVideo.published_at >= start_at)
            if end_at is not None:
                query = query.filter(YouTubeVideo.published_at <= end_at)
            if status:
                query = query.filter(YouTubeVideo.transcript_status == status)

            for video in query.all():
                if not self._matches_search(video.title, q):
                    continue
                items.append(
                    self._serialize_source_archive_item(
                        source_type="youtube",
                        source_id=video.video_id,
                        title=video.title,
                        url=video.url,
                        published_at=video.published_at,
                        content_richness=video.content_richness,
                        content_source_type=video.content_source_type,
                        enrichment_stage="transcript",
                        enrichment_status=video.transcript_status,
                        failure_reason=video.transcript_failure_reason,
                        cleaned_content=video.cleaned_content,
                        description=video.description,
                        transcript=video.transcript,
                    )
                )

        if source_type in (None, "openai"):
            if status in (None, "not_applicable"):
                query = self.session.query(OpenAIArticle)
                if start_at is not None:
                    query = query.filter(OpenAIArticle.published_at >= start_at)
                if end_at is not None:
                    query = query.filter(OpenAIArticle.published_at <= end_at)

                for article in query.all():
                    if not self._matches_search(article.title, q):
                        continue
                    items.append(
                        self._serialize_source_archive_item(
                            source_type="openai",
                            source_id=article.guid,
                            title=article.title,
                            url=article.url or "",
                            published_at=article.published_at,
                            content_richness=article.content_richness,
                            content_source_type=article.content_source_type,
                            enrichment_stage="none",
                            enrichment_status="not_applicable",
                            failure_reason=None,
                            cleaned_content=article.cleaned_content,
                            description=article.description,
                        )
                    )

        if source_type in (None, "anthropic"):
            query = self.session.query(AnthropicArticle)
            if start_at is not None:
                query = query.filter(AnthropicArticle.published_at >= start_at)
            if end_at is not None:
                query = query.filter(AnthropicArticle.published_at <= end_at)
            if status:
                query = query.filter(AnthropicArticle.markdown_status == status)

            for article in query.all():
                if not self._matches_search(article.title, q):
                    continue
                items.append(
                    self._serialize_source_archive_item(
                        source_type="anthropic",
                        source_id=article.guid,
                        title=article.title,
                        url=article.url,
                        published_at=article.published_at,
                        content_richness=article.content_richness,
                        content_source_type=article.content_source_type,
                        enrichment_stage="markdown",
                        enrichment_status=article.markdown_status,
                        failure_reason=article.markdown_failure_reason,
                        cleaned_content=article.cleaned_content,
                        description=article.description,
                        markdown=article.markdown,
                    )
                )

        items.sort(key=lambda item: self._normalize_datetime(item["published_at"]), reverse=True)
        return self._paginate_items(items, limit=limit, offset=offset)

    def get_source_archive_item(self, source_type: str, source_id: str) -> Optional[Dict[str, Any]]:
        if source_type == "youtube":
            video = self.session.query(YouTubeVideo).filter_by(video_id=source_id).first()
            if video is None:
                return None
            return self._serialize_source_archive_item(
                source_type="youtube",
                source_id=video.video_id,
                title=video.title,
                url=video.url,
                published_at=video.published_at,
                content_richness=video.content_richness,
                content_source_type=video.content_source_type,
                enrichment_stage="transcript",
                enrichment_status=video.transcript_status,
                failure_reason=video.transcript_failure_reason,
                cleaned_content=video.cleaned_content,
                description=video.description,
                transcript=video.transcript,
            )

        if source_type == "openai":
            article = self.session.query(OpenAIArticle).filter_by(guid=source_id).first()
            if article is None:
                return None
            return self._serialize_source_archive_item(
                source_type="openai",
                source_id=article.guid,
                title=article.title,
                url=article.url or "",
                published_at=article.published_at,
                content_richness=article.content_richness,
                content_source_type=article.content_source_type,
                enrichment_stage="none",
                enrichment_status="not_applicable",
                failure_reason=None,
                cleaned_content=article.cleaned_content,
                description=article.description,
            )

        if source_type == "anthropic":
            article = self.session.query(AnthropicArticle).filter_by(guid=source_id).first()
            if article is None:
                return None
            return self._serialize_source_archive_item(
                source_type="anthropic",
                source_id=article.guid,
                title=article.title,
                url=article.url,
                published_at=article.published_at,
                content_richness=article.content_richness,
                content_source_type=article.content_source_type,
                enrichment_stage="markdown",
                enrichment_status=article.markdown_status,
                failure_reason=article.markdown_failure_reason,
                cleaned_content=article.cleaned_content,
                description=article.description,
                markdown=article.markdown,
            )

        return None

    def list_story_archive(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        q: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        query = self.session.query(Story)
        if status:
            query = query.filter(Story.story_digest_status == status)
        if source_type:
            query = query.filter(Story.representative_source_type == source_type)
        if start_at is not None:
            query = query.filter(Story.representative_published_at >= start_at)
        if end_at is not None:
            query = query.filter(Story.representative_published_at <= end_at)

        stories = query.order_by(Story.representative_published_at.desc()).all()
        if q:
            stories = [story for story in stories if self._matches_search(story.title, q)]

        total = len(stories)
        paged_stories = stories[offset : offset + limit]
        if not paged_stories:
            return {"items": [], "total": total, "limit": limit, "offset": offset}

        story_ids = [story.id for story in paged_stories]
        links_by_story = self._get_story_source_links(story_ids)
        source_refs = [
            (link.source_type, link.source_id)
            for story_links in links_by_story.values()
            for link in story_links
        ]
        link_map = {
            build_source_key(link.source_type, link.source_id): link
            for story_links in links_by_story.values()
            for link in story_links
        }
        source_map = self._get_story_digest_source_map(source_refs, link_map)

        digest_rows = (
            self.session.query(StoryDigest, Story)
            .join(Story, Story.id == StoryDigest.story_id)
            .filter(StoryDigest.story_id.in_(story_ids))
            .all()
        )
        digest_map = {
            story_digest.story_id: story_digest
            for story_digest, story in digest_rows
            if story_digest.generated_input_hash == story.story_digest_input_hash
        }

        items: List[Dict[str, Any]] = []
        for story in paged_stories:
            story_links = links_by_story.get(story.id, [])
            current_digest = digest_map.get(story.id)
            source_types: List[str] = []
            for link in story_links:
                if link.source_type not in source_types:
                    source_types.append(link.source_type)

            representative = source_map.get(
                build_source_key(story.representative_source_type, story.representative_source_id)
            )
            items.append(
                {
                    "story_id": story.id,
                    "title": story.title,
                    "story_digest_status": story.story_digest_status,
                    "story_digest_failure_reason": story.story_digest_failure_reason,
                    "representative_source_type": story.representative_source_type,
                    "representative_source_id": story.representative_source_id,
                    "representative_url": representative.url if representative else "",
                    "representative_published_at": self._coerce_datetime(
                        story.representative_published_at
                    ),
                    "source_count": story.source_count,
                    "source_types": source_types,
                    "digest_title": current_digest.title if current_digest else None,
                    "digest_summary": current_digest.summary if current_digest else None,
                    "digest_why_it_matters": current_digest.why_it_matters if current_digest else None,
                }
            )

        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_story_archive_item(self, story_id: str) -> Optional[Dict[str, Any]]:
        story = self.session.query(Story).filter_by(id=story_id).first()
        if story is None:
            return None

        current_digest = self.get_current_story_digest(story_id)
        links_by_story = self._get_story_source_links([story_id])
        story_links = links_by_story.get(story_id, [])
        source_refs = [(link.source_type, link.source_id) for link in story_links]
        link_map = {
            build_source_key(link.source_type, link.source_id): link for link in story_links
        }
        source_map = self._get_story_digest_source_map(source_refs, link_map)

        sources: List[Dict[str, Any]] = []
        source_types: List[str] = []
        for link in story_links:
            if link.source_type not in source_types:
                source_types.append(link.source_type)

            source = source_map.get(build_source_key(link.source_type, link.source_id))
            if source is None:
                continue
            sources.append(
                {
                    "source_type": source.source_type,
                    "source_id": source.source_id,
                    "title": source.raw_title,
                    "url": source.url,
                    "published_at": self._coerce_datetime(source.published_at),
                    "content_richness": source.content_richness,
                    "content_source_type": source.content_source_type,
                    "similarity_to_primary": source.similarity_to_primary,
                    "is_primary": source.is_primary,
                }
            )

        representative = source_map.get(
            build_source_key(story.representative_source_type, story.representative_source_id)
        )
        return {
            "story_id": story.id,
            "title": story.title,
            "story_digest_status": story.story_digest_status,
            "story_digest_failure_reason": story.story_digest_failure_reason,
            "story_digest_last_processed_at": self._coerce_datetime(
                story.story_digest_last_processed_at
            ),
            "representative_source_type": story.representative_source_type,
            "representative_source_id": story.representative_source_id,
            "representative_url": representative.url if representative else "",
            "representative_published_at": self._coerce_datetime(story.representative_published_at),
            "source_count": story.source_count,
            "source_types": source_types,
            "digest": (
                {
                    "title": current_digest.title,
                    "summary": current_digest.summary,
                    "why_it_matters": current_digest.why_it_matters,
                    "disagreement_notes": current_digest.disagreement_notes,
                    "synthesis_mode": current_digest.synthesis_mode,
                    "available_source_count": current_digest.available_source_count,
                    "used_source_count": current_digest.used_source_count,
                    "generated_input_hash": current_digest.generated_input_hash,
                }
                if current_digest
                else None
            ),
            "sources": sources,
        }

    def get_failure_summary(self, hours: int = 168, limit: int = 20) -> Dict[str, Any]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        items: List[Dict[str, Any]] = []

        youtube_rows = (
            self.session.query(YouTubeVideo)
            .filter(YouTubeVideo.published_at >= cutoff_time)
            .filter(YouTubeVideo.transcript_status.in_(("failed", "unavailable")))
            .all()
        )
        anthropic_rows = (
            self.session.query(AnthropicArticle)
            .filter(AnthropicArticle.published_at >= cutoff_time)
            .filter(AnthropicArticle.markdown_status.in_(("failed", "unavailable")))
            .all()
        )
        story_rows = (
            self.session.query(Story)
            .filter(Story.representative_published_at >= cutoff_time)
            .filter(Story.story_digest_status == "failed")
            .all()
        )
        pipeline_rows = (
            self.session.query(PipelineRun)
            .filter(PipelineRun.started_at >= cutoff_time)
            .filter(PipelineRun.status == "failed")
            .all()
        )

        for video in youtube_rows:
            items.append(
                {
                    "kind": "source",
                    "category": "youtube_transcript",
                    "status": video.transcript_status,
                    "title": video.title,
                    "reference_id": video.video_id,
                    "source_type": "youtube",
                    "failure_reason": video.transcript_failure_reason,
                    "occurred_at": self._coerce_datetime(video.published_at),
                }
            )

        for article in anthropic_rows:
            items.append(
                {
                    "kind": "source",
                    "category": "anthropic_markdown",
                    "status": article.markdown_status,
                    "title": article.title,
                    "reference_id": article.guid,
                    "source_type": "anthropic",
                    "failure_reason": article.markdown_failure_reason,
                    "occurred_at": self._coerce_datetime(article.published_at),
                }
            )

        for story in story_rows:
            items.append(
                {
                    "kind": "story",
                    "category": "story_digest",
                    "status": story.story_digest_status,
                    "title": story.title,
                    "reference_id": story.id,
                    "source_type": story.representative_source_type,
                    "failure_reason": story.story_digest_failure_reason,
                    "occurred_at": self._coerce_datetime(story.representative_published_at),
                }
            )

        for run in pipeline_rows:
            items.append(
                {
                    "kind": "pipeline",
                    "category": "pipeline_run",
                    "status": run.status,
                    "title": f"{run.trigger_source} pipeline run",
                    "reference_id": run.id,
                    "source_type": run.trigger_source,
                    "failure_reason": run.error_message,
                    "occurred_at": self._coerce_datetime(run.started_at),
                }
            )

        items.sort(key=lambda item: self._normalize_datetime(item["occurred_at"]), reverse=True)
        summary = {
            "youtube_failed": sum(1 for row in youtube_rows if row.transcript_status == "failed"),
            "youtube_unavailable": sum(
                1 for row in youtube_rows if row.transcript_status == "unavailable"
            ),
            "anthropic_failed": sum(
                1 for row in anthropic_rows if row.markdown_status == "failed"
            ),
            "anthropic_unavailable": sum(
                1 for row in anthropic_rows if row.markdown_status == "unavailable"
            ),
            "story_digest_failed": len(story_rows),
            "pipeline_failed": len(pipeline_rows),
        }
        return {
            "summary": summary,
            "items": items[:limit],
            "hours": hours,
        }

    def get_dashboard_overview(self, hours: int = 24) -> Dict[str, Any]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        latest_pipeline = (
            self.session.query(PipelineRun)
            .order_by(PipelineRun.started_at.desc(), PipelineRun.id)
            .first()
        )
        latest_newsletter = (
            self.session.query(NewsletterRun)
            .order_by(NewsletterRun.created_at.desc(), NewsletterRun.id)
            .first()
        )

        source_counts = {
            "youtube": self.session.query(YouTubeVideo)
            .filter(YouTubeVideo.published_at >= cutoff_time)
            .count(),
            "openai": self.session.query(OpenAIArticle)
            .filter(OpenAIArticle.published_at >= cutoff_time)
            .count(),
            "anthropic": self.session.query(AnthropicArticle)
            .filter(AnthropicArticle.published_at >= cutoff_time)
            .count(),
        }
        story_rows = (
            self.session.query(Story).filter(Story.representative_published_at >= cutoff_time).all()
        )
        digest_counts = {
            "completed": sum(1 for story in story_rows if story.story_digest_status == "completed"),
            "pending": sum(1 for story in story_rows if story.story_digest_status == "pending"),
            "failed": sum(1 for story in story_rows if story.story_digest_status == "failed"),
        }
        story_counts = {
            "total": len(story_rows),
            "multi_source": sum(1 for story in story_rows if story.source_count > 1),
            "singleton": sum(1 for story in story_rows if story.source_count == 1),
        }

        return {
            "hours": hours,
            "source_counts": source_counts,
            "story_counts": story_counts,
            "digest_counts": digest_counts,
            "failure_summary": self.get_failure_summary(hours=max(hours, 168), limit=5),
            "latest_pipeline_run": (
                self._serialize_pipeline_run(latest_pipeline) if latest_pipeline else None
            ),
            "latest_newsletter_run": (
                self._serialize_newsletter_run(latest_newsletter) if latest_newsletter else None
            ),
        }
