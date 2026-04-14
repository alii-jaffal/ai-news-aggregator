"""add cleaned content to source tables

Revision ID: 3ef7b5997f2a
Revises: 9771fd7ad96f
Create Date: 2026-04-13 20:00:00.000000

"""

import html
import re
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3ef7b5997f2a"
down_revision: Union[str, Sequence[str], None] = "9771fd7ad96f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WHITESPACE_RE = re.compile(r"\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
MARKDOWN_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+", re.MULTILINE)
MARKDOWN_QUOTE_RE = re.compile(r"^\s*>\s*", re.MULTILINE)
MARKDOWN_CODE_FENCE_RE = re.compile(r"```+")
MARKDOWN_INLINE_CODE_RE = re.compile(r"`([^`]*)`")


def _collapse_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def _clean_rss_summary(summary: str | None) -> str:
    if not summary:
        return ""

    stripped = HTML_TAG_RE.sub(" ", html.unescape(summary))
    return _collapse_whitespace(stripped)


def _clean_transcript_text(transcript: str | None) -> str:
    if not transcript:
        return ""

    return _collapse_whitespace(html.unescape(transcript))


def _clean_markdown_text(markdown: str | None) -> str:
    if not markdown:
        return ""

    text = html.unescape(markdown)
    text = MARKDOWN_IMAGE_RE.sub(r"\1", text)
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = MARKDOWN_CODE_FENCE_RE.sub("", text)
    text = MARKDOWN_INLINE_CODE_RE.sub(r"\1", text)
    text = MARKDOWN_HEADING_RE.sub("", text)
    text = MARKDOWN_BULLET_RE.sub("", text)
    text = MARKDOWN_QUOTE_RE.sub("", text)
    return _collapse_whitespace(text)


def _select_content(
    *,
    description: str | None = None,
    transcript: str | None = None,
    markdown: str | None = None,
) -> tuple[str | None, str, str]:
    cleaned_transcript = _clean_transcript_text(transcript)
    if cleaned_transcript:
        return cleaned_transcript, "full", "transcript"

    cleaned_markdown = _clean_markdown_text(markdown)
    if cleaned_markdown:
        return cleaned_markdown, "full", "markdown"

    cleaned_summary = _clean_rss_summary(description)
    if cleaned_summary:
        return cleaned_summary, "summary", "rss"

    return None, "missing", "rss"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("youtube_videos", sa.Column("cleaned_content", sa.Text(), nullable=True))
    op.add_column(
        "youtube_videos",
        sa.Column(
            "content_source_type",
            sa.String(length=20),
            server_default="rss",
            nullable=False,
        ),
    )
    op.add_column("openai_articles", sa.Column("cleaned_content", sa.Text(), nullable=True))
    op.add_column("anthropic_articles", sa.Column("cleaned_content", sa.Text(), nullable=True))
    op.add_column(
        "anthropic_articles",
        sa.Column(
            "content_source_type",
            sa.String(length=20),
            server_default="rss",
            nullable=False,
        ),
    )

    conn = op.get_bind()

    youtube_videos = sa.table(
        "youtube_videos",
        sa.column("video_id", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("transcript", sa.Text()),
        sa.column("transcript_length", sa.Integer()),
        sa.column("content_richness", sa.String(length=20)),
        sa.column("content_source_type", sa.String(length=20)),
        sa.column("cleaned_content", sa.Text()),
    )
    openai_articles = sa.table(
        "openai_articles",
        sa.column("guid", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("content_length", sa.Integer()),
        sa.column("content_richness", sa.String(length=20)),
        sa.column("content_source_type", sa.String(length=20)),
        sa.column("cleaned_content", sa.Text()),
    )
    anthropic_articles = sa.table(
        "anthropic_articles",
        sa.column("guid", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("markdown", sa.Text()),
        sa.column("markdown_length", sa.Integer()),
        sa.column("content_richness", sa.String(length=20)),
        sa.column("content_source_type", sa.String(length=20)),
        sa.column("cleaned_content", sa.Text()),
    )

    youtube_rows = conn.execute(
        sa.select(
            youtube_videos.c.video_id,
            youtube_videos.c.description,
            youtube_videos.c.transcript,
        )
    ).mappings()
    for row in youtube_rows:
        cleaned_content, content_richness, content_source_type = _select_content(
            description=row["description"],
            transcript=row["transcript"],
        )
        transcript_text = _clean_transcript_text(row["transcript"])
        conn.execute(
            youtube_videos.update()
            .where(youtube_videos.c.video_id == row["video_id"])
            .values(
                cleaned_content=cleaned_content,
                transcript_length=len(transcript_text) if transcript_text else None,
                content_richness=content_richness,
                content_source_type=content_source_type,
            )
        )

    openai_rows = conn.execute(
        sa.select(openai_articles.c.guid, openai_articles.c.description)
    ).mappings()
    for row in openai_rows:
        cleaned_content, content_richness, content_source_type = _select_content(
            description=row["description"]
        )
        conn.execute(
            openai_articles.update()
            .where(openai_articles.c.guid == row["guid"])
            .values(
                cleaned_content=cleaned_content,
                content_length=len(cleaned_content) if cleaned_content else None,
                content_richness=content_richness,
                content_source_type=content_source_type,
            )
        )

    anthropic_rows = conn.execute(
        sa.select(
            anthropic_articles.c.guid,
            anthropic_articles.c.description,
            anthropic_articles.c.markdown,
        )
    ).mappings()
    for row in anthropic_rows:
        cleaned_content, content_richness, content_source_type = _select_content(
            description=row["description"],
            markdown=row["markdown"],
        )
        markdown_text = _clean_markdown_text(row["markdown"])
        conn.execute(
            anthropic_articles.update()
            .where(anthropic_articles.c.guid == row["guid"])
            .values(
                cleaned_content=cleaned_content,
                markdown_length=len(markdown_text) if markdown_text else None,
                content_richness=content_richness,
                content_source_type=content_source_type,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("anthropic_articles", "content_source_type")
    op.drop_column("anthropic_articles", "cleaned_content")
    op.drop_column("openai_articles", "cleaned_content")
    op.drop_column("youtube_videos", "content_source_type")
    op.drop_column("youtube_videos", "cleaned_content")
