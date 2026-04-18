from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import tuple_
from sqlalchemy.orm import Session

from app.content_normalization import (
    NormalizedSourceItem,
    clean_markdown_text,
    clean_transcript_text,
    select_normalized_content,
)
from app.story_clustering import RICHNESS_PRIORITY, SOURCE_TYPE_PRIORITY, build_source_key
from app.story_digesting import (
    StoryDigestJob,
    StoryDigestSource,
    build_story_digest_input_hash,
    format_source_attribution_line,
)

from .connection import get_session
from .models import (
    AnthropicArticle,
    Digest,
    OpenAIArticle,
    Story,
    StoryDigest,
    StorySourceLink,
    YouTubeVideo,
)


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
    def _digest_selection_key(digest: Dict[str, Any], source_metadata: Dict[str, Any]) -> tuple:
        published_at = source_metadata.get("published_at") or digest.get("created_at")
        if published_at is None:
            published_order = 0.0
        else:
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)
            published_order = published_at.timestamp()

        return (
            RICHNESS_PRIORITY.get(source_metadata.get("content_richness", "missing"), 0),
            SOURCE_TYPE_PRIORITY.get(source_metadata.get("content_source_type", "rss"), 0),
            published_order,
            digest["id"],
        )

    def _collect_normalized_source_items(
        self,
        *,
        hours: Optional[int] = None,
        pending_digest_only: bool = False,
    ) -> List[NormalizedSourceItem]:
        articles: List[NormalizedSourceItem] = []
        cutoff_time = None
        if hours is not None:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        youtube_query = self.session.query(YouTubeVideo).filter(
            YouTubeVideo.cleaned_content.isnot(None),
            YouTubeVideo.cleaned_content != "",
        )
        if pending_digest_only:
            youtube_query = youtube_query.filter(YouTubeVideo.digest_status == "pending")
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
        if pending_digest_only:
            openai_query = openai_query.filter(OpenAIArticle.digest_status == "pending")
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
        if pending_digest_only:
            anthropic_query = anthropic_query.filter(AnthropicArticle.digest_status == "pending")
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
                    digest_status="pending",
                    digest_failure_reason=None,
                )
            )

        if new_articles:
            self.session.add_all(new_articles)
            self.session.commit()

        return len(new_articles)

    def get_recent_normalized_source_items(self, hours: int) -> List[NormalizedSourceItem]:
        return self._collect_normalized_source_items(hours=hours, pending_digest_only=False)

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
        articles = self._collect_normalized_source_items(pending_digest_only=True)
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
        digest_id = build_source_key(article_type, article_id)
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
                "id": digest.id,
                "article_type": digest.article_type,
                "article_id": digest.article_id,
                "url": digest.url,
                "title": digest.title,
                "summary": digest.summary,
                "created_at": digest.created_at,
            }
            for digest in digests
        ]

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

    def _get_story_links_for_source_refs(
        self,
        source_refs: Sequence[tuple[str, str]],
    ) -> Dict[str, StorySourceLink]:
        if not source_refs:
            return {}

        links = (
            self.session.query(StorySourceLink)
            .filter(tuple_(StorySourceLink.source_type, StorySourceLink.source_id).in_(source_refs))
            .all()
        )
        return {build_source_key(link.source_type, link.source_id): link for link in links}

    def _get_source_metadata_map(
        self,
        source_refs: Sequence[tuple[str, str]],
    ) -> Dict[str, Dict[str, Any]]:
        metadata: Dict[str, Dict[str, Any]] = {}
        refs_by_type: Dict[str, List[str]] = {"youtube": [], "openai": [], "anthropic": []}
        for source_type, source_id in source_refs:
            refs_by_type.setdefault(source_type, []).append(source_id)

        if refs_by_type["youtube"]:
            for video in (
                self.session.query(YouTubeVideo)
                .filter(YouTubeVideo.video_id.in_(refs_by_type["youtube"]))
                .all()
            ):
                metadata[build_source_key("youtube", video.video_id)] = {
                    "content_richness": video.content_richness,
                    "content_source_type": video.content_source_type,
                    "published_at": video.published_at,
                }

        if refs_by_type["openai"]:
            for article in (
                self.session.query(OpenAIArticle)
                .filter(OpenAIArticle.guid.in_(refs_by_type["openai"]))
                .all()
            ):
                metadata[build_source_key("openai", article.guid)] = {
                    "content_richness": article.content_richness,
                    "content_source_type": article.content_source_type,
                    "published_at": article.published_at,
                }

        if refs_by_type["anthropic"]:
            for article in (
                self.session.query(AnthropicArticle)
                .filter(AnthropicArticle.guid.in_(refs_by_type["anthropic"]))
                .all()
            ):
                metadata[build_source_key("anthropic", article.guid)] = {
                    "content_richness": article.content_richness,
                    "content_source_type": article.content_source_type,
                    "published_at": article.published_at,
                }

        return metadata

    def get_recent_story_digests(self, hours: int = 24) -> List[Dict[str, Any]]:
        recent_digests = self.get_recent_digests(hours=hours)
        if not recent_digests:
            return []

        source_refs = [(digest["article_type"], digest["article_id"]) for digest in recent_digests]
        story_link_map = self._get_story_links_for_source_refs(source_refs)
        story_ids = {link.story_id for link in story_link_map.values()}
        story_map = {
            story.id: story
            for story in self.session.query(Story).filter(Story.id.in_(story_ids)).all()
        }
        source_metadata = self._get_source_metadata_map(source_refs)

        grouped_digests: Dict[str, List[Dict[str, Any]]] = {}
        for digest in recent_digests:
            source_key = build_source_key(digest["article_type"], digest["article_id"])
            link = story_link_map.get(source_key)
            group_key = link.story_id if link else digest["id"]
            grouped_digests.setdefault(group_key, []).append(digest)

        collapsed_digests: List[Dict[str, Any]] = []
        for group_key, digests in grouped_digests.items():
            if group_key in story_map:
                story = story_map[group_key]
                representative_digest_id = build_source_key(
                    story.representative_source_type,
                    story.representative_source_id,
                )
                digest_by_id = {digest["id"]: digest for digest in digests}
                selected_digest = digest_by_id.get(representative_digest_id)
                if selected_digest is None:
                    selected_digest = max(
                        digests,
                        key=lambda digest: self._digest_selection_key(
                            digest,
                            source_metadata.get(digest["id"], {}),
                        ),
                    )
                collapsed_digests.append(
                    {
                        **selected_digest,
                        "story_id": story.id,
                        "story_source_count": story.source_count,
                    }
                )
            else:
                collapsed_digests.append(
                    {
                        **digests[0],
                        "story_id": None,
                        "story_source_count": 1,
                    }
                )

        collapsed_digests.sort(
            key=lambda digest: self._normalize_datetime(digest["created_at"]),
            reverse=True,
        )
        return collapsed_digests

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
