import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from app.story_clustering import RICHNESS_PRIORITY, SOURCE_TYPE_PRIORITY, build_source_key

MAX_STORY_DIGEST_SOURCES = 4
MAX_STORY_DIGEST_SOURCE_CHARS = 2500

SOURCE_TYPE_LABELS = {
    "youtube": "YouTube",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
}
SOURCE_TYPE_DISPLAY_PRIORITY = {
    "youtube": 0,
    "openai": 1,
    "anthropic": 2,
}


@dataclass(frozen=True)
class StoryDigestSource:
    source_type: str
    source_id: str
    url: str
    raw_title: str
    cleaned_content: str
    published_at: datetime
    content_richness: str
    content_source_type: str
    similarity_to_primary: float | None = None
    is_primary: bool = False


@dataclass(frozen=True)
class StoryDigestJob:
    story_id: str
    story_title: str
    representative_source_type: str
    representative_source_id: str
    source_count: int
    story_digest_input_hash: str
    members: list[StoryDigestSource]


def _normalize_datetime(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def build_story_digest_input_hash(
    representative_source_type: str,
    representative_source_id: str,
    members: Sequence[StoryDigestSource],
) -> str:
    payload = {
        "representative_source_key": build_source_key(
            representative_source_type,
            representative_source_id,
        ),
        "members": [
            {
                "source_key": build_source_key(member.source_type, member.source_id),
                "raw_title": member.raw_title,
                "cleaned_content": member.cleaned_content,
                "content_source_type": member.content_source_type,
                "content_richness": member.content_richness,
            }
            for member in sorted(
                members,
                key=lambda member: build_source_key(member.source_type, member.source_id),
            )
        ],
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def select_story_digest_sources(
    members: Sequence[StoryDigestSource],
    max_sources: int = MAX_STORY_DIGEST_SOURCES,
) -> list[StoryDigestSource]:
    if not members:
        return []

    representative = next((member for member in members if member.is_primary), members[0])
    remaining = [
        member
        for member in members
        if build_source_key(member.source_type, member.source_id)
        != build_source_key(representative.source_type, representative.source_id)
    ]

    selected = [representative]
    seen_types = {representative.source_type}

    def selection_key(member: StoryDigestSource) -> tuple[int, int, float, float, str]:
        similarity = (
            member.similarity_to_primary
            if member.similarity_to_primary is not None
            else -1.0
        )
        return (
            RICHNESS_PRIORITY.get(member.content_richness, 0),
            SOURCE_TYPE_PRIORITY.get(member.content_source_type, 0),
            similarity,
            _normalize_datetime(member.published_at),
            build_source_key(member.source_type, member.source_id),
        )

    while remaining and len(selected) < max_sources:
        diverse_candidates = [
            member for member in remaining if member.source_type not in seen_types
        ]
        candidates = diverse_candidates or remaining
        chosen = max(candidates, key=selection_key)
        selected.append(chosen)
        seen_types.add(chosen.source_type)
        remaining = [
            member
            for member in remaining
            if build_source_key(member.source_type, member.source_id)
            != build_source_key(chosen.source_type, chosen.source_id)
        ]

    return selected


def format_source_type_label(source_type: str) -> str:
    return SOURCE_TYPE_LABELS.get(source_type, source_type.title())


def format_source_attribution_line(
    *,
    source_types: Sequence[str],
    available_source_count: int,
    synthesis_mode: str,
) -> str:
    ordered_types = [
        format_source_type_label(source_type)
        for source_type in sorted(
            set(source_types),
            key=lambda source_type: (
                SOURCE_TYPE_DISPLAY_PRIORITY.get(source_type, 99),
                source_type,
            ),
        )
    ]

    if synthesis_mode == "single_source":
        label = ordered_types[0] if ordered_types else "Unknown"
        return f"Source: {label}"

    if synthesis_mode == "fallback_single_source":
        return (
            f"Sources available: {available_source_count}; "
            "digest based on representative source"
        )

    labels = ", ".join(ordered_types) if ordered_types else "Unknown"
    return f"Sources: {available_source_count} ({labels})"
