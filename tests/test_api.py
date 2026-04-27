from collections.abc import Generator
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_repository
from app.api.main import create_app
from app.database.models import Base
from app.database.repository import Repository


def _build_session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def _build_app_and_repo():
    session_factory = _build_session_factory()
    seed_session = session_factory()
    seed_repo = Repository(session=seed_session)
    app = create_app()

    def override_repository() -> Generator[Repository, None, None]:
        session = session_factory()
        repo = Repository(session=session)
        try:
            yield repo
        finally:
            session.close()

    app.dependency_overrides[get_repository] = override_repository
    return app, seed_repo, seed_session


def _seed_dashboard_api_data(repo: Repository, now: datetime) -> None:
    repo.create_openai_article(
        guid="openai-story",
        title="OpenAI Story",
        url="https://openai.com/story",
        published_at=now,
        description="OpenAI summary",
        category="news",
    )
    repo.create_youtube_video(
        video_id="yt-story",
        title="YouTube Story",
        url="https://youtube.com/watch?v=yt-story",
        channel_id="channel-1",
        published_at=now - timedelta(minutes=5),
        description="Video summary",
        transcript="Full transcript",
    )
    repo.upsert_story_clusters(
        [
            {
                "story_id": "story-1",
                "title": "OpenAI Story",
                "representative_source_type": "openai",
                "representative_source_id": "openai-story",
                "representative_published_at": now,
                "cluster_version": "test-v1",
                "window_start": now - timedelta(hours=24),
                "window_end": now,
                "links": [
                    {
                        "source_type": "openai",
                        "source_id": "openai-story",
                        "published_at": now,
                        "similarity_to_primary": 1.0,
                        "is_primary": True,
                    },
                    {
                        "source_type": "youtube",
                        "source_id": "yt-story",
                        "published_at": now - timedelta(minutes=5),
                        "similarity_to_primary": 0.91,
                        "is_primary": False,
                    },
                ],
            }
        ]
    )
    pending_digest = repo.get_stories_pending_story_digest(limit=1)[0]
    repo.upsert_story_digest(
        story_id="story-1",
        title="OpenAI Story Digest",
        summary="A synthesized summary.",
        why_it_matters="It matters for builders.",
        disagreement_notes=None,
        synthesis_mode="multi_source",
        available_source_count=2,
        used_source_count=2,
        generated_input_hash=pending_digest.story_digest_input_hash,
    )

    pipeline_run = repo.create_pipeline_run(
        trigger_source="cli",
        requested_hours=24,
        requested_top_n=10,
        profile_slug="default",
        send_email=True,
    )
    repo.complete_pipeline_run(
        pipeline_run.id,
        scraping_summary={"youtube": 1, "openai": 1, "anthropic": 0},
        processing_summary={"youtube": {"processed": 1}},
        digest_summary={"processed": 1},
        email_summary={"success": True, "sent": True},
    )
    repo.create_newsletter_run(
        pipeline_run_id=pipeline_run.id,
        profile_slug="default",
        window_hours=24,
        resolved_top_n=5,
        subject="Daily AI News Digest - April 27, 2026",
        greeting="Hey Ali, here is your digest for April 27, 2026.",
        introduction="Two strong stories today.",
        sent=True,
        article_count=1,
        payload_json={"articles": [{"title": "OpenAI Story Digest"}]},
    )


def test_dashboard_api_overview_archive_and_run_endpoints():
    app, seed_repo, seed_session = _build_app_and_repo()
    try:
        _seed_dashboard_api_data(seed_repo, datetime.now(timezone.utc))
        client = TestClient(app)

        health = client.get("/api/health")
        overview = client.get("/api/dashboard/overview?hours=24")
        sources = client.get("/api/sources?source_type=openai")
        source_detail = client.get("/api/sources/openai/openai-story")
        stories = client.get("/api/stories?q=OpenAI")
        story_detail = client.get("/api/stories/story-1")
        pipeline_runs = client.get("/api/pipeline-runs")
        newsletter_runs = client.get("/api/newsletter-runs")

        assert health.status_code == 204
        assert overview.status_code == 200
        assert overview.json()["latest_pipeline_run"]["status"] == "completed"
        assert sources.status_code == 200
        assert sources.json()["total"] == 1
        assert source_detail.status_code == 200
        assert source_detail.json()["source_type"] == "openai"
        assert stories.status_code == 200
        assert stories.json()["items"][0]["digest_title"] == "OpenAI Story Digest"
        assert story_detail.status_code == 200
        assert len(story_detail.json()["sources"]) == 2
        assert pipeline_runs.status_code == 200
        assert pipeline_runs.json()["total"] == 1
        assert newsletter_runs.status_code == 200
        assert newsletter_runs.json()["total"] == 1
    finally:
        seed_session.close()


def test_create_pipeline_run_endpoint_conflict_and_queue(monkeypatch):
    app, seed_repo, seed_session = _build_app_and_repo()
    try:
        client = TestClient(app)

        monkeypatch.setattr(
            "app.api.main.get_runtime_user_profile",
            lambda repo=None: {"slug": "default"},
        )
        monkeypatch.setattr("app.api.main.execute_pipeline_run", lambda run_id, hours, top_n: None)

        first = client.post("/api/pipeline-runs", json={"hours": 24, "top_n": 5})
        second = client.post("/api/pipeline-runs", json={"hours": 24, "top_n": 5})

        assert first.status_code == 202
        assert first.json()["status"] == "queued"
        assert second.status_code == 409
    finally:
        seed_repo.close()
        seed_session.close()
