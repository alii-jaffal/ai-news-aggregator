from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    video_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)
    description = Column(Text)
    transcript = Column(Text, nullable=True)
    cleaned_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    transcript_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    transcript_length = Column(Integer, nullable=True)
    transcript_failure_reason = Column(String(100), nullable=True)
    content_richness = Column(
        String(20), nullable=False, default="missing", server_default="missing"
    )
    content_source_type = Column(
        String(20), nullable=False, default="rss", server_default="rss"
    )
    digest_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    digest_failure_reason = Column(String(100), nullable=True)


class OpenAIArticle(Base):
    __tablename__ = "openai_articles"

    guid = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=True)
    description = Column(Text)
    cleaned_content = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    content_length = Column(Integer, nullable=True)
    content_richness = Column(
        String(20), nullable=False, default="missing", server_default="missing"
    )
    content_source_type = Column(String(20), nullable=False, default="rss", server_default="rss")
    digest_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    digest_failure_reason = Column(String(100), nullable=True)


class AnthropicArticle(Base):
    __tablename__ = "anthropic_articles"

    guid = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False)
    category = Column(String, nullable=True)
    markdown = Column(Text, nullable=True)
    cleaned_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    markdown_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    markdown_length = Column(Integer, nullable=True)
    markdown_failure_reason = Column(String(100), nullable=True)
    content_richness = Column(
        String(20), nullable=False, default="missing", server_default="missing"
    )
    content_source_type = Column(
        String(20), nullable=False, default="rss", server_default="rss"
    )
    digest_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )
    digest_failure_reason = Column(String(100), nullable=True)


class Digest(Base):
    __tablename__ = "digests"

    id = Column(String, primary_key=True)
    article_type = Column(String, nullable=False)
    article_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Story(Base):
    __tablename__ = "stories"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    representative_source_type = Column(String(20), nullable=False)
    representative_source_id = Column(String, nullable=False)
    representative_published_at = Column(DateTime, nullable=False)
    source_count = Column(Integer, nullable=False, default=1, server_default="1")
    cluster_version = Column(String(50), nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class StorySourceLink(Base):
    __tablename__ = "story_source_links"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", name="uq_story_source_links_source_ref"),
        UniqueConstraint(
            "story_id",
            "source_type",
            "source_id",
            name="uq_story_source_links_story_source_ref",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    story_id = Column(
        String,
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type = Column(String(20), nullable=False)
    source_id = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    similarity_to_primary = Column(Float, nullable=True)
    is_primary = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
