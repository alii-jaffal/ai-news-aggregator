from datetime import datetime, timedelta, timezone

from app.story_digesting import (
    StoryDigestSource,
    build_story_digest_input_hash,
    format_source_attribution_line,
    select_story_digest_sources,
)


def make_source(
    *,
    source_type: str,
    source_id: str,
    published_at: datetime,
    content_richness: str = "summary",
    content_source_type: str = "rss",
    similarity_to_primary: float | None = None,
    is_primary: bool = False,
) -> StoryDigestSource:
    return StoryDigestSource(
        source_type=source_type,
        source_id=source_id,
        url=f"https://example.com/{source_type}/{source_id}",
        raw_title=f"{source_type} {source_id}",
        cleaned_content=f"content for {source_id}",
        published_at=published_at,
        content_richness=content_richness,
        content_source_type=content_source_type,
        similarity_to_primary=similarity_to_primary,
        is_primary=is_primary,
    )


def test_story_digest_input_hash_is_stable_across_member_order():
    now = datetime.now(timezone.utc)
    first = make_source(source_type="youtube", source_id="yt-1", published_at=now, is_primary=True)
    second = make_source(source_type="openai", source_id="oa-1", published_at=now)

    hash_a = build_story_digest_input_hash("youtube", "yt-1", [first, second])
    hash_b = build_story_digest_input_hash("youtube", "yt-1", [second, first])

    assert hash_a == hash_b


def test_select_story_digest_sources_prefers_diversity_after_representative():
    now = datetime.now(timezone.utc)
    representative = make_source(
        source_type="youtube",
        source_id="yt-1",
        published_at=now,
        content_richness="full",
        content_source_type="transcript",
        is_primary=True,
    )
    openai = make_source(
        source_type="openai",
        source_id="oa-1",
        published_at=now - timedelta(minutes=5),
        content_richness="summary",
        similarity_to_primary=0.92,
    )
    anthropic = make_source(
        source_type="anthropic",
        source_id="an-1",
        published_at=now - timedelta(minutes=10),
        content_richness="full",
        content_source_type="markdown",
        similarity_to_primary=0.88,
    )
    second_youtube = make_source(
        source_type="youtube",
        source_id="yt-2",
        published_at=now - timedelta(minutes=1),
        content_richness="full",
        content_source_type="transcript",
        similarity_to_primary=0.99,
    )

    selected = select_story_digest_sources([representative, openai, anthropic, second_youtube])

    assert selected[0].source_id == "yt-1"
    assert {source.source_type for source in selected[:3]} == {"youtube", "openai", "anthropic"}


def test_format_source_attribution_line_handles_all_modes():
    assert (
        format_source_attribution_line(
            source_types=["openai"],
            available_source_count=1,
            synthesis_mode="single_source",
        )
        == "Source: OpenAI"
    )
    assert (
        format_source_attribution_line(
            source_types=["youtube", "openai", "anthropic"],
            available_source_count=3,
            synthesis_mode="multi_source",
        )
        == "Sources: 3 (YouTube, OpenAI, Anthropic)"
    )
    assert (
        format_source_attribution_line(
            source_types=["youtube", "openai"],
            available_source_count=2,
            synthesis_mode="fallback_single_source",
        )
        == "Sources available: 2; digest based on representative source"
    )
