from datetime import datetime, timedelta, timezone

from app.database.models import Story, StorySourceLink
from app.database.repository import Repository
from app.services.process_story_clusters import process_story_clusters
from app.story_clustering import StoryClusterer, build_embedding_text


class FakeEmbeddingProvider:
    def __init__(self, embedding_map):
        self.embedding_map = embedding_map

    def embed_texts(self, texts):
        return [self.embedding_map[text] for text in texts]


def test_process_story_clusters_persists_and_reuses_story_ids(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="yt-1",
        title="OpenAI launches agents sdk",
        url="https://youtube.com/watch?v=yt-1",
        channel_id="channel-1",
        published_at=now,
        description="fallback",
        transcript="OpenAI launched a new agents sdk for developers.",
    )
    repo.create_openai_article(
        guid="oa-1",
        title="OpenAI agents sdk is now available",
        url="https://openai.com/agents-sdk",
        published_at=now - timedelta(hours=1),
        description="The agents sdk is now available for developers.",
        category="news",
    )

    first_items = repo.get_recent_normalized_source_items(hours=72)
    first_clusterer = StoryClusterer(
        FakeEmbeddingProvider(
            {
                build_embedding_text(item): [1.0, 0.0]
                for item in first_items
            }
        )
    )

    first_result = process_story_clusters(hours=24, repo=repo, clusterer=first_clusterer)

    story = db_session.query(Story).one()
    assert first_result["stories"] == 1
    assert first_result["multi_item_stories"] == 1
    assert story.representative_source_type == "youtube"
    assert story.representative_source_id == "yt-1"
    assert story.story_digest_status == "pending"
    assert story.story_digest_input_hash is not None
    assert db_session.query(StorySourceLink).count() == 2

    story_id = story.id

    repo.create_anthropic_article(
        guid="an-1",
        title="Developers get OpenAI agents sdk",
        url="https://anthropic.com/agents-sdk-commentary",
        published_at=now - timedelta(hours=2),
        description="More coverage about the same sdk launch.",
        category="news",
    )

    second_items = repo.get_recent_normalized_source_items(hours=72)
    second_clusterer = StoryClusterer(
        FakeEmbeddingProvider(
            {
                build_embedding_text(item): [1.0, 0.0]
                for item in second_items
            }
        )
    )

    second_result = process_story_clusters(hours=24, repo=repo, clusterer=second_clusterer)

    assert second_result["stories"] == 1
    assert second_result["links_updated"] >= 2
    assert db_session.query(Story).count() == 1
    assert db_session.query(Story).one().id == story_id
    assert db_session.query(StorySourceLink).count() == 3
    assert db_session.query(Story).one().source_count == 3


def test_get_recent_story_digests_collapses_duplicates_by_story(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="yt-primary",
        title="Primary story",
        url="https://youtube.com/watch?v=yt-primary",
        channel_id="channel-1",
        published_at=now,
        description="summary",
        transcript="rich transcript content",
    )
    repo.create_openai_article(
        guid="oa-secondary",
        title="Secondary story",
        url="https://openai.com/story",
        published_at=now - timedelta(hours=1),
        description="lighter summary",
        category="news",
    )

    repo.upsert_story_clusters(
        [
            {
                "story_id": "story-1",
                "title": "Primary story",
                "representative_source_type": "youtube",
                "representative_source_id": "yt-primary",
                "representative_published_at": now,
                "cluster_version": "story-cluster-v1",
                "window_start": now - timedelta(hours=72),
                "window_end": now,
                "links": [
                    {
                        "source_type": "youtube",
                        "source_id": "yt-primary",
                        "published_at": now,
                        "similarity_to_primary": 1.0,
                        "is_primary": True,
                    },
                    {
                        "source_type": "openai",
                        "source_id": "oa-secondary",
                        "published_at": now - timedelta(hours=1),
                        "similarity_to_primary": 0.91,
                        "is_primary": False,
                    },
                ],
            }
        ]
    )

    repo.create_digest(
        article_type="youtube",
        article_id="yt-primary",
        url="https://youtube.com/watch?v=yt-primary",
        title="Primary digest",
        summary="Primary summary",
        published_at=now,
    )
    repo.create_digest(
        article_type="openai",
        article_id="oa-secondary",
        url="https://openai.com/story",
        title="Secondary digest",
        summary="Secondary summary",
        published_at=now - timedelta(hours=1),
    )

    digests = repo.get_recent_story_digests(hours=24)

    assert len(digests) == 1
    assert digests[0]["id"] == "youtube:yt-primary"
    assert digests[0]["story_id"] == "story-1"
    assert digests[0]["story_source_count"] == 2
