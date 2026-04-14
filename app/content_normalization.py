import html
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel

WHITESPACE_RE = re.compile(r"\s+")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
MARKDOWN_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+", re.MULTILINE)
MARKDOWN_QUOTE_RE = re.compile(r"^\s*>\s*", re.MULTILINE)
MARKDOWN_CODE_FENCE_RE = re.compile(r"```+")
MARKDOWN_INLINE_CODE_RE = re.compile(r"`([^`]*)`")


class NormalizedContent(BaseModel):
    cleaned_content: Optional[str]
    content_length: Optional[int]
    content_richness: str
    content_source_type: str


class NormalizedSourceItem(BaseModel):
    source_type: str
    source_id: str
    url: str
    raw_title: str
    raw_summary: str
    cleaned_content: str
    published_at: datetime
    content_length: int
    content_richness: str
    content_source_type: str


def collapse_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def clean_rss_summary(summary: Optional[str]) -> str:
    if not summary:
        return ""

    parsed = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
    return collapse_whitespace(html.unescape(parsed))


def clean_transcript_text(transcript: Optional[str]) -> str:
    if not transcript:
        return ""

    return collapse_whitespace(html.unescape(transcript))


def clean_markdown_text(markdown: Optional[str]) -> str:
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
    return collapse_whitespace(text)


def select_normalized_content(
    description: Optional[str] = None,
    transcript: Optional[str] = None,
    markdown: Optional[str] = None,
) -> NormalizedContent:
    cleaned_transcript = clean_transcript_text(transcript)
    if cleaned_transcript:
        return NormalizedContent(
            cleaned_content=cleaned_transcript,
            content_length=len(cleaned_transcript),
            content_richness="full",
            content_source_type="transcript",
        )

    cleaned_markdown = clean_markdown_text(markdown)
    if cleaned_markdown:
        return NormalizedContent(
            cleaned_content=cleaned_markdown,
            content_length=len(cleaned_markdown),
            content_richness="full",
            content_source_type="markdown",
        )

    cleaned_summary = clean_rss_summary(description)
    if cleaned_summary:
        return NormalizedContent(
            cleaned_content=cleaned_summary,
            content_length=len(cleaned_summary),
            content_richness="summary",
            content_source_type="rss",
        )

    return NormalizedContent(
        cleaned_content=None,
        content_length=None,
        content_richness="missing",
        content_source_type="rss",
    )
