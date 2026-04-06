from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .models import YouTubeVideo, OpenAIArticle, AnthropicArticle, Digest
from .connection import get_session


class Repository:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

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

        video = YouTubeVideo(
            video_id=video_id,
            title=title,
            url=url,
            channel_id=channel_id,
            published_at=published_at,
            description=description,
            transcript=transcript,
            transcript_status="completed" if transcript else "pending",
            transcript_length=len(transcript) if transcript else None,
            transcript_failure_reason=None,
            content_richness="full" if transcript else "missing",
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

        article = OpenAIArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            category=category,
            content_length=len(description) if description else None,
            content_richness="summary" if description else "missing",
            content_source_type="rss",
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

        article = AnthropicArticle(
            guid=guid,
            title=title,
            url=url,
            published_at=published_at,
            description=description,
            category=category,
            markdown_status="pending",
            markdown_length=None,
            markdown_failure_reason=None,
            content_richness="missing",
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

            new_videos.append(
                YouTubeVideo(
                    video_id=v["video_id"],
                    title=v["title"],
                    url=v["url"],
                    channel_id=v.get("channel_id", ""),
                    published_at=v["published_at"],
                    description=v.get("description", ""),
                    transcript=v.get("transcript"),
                    transcript_status="completed" if v.get("transcript") else "pending",
                    transcript_length=len(v["transcript"]) if v.get("transcript") else None,
                    transcript_failure_reason=None,
                    content_richness="full" if v.get("transcript") else "missing",
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

            new_articles.append(
                OpenAIArticle(
                    guid=a["guid"],
                    title=a["title"],
                    url=a["url"],
                    published_at=a["published_at"],
                    description=a.get("description", ""),
                    category=a.get("category"),
                    content_length=len(a.get("description", "")) if a.get("description") else None,
                    content_richness="summary" if a.get("description") else "missing",
                    content_source_type="rss",
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

            new_articles.append(
                AnthropicArticle(
                    guid=a["guid"],
                    title=a["title"],
                    url=a["url"],
                    published_at=a["published_at"],
                    description=a.get("description", ""),
                    category=a.get("category"),
                    markdown_status="pending",
                    markdown_length=None,
                    markdown_failure_reason=None,
                    content_richness="missing",
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

        article.markdown = markdown
        article.markdown_status = "completed"
        article.markdown_length = len(markdown)
        article.markdown_failure_reason = None
        article.content_richness = "full"
        self.session.commit()
        return True

    def mark_anthropic_markdown_unavailable(
        self, guid: str, reason: str = "no_markdown_extracted"
    ) -> bool:
        article = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if not article:
            return False

        article.markdown = None
        article.markdown_status = "unavailable"
        article.markdown_length = None
        article.markdown_failure_reason = reason
        article.content_richness = "missing"
        self.session.commit()
        return True

    def mark_anthropic_markdown_failed(self, guid: str, reason: str) -> bool:
        article = self.session.query(AnthropicArticle).filter_by(guid=guid).first()
        if not article:
            return False

        article.markdown_status = "failed"
        article.markdown_length = None
        article.markdown_failure_reason = reason
        article.content_richness = "missing"
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

        video.transcript = transcript
        video.transcript_status = "completed"
        video.transcript_length = len(transcript)
        video.transcript_failure_reason = None
        video.content_richness = "full"
        self.session.commit()
        return True

    def mark_youtube_transcript_unavailable(
        self, video_id: str, reason: str = "transcript_not_available"
    ) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if not video:
            return False

        video.transcript = None
        video.transcript_status = "unavailable"
        video.transcript_length = None
        video.transcript_failure_reason = reason
        video.content_richness = "missing"
        self.session.commit()
        return True

    def mark_youtube_transcript_failed(self, video_id: str, reason: str) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if not video:
            return False

        video.transcript_status = "failed"
        video.transcript_length = None
        video.transcript_failure_reason = reason
        video.content_richness = "missing"
        self.session.commit()
        return True

    def get_articles_pending_digest(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        articles = []

        youtube_videos = (
            self.session.query(YouTubeVideo)
            .filter(
                YouTubeVideo.digest_status == "pending",
                YouTubeVideo.transcript_status == "completed",
            )
            .all()
        )

        for video in youtube_videos:
            articles.append(
                {
                    "type": "youtube",
                    "id": video.video_id,
                    "title": video.title,
                    "url": video.url,
                    "content": video.transcript or video.description or "",
                    "published_at": video.published_at,
                    "content_length": video.transcript_length,
                    "content_richness": video.content_richness,
                }
            )

        openai_articles = (
            self.session.query(OpenAIArticle)
            .filter(
                OpenAIArticle.digest_status == "pending",
                OpenAIArticle.content_richness != "missing",
            )
            .all()
        )

        for article in openai_articles:
            articles.append(
                {
                    "type": "openai",
                    "id": article.guid,
                    "title": article.title,
                    "url": article.url,
                    "content": article.description or "",
                    "published_at": article.published_at,
                    "content_length": article.content_length,
                    "content_richness": article.content_richness,
                }
            )

        anthropic_articles = (
            self.session.query(AnthropicArticle)
            .filter(
                AnthropicArticle.digest_status == "pending",
                AnthropicArticle.markdown_status == "completed",
            )
            .all()
        )

        for article in anthropic_articles:
            articles.append(
                {
                    "type": "anthropic",
                    "id": article.guid,
                    "title": article.title,
                    "url": article.url,
                    "content": article.markdown or article.description or "",
                    "published_at": article.published_at,
                    "content_length": article.markdown_length,
                    "content_richness": article.content_richness,
                }
            )

        articles.sort(
            key=lambda item: item["published_at"] or datetime.min.replace(tzinfo=timezone.utc),
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
