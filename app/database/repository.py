from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.content_normalization import (
    NormalizedSourceItem,
    clean_markdown_text,
    clean_transcript_text,
    select_normalized_content,
)

from .connection import get_session
from .models import AnthropicArticle, Digest, OpenAIArticle, YouTubeVideo


class Repository:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

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
            digest_status="pending",
            digest_failure_reason=None,
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
            digest_status="pending",
            digest_failure_reason=None,
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
            digest_status="pending",
            digest_failure_reason=None,
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
        for v in videos:
            if v["video_id"] in existing_ids:
                continue

            normalized = select_normalized_content(
                description=v.get("description"),
                transcript=v.get("transcript"),
            )
            transcript_text = clean_transcript_text(v.get("transcript"))

            new_videos.append(
                YouTubeVideo(
                    video_id=v["video_id"],
                    title=v["title"],
                    url=v["url"],
                    channel_id=v.get("channel_id", ""),
                    published_at=v["published_at"],
                    description=v.get("description", ""),
                    transcript=v.get("transcript"),
                    cleaned_content=normalized.cleaned_content,
                    transcript_status="completed" if v.get("transcript") else "pending",
                    transcript_length=len(transcript_text) if transcript_text else None,
                    transcript_failure_reason=None,
                    content_richness=normalized.content_richness,
                    content_source_type=normalized.content_source_type,
                    digest_status="pending",
                    digest_failure_reason=None,
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
        for a in articles:
            if a["guid"] in existing_ids:
                continue

            normalized = select_normalized_content(description=a.get("description"))

            new_articles.append(
                OpenAIArticle(
                    guid=a["guid"],
                    title=a["title"],
                    url=a["url"],
                    published_at=a["published_at"],
                    description=a.get("description", ""),
                    cleaned_content=normalized.cleaned_content,
                    category=a.get("category"),
                    content_length=normalized.content_length,
                    content_richness=normalized.content_richness,
                    content_source_type=normalized.content_source_type,
                    digest_status="pending",
                    digest_failure_reason=None,
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
        for a in articles:
            if a["guid"] in existing_ids:
                continue

            normalized = select_normalized_content(description=a.get("description"))

            new_articles.append(
                AnthropicArticle(
                    guid=a["guid"],
                    title=a["title"],
                    url=a["url"],
                    published_at=a["published_at"],
                    description=a.get("description", ""),
                    cleaned_content=normalized.cleaned_content,
                    category=a.get("category"),
                    markdown_status="pending",
                    markdown_length=None,
                    markdown_failure_reason=None,
                    content_richness=normalized.content_richness,
                    content_source_type=normalized.content_source_type,
                    digest_status="pending",
                    digest_failure_reason=None,
                )
            )

        if new_articles:
            self.session.add_all(new_articles)
            self.session.commit()

        return len(new_articles)

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

    def get_articles_pending_digest(
        self, limit: Optional[int] = None
    ) -> List[NormalizedSourceItem]:
        articles: List[NormalizedSourceItem] = []

        youtube_videos = (
            self.session.query(YouTubeVideo)
            .filter(
                YouTubeVideo.digest_status == "pending",
                YouTubeVideo.cleaned_content.isnot(None),
                YouTubeVideo.cleaned_content != "",
            )
            .all()
        )

        for video in youtube_videos:
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

        openai_articles = (
            self.session.query(OpenAIArticle)
            .filter(
                OpenAIArticle.digest_status == "pending",
                OpenAIArticle.cleaned_content.isnot(None),
                OpenAIArticle.cleaned_content != "",
            )
            .all()
        )

        for article in openai_articles:
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

        anthropic_articles = (
            self.session.query(AnthropicArticle)
            .filter(
                AnthropicArticle.digest_status == "pending",
                AnthropicArticle.cleaned_content.isnot(None),
                AnthropicArticle.cleaned_content != "",
            )
            .all()
        )

        for article in anthropic_articles:
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
            key=lambda item: item.published_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        if limit:
            articles = articles[:limit]

        return articles

    def create_digest(
        self,
        article_type: str,
        article_id: str,
        url: str,
        title: str,
        summary: str,
        published_at: Optional[datetime] = None,
    ) -> Optional[Digest]:
        digest_id = f"{article_type}:{article_id}"
        existing = self.session.query(Digest).filter_by(id=digest_id).first()
        if existing:
            return None

        if published_at:
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            created_at = published_at
        else:
            created_at = datetime.now(timezone.utc)

        digest = Digest(
            id=digest_id,
            article_type=article_type,
            article_id=article_id,
            url=url,
            title=title,
            summary=summary,
            created_at=created_at,
        )
        self.session.add(digest)
        self.session.commit()
        return digest

    def get_recent_digests(self, hours: int = 24) -> List[Dict[str, Any]]:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        digests = (
            self.session.query(Digest)
            .filter(Digest.created_at >= cutoff_time)
            .order_by(Digest.created_at.desc())
            .all()
        )

        return [
            {
                "id": d.id,
                "article_type": d.article_type,
                "article_id": d.article_id,
                "url": d.url,
                "title": d.title,
                "summary": d.summary,
                "created_at": d.created_at,
            }
            for d in digests
        ]

    def mark_digest_completed(self, article_type: str, article_id: str) -> bool:
        record = None

        if article_type == "youtube":
            record = self.session.query(YouTubeVideo).filter_by(video_id=article_id).first()
        elif article_type == "openai":
            record = self.session.query(OpenAIArticle).filter_by(guid=article_id).first()
        elif article_type == "anthropic":
            record = self.session.query(AnthropicArticle).filter_by(guid=article_id).first()

        if not record:
            return False

        record.digest_status = "completed"
        record.digest_failure_reason = None
        self.session.commit()
        return True

    def mark_digest_failed(self, article_type: str, article_id: str, reason: str) -> bool:
        record = None

        if article_type == "youtube":
            record = self.session.query(YouTubeVideo).filter_by(video_id=article_id).first()
        elif article_type == "openai":
            record = self.session.query(OpenAIArticle).filter_by(guid=article_id).first()
        elif article_type == "anthropic":
            record = self.session.query(AnthropicArticle).filter_by(guid=article_id).first()

        if not record:
            return False

        record.digest_status = "failed"
        record.digest_failure_reason = reason
        self.session.commit()
        return True
