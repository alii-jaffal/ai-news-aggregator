from datetime import datetime, timedelta, timezone

from app.content_normalization import NormalizedSourceItem
from app.story_clustering import (
    StoryClusterer,
    build_embedding_text,
    choose_representative,
)


class FakeEmbeddingProvider:
    def __init__(self, embedding_map):
        self.embedding_map = embedding_map

    def embed_texts(self, texts):
        return [self.embedding_map[text] for text in texts]


def make_item(
    *,
    source_type,
    source_id,
    title,
    cleaned_content,
    published_at,
    content_richness="summary",
    content_source_type="rss",
):
    return NormalizedSourceItem(
        source_type=source_type,
        source_id=source_id,
        url=f"https://example.com/{source_type}/{source_id}",
        raw_title=title,
        raw_summary=title,
        cleaned_content=cleaned_content,
        published_at=published_at,
        content_length=len(cleaned_content),
        content_richness=content_richness,
        content_source_type=content_source_type,
    )


def test_story_clusterer_merges_high_similarity_cross_source_items():
    now = datetime.now(timezone.utc)
    item_a = make_item(
        source_type="youtube",
        source_id="yt-1",
        title="OpenAI launches new agent sdk",
        cleaned_content="OpenAI launched a new agent sdk for developers.",
        published_at=now,
        content_richness="full",
        content_source_type="transcript",
    )
    item_b = make_item(
        source_type="openai",
        source_id="oa-1",
        title="Developer tools arrive in OpenAI sdk update",
        cleaned_content="The new OpenAI agent sdk gives developers orchestration tools.",
        published_at=now - timedelta(hours=2),
    )
    item_c = make_item(
        source_type="anthropic",
        source_id="an-1",
        title="Anthropic publishes safety update",
        cleaned_content="Anthropic shared an unrelated safety update.",
        published_at=now - timedelta(hours=1),
    )

    embedding_map = {
        build_embedding_text(item_a): [1.0, 0.0],
        build_embedding_text(item_b): [1.0, 0.0],
        build_embedding_text(item_c): [0.0, 1.0],
    }

    clusters = StoryClusterer(FakeEmbeddingProvider(embedding_map)).cluster_items(
        [item_a, item_b, item_c]
    )

    assert len(clusters) == 2
    merged_cluster = next(cluster for cluster in clusters if len(cluster.members) == 2)
    assert {member.source_id for member in merged_cluster.members} == {"yt-1", "oa-1"}
    assert merged_cluster.representative.source_id == "yt-1"


def test_story_clusterer_requires_title_overlap_for_medium_similarity():
    now = datetime.now(timezone.utc)
    item_a = make_item(
        source_type="openai",
        source_id="oa-1",
        title="OpenAI releases roadmap",
        cleaned_content="Roadmap content",
        published_at=now,
    )
    item_b = make_item(
        source_type="anthropic",
        source_id="an-1",
        title="Anthropic safety report",
        cleaned_content="Safety report content",
        published_at=now - timedelta(hours=1),
    )

    embedding_map = {
        build_embedding_text(item_a): [1.0, 0.0],
        build_embedding_text(item_b): [0.8, 0.6],
    }

    clusters = StoryClusterer(FakeEmbeddingProvider(embedding_map)).cluster_items([item_a, item_b])

    assert len(clusters) == 2


def test_story_clusterer_links_medium_similarity_with_title_overlap():
    now = datetime.now(timezone.utc)
    item_a = make_item(
        source_type="openai",
        source_id="oa-1",
        title="OpenAI agents platform launches",
        cleaned_content="Platform launch content",
        published_at=now,
    )
    item_b = make_item(
        source_type="anthropic",
        source_id="an-1",
        title="OpenAI agents tutorial",
        cleaned_content="Tutorial content",
        published_at=now - timedelta(hours=1),
    )

    embedding_map = {
        build_embedding_text(item_a): [1.0, 0.0],
        build_embedding_text(item_b): [0.8, 0.6],
    }

    clusters = StoryClusterer(FakeEmbeddingProvider(embedding_map)).cluster_items([item_a, item_b])

    assert len(clusters) == 1
    assert {member.source_id for member in clusters[0].members} == {"oa-1", "an-1"}


def test_choose_representative_prefers_richer_sources_then_recency():
    now = datetime.now(timezone.utc)
    summary_item = make_item(
        source_type="openai",
        source_id="oa-summary",
        title="Summary",
        cleaned_content="Summary",
        published_at=now,
        content_richness="summary",
        content_source_type="rss",
    )
    markdown_item = make_item(
        source_type="anthropic",
        source_id="an-markdown",
        title="Markdown",
        cleaned_content="Markdown",
        published_at=now - timedelta(minutes=5),
        content_richness="full",
        content_source_type="markdown",
    )
    transcript_item = make_item(
        source_type="youtube",
        source_id="yt-transcript",
        title="Transcript",
        cleaned_content="Transcript",
        published_at=now - timedelta(hours=1),
        content_richness="full",
        content_source_type="transcript",
    )

    representative = choose_representative([summary_item, markdown_item, transcript_item])

    assert representative.source_id == "yt-transcript"
