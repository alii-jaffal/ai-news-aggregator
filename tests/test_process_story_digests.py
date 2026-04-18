from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.database.models import OpenAIArticle, Story, StoryDigest
from app.database.repository import Repository
from app.services.process_story_digests import process_story_digests


class FakeStoryDigestAgent:
    def __init__(self, fail_multi_source: bool = False):
        self.fail_multi_source = fail_multi_source
        self.calls = []

    def generate_digest(self, *, story_title, sources, synthesis_mode, available_source_count):
        self.calls.append(
            {
                "story_title": story_title,
                "source_ids": [source.source_id for source in sources],
                "synthesis_mode": synthesis_mode,
                "available_source_count": available_source_count,
            }
        )

        if self.fail_multi_source and synthesis_mode == "multi_source":
            return None

        return SimpleNamespace(
            title=f"{story_title} digest",
            summary=f"Summary for {story_title}",
            why_it_matters=f"Why {story_title} matters",
            disagreement_notes=None,
        )


def test_process_story_digests_generates_single_and_multi_source_digests(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_openai_article(
        guid="oa-single",
        title="Single story",
        url="https://openai.com/single",
        published_at=now,
        description="single source summary",
        category="news",
    )
    repo.create_youtube_video(
        video_id="yt-multi",
        title="Multi story video",
        url="https://youtube.com/watch?v=yt-multi",
        channel_id="channel-1",
        published_at=now - timedelta(minutes=5),
        description="video fallback",
        transcript="rich transcript content",
    )
    repo.create_anthropic_article(
        guid="an-multi",
        title="Multi story article",
        url="https://anthropic.com/multi",
        published_at=now - timedelta(minutes=10),
        description="supporting source summary",
        category="news",
    )

    repo.upsert_story_clusters(
        [
            {
                "story_id": "story-single",
                "title": "Single story",
                "representative_source_type": "openai",
                "representative_source_id": "oa-single",
                "representative_published_at": now,
                "cluster_version": "story-cluster-v1",
                "window_start": now - timedelta(hours=72),
                "window_end": now,
                "links": [
                    {
                        "source_type": "openai",
                        "source_id": "oa-single",
                        "published_at": now,
                        "similarity_to_primary": 1.0,
                        "is_primary": True,
                    }
                ],
            },
            {
                "story_id": "story-multi",
                "title": "Multi story",
                "representative_source_type": "youtube",
                "representative_source_id": "yt-multi",
                "representative_published_at": now - timedelta(minutes=5),
                "cluster_version": "story-cluster-v1",
                "window_start": now - timedelta(hours=72),
                "window_end": now,
                "links": [
                    {
                        "source_type": "youtube",
                        "source_id": "yt-multi",
                        "published_at": now - timedelta(minutes=5),
                        "similarity_to_primary": 1.0,
                        "is_primary": True,
                    },
                    {
                        "source_type": "anthropic",
                        "source_id": "an-multi",
                        "published_at": now - timedelta(minutes=10),
                        "similarity_to_primary": 0.91,
                        "is_primary": False,
                    },
                ],
            },
        ]
    )

    result = process_story_digests(repo=repo, agent=FakeStoryDigestAgent())

    assert result == {
        "total": 2,
        "processed": 2,
        "failed": 0,
        "fallback_used": 0,
        "kept_existing": 0,
    }
    assert db_session.query(StoryDigest).count() == 2

    single_story = db_session.query(Story).filter_by(id="story-single").one()
    multi_story = db_session.query(Story).filter_by(id="story-multi").one()
    assert single_story.story_digest_status == "completed"
    assert multi_story.story_digest_status == "completed"

    candidates = repo.get_recent_story_digest_candidates(hours=24)

    assert {candidate["id"] for candidate in candidates} == {
        "story:story-single",
        "story:story-multi",
    }
    assert all(candidate["article_type"] == "story" for candidate in candidates)
    assert any(
        candidate["source_attribution_line"] == "Source: OpenAI"
        for candidate in candidates
    )
    assert any(
        candidate["source_attribution_line"].startswith("Sources: 2")
        for candidate in candidates
    )


def test_process_story_digests_falls_back_to_representative_source(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="yt-story",
        title="Story video",
        url="https://youtube.com/watch?v=yt-story",
        channel_id="channel-1",
        published_at=now,
        description="fallback",
        transcript="rich transcript content",
    )
    repo.create_openai_article(
        guid="oa-story",
        title="Story article",
        url="https://openai.com/story",
        published_at=now - timedelta(minutes=5),
        description="supporting summary",
        category="news",
    )

    repo.upsert_story_clusters(
        [
            {
                "story_id": "story-fallback",
                "title": "Story fallback",
                "representative_source_type": "youtube",
                "representative_source_id": "yt-story",
                "representative_published_at": now,
                "cluster_version": "story-cluster-v1",
                "window_start": now - timedelta(hours=72),
                "window_end": now,
                "links": [
                    {
                        "source_type": "youtube",
                        "source_id": "yt-story",
                        "published_at": now,
                        "similarity_to_primary": 1.0,
                        "is_primary": True,
                    },
                    {
                        "source_type": "openai",
                        "source_id": "oa-story",
                        "published_at": now - timedelta(minutes=5),
                        "similarity_to_primary": 0.9,
                        "is_primary": False,
                    },
                ],
            }
        ]
    )

    result = process_story_digests(
        repo=repo,
        agent=FakeStoryDigestAgent(fail_multi_source=True),
    )

    story_digest = db_session.query(StoryDigest).filter_by(story_id="story-fallback").one()
    story = db_session.query(Story).filter_by(id="story-fallback").one()

    assert result["fallback_used"] == 1
    assert story.story_digest_status == "completed"
    assert story_digest.synthesis_mode == "fallback_single_source"
    assert story_digest.used_source_count == 1
    assert story_digest.available_source_count == 2


def test_upsert_story_clusters_only_requeues_story_digest_when_hash_changes(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_openai_article(
        guid="oa-hash",
        title="Hash story",
        url="https://openai.com/hash",
        published_at=now,
        description="original summary",
        category="news",
    )

    payload = [
        {
            "story_id": "story-hash",
            "title": "Hash story",
            "representative_source_type": "openai",
            "representative_source_id": "oa-hash",
            "representative_published_at": now,
            "cluster_version": "story-cluster-v1",
            "window_start": now - timedelta(hours=72),
            "window_end": now,
            "links": [
                {
                    "source_type": "openai",
                    "source_id": "oa-hash",
                    "published_at": now,
                    "similarity_to_primary": 1.0,
                    "is_primary": True,
                }
            ],
        }
    ]

    repo.upsert_story_clusters(payload)
    story = db_session.query(Story).filter_by(id="story-hash").one()
    original_hash = story.story_digest_input_hash

    repo.upsert_story_digest(
        story_id="story-hash",
        title="Hash story digest",
        summary="Summary",
        why_it_matters="Why it matters",
        disagreement_notes=None,
        synthesis_mode="single_source",
        available_source_count=1,
        used_source_count=1,
        generated_input_hash=original_hash,
    )

    repo.upsert_story_clusters(payload)
    story = db_session.query(Story).filter_by(id="story-hash").one()

    assert story.story_digest_status == "completed"
    assert story.story_digest_input_hash == original_hash

    article = db_session.query(OpenAIArticle).filter_by(guid="oa-hash").one()
    article.cleaned_content = "updated summary text"
    db_session.commit()

    repo.upsert_story_clusters(payload)
    story = db_session.query(Story).filter_by(id="story-hash").one()

    assert story.story_digest_status == "pending"
    assert story.story_digest_input_hash != original_hash
