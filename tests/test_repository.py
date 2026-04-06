from datetime import datetime, timedelta, timezone

from app.database.models import AnthropicArticle, OpenAIArticle, YouTubeVideo
from app.database.repository import Repository


def test_create_youtube_video_is_idempotent(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    created = repo.create_youtube_video(
        video_id="vid-1",
        title="Video 1",
        url="https://youtube.com/watch?v=vid-1",
        channel_id="channel-1",
        published_at=now,
        description="desc",
        transcript=None,
    )
    duplicate = repo.create_youtube_video(
        video_id="vid-1",
        title="Video 1",
        url="https://youtube.com/watch?v=vid-1",
        channel_id="channel-1",
        published_at=now,
        description="desc",
        transcript=None,
    )

    assert created is not None
    assert duplicate is None
    assert db_session.query(YouTubeVideo).count() == 1


def test_bulk_create_openai_articles_skips_existing_rows(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    articles = [
        {
            "guid": "openai-1",
            "title": "A1",
            "url": "https://openai.com/a1",
            "published_at": now,
            "description": "summary 1",
            "category": "news",
        },
        {
            "guid": "openai-2",
            "title": "A2",
            "url": "https://openai.com/a2",
            "published_at": now,
            "description": "summary 2",
            "category": "news",
        },
    ]

    inserted_first = repo.bulk_create_openai_articles(articles)
    inserted_second = repo.bulk_create_openai_articles(articles)

    assert inserted_first == 2
    assert inserted_second == 0
    assert db_session.query(OpenAIArticle).count() == 2


def test_bulk_create_anthropic_articles_skips_existing_rows(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    articles = [
        {
            "guid": "anthropic-1",
            "title": "A1",
            "url": "https://anthropic.com/a1",
            "published_at": now,
            "description": "summary 1",
            "category": "news",
        }
    ]

    inserted_first = repo.bulk_create_anthropic_articles(articles)
    inserted_second = repo.bulk_create_anthropic_articles(articles)

    assert inserted_first == 1
    assert inserted_second == 0
    assert db_session.query(AnthropicArticle).count() == 1


def test_mark_youtube_transcript_completed(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="vid-2",
        title="Video 2",
        url="https://youtube.com/watch?v=vid-2",
        channel_id="channel-1",
        published_at=now,
        description="desc",
        transcript=None,
    )

    ok = repo.mark_youtube_transcript_completed("vid-2", "hello world transcript")
    video = db_session.query(YouTubeVideo).filter_by(video_id="vid-2").first()

    assert ok is True
    assert video.transcript_status == "completed"
    assert video.transcript_length == len("hello world transcript")
    assert video.transcript_failure_reason is None
    assert video.content_richness == "full"


def test_mark_youtube_transcript_unavailable(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="vid-3",
        title="Video 3",
        url="https://youtube.com/watch?v=vid-3",
        channel_id="channel-1",
        published_at=now,
        description="desc",
        transcript=None,
    )

    ok = repo.mark_youtube_transcript_unavailable("vid-3", "transcript_not_available")
    video = db_session.query(YouTubeVideo).filter_by(video_id="vid-3").first()

    assert ok is True
    assert video.transcript is None
    assert video.transcript_status == "unavailable"
    assert video.transcript_failure_reason == "transcript_not_available"
    assert video.content_richness == "missing"


def test_mark_anthropic_markdown_completed(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_anthropic_article(
        guid="anthropic-2",
        title="Anthropic 2",
        url="https://anthropic.com/a2",
        published_at=now,
        description="desc",
        category="news",
    )

    ok = repo.mark_anthropic_markdown_completed("anthropic-2", "# markdown body")
    article = db_session.query(AnthropicArticle).filter_by(guid="anthropic-2").first()

    assert ok is True
    assert article.markdown_status == "completed"
    assert article.markdown_length == len("# markdown body")
    assert article.markdown_failure_reason is None
    assert article.content_richness == "full"


def test_mark_digest_completed_and_failed(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_openai_article(
        guid="openai-3",
        title="A3",
        url="https://openai.com/a3",
        published_at=now,
        description="summary",
        category="news",
    )

    ok_failed = repo.mark_digest_failed("openai", "openai-3", "gemini_503")
    article = db_session.query(OpenAIArticle).filter_by(guid="openai-3").first()

    assert ok_failed is True
    assert article.digest_status == "failed"
    assert article.digest_failure_reason == "gemini_503"

    ok_completed = repo.mark_digest_completed("openai", "openai-3")
    article = db_session.query(OpenAIArticle).filter_by(guid="openai-3").first()

    assert ok_completed is True
    assert article.digest_status == "completed"
    assert article.digest_failure_reason is None


def test_get_articles_pending_digest_only_returns_ready_items(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="yt-ready",
        title="YT Ready",
        url="https://youtube.com/watch?v=yt-ready",
        channel_id="c1",
        published_at=now,
        description="desc",
        transcript="full transcript",
    )

    repo.create_youtube_video(
        video_id="yt-pending",
        title="YT Pending",
        url="https://youtube.com/watch?v=yt-pending",
        channel_id="c1",
        published_at=now,
        description="desc",
        transcript=None,
    )

    repo.create_openai_article(
        guid="openai-ready",
        title="OpenAI Ready",
        url="https://openai.com/ready",
        published_at=now,
        description="summary",
        category="news",
    )

    repo.create_anthropic_article(
        guid="anthropic-pending",
        title="Anthropic Pending",
        url="https://anthropic.com/pending",
        published_at=now,
        description="desc",
        category="news",
    )

    rows = repo.get_articles_pending_digest()

    ids = {row["id"] for row in rows}
    assert "yt-ready" in ids
    assert "openai-ready" in ids
    assert "yt-pending" not in ids
    assert "anthropic-pending" not in ids


def test_get_recent_digests_returns_newest_first(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_digest(
        article_type="openai",
        article_id="d1",
        url="https://openai.com/1",
        title="Digest 1",
        summary="summary 1",
        published_at=now - timedelta(hours=2),
    )
    repo.create_digest(
        article_type="openai",
        article_id="d2",
        url="https://openai.com/2",
        title="Digest 2",
        summary="summary 2",
        published_at=now,
    )

    rows = repo.get_recent_digests(hours=24)

    assert rows[0]["article_id"] == "d2"
    assert rows[1]["article_id"] == "d1"
