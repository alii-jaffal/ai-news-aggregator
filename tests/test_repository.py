from datetime import datetime, timedelta, timezone

from app.database.models import AnthropicArticle, OpenAIArticle, UserProfile, YouTubeVideo
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
        description="<p>desc</p>",
        transcript=None,
    )
    duplicate = repo.create_youtube_video(
        video_id="vid-1",
        title="Video 1",
        url="https://youtube.com/watch?v=vid-1",
        channel_id="channel-1",
        published_at=now,
        description="<p>desc</p>",
        transcript=None,
    )

    assert created is not None
    assert created.cleaned_content == "desc"
    assert created.content_richness == "summary"
    assert created.content_source_type == "rss"
    assert duplicate is None
    assert db_session.query(YouTubeVideo).count() == 1


def test_create_openai_article_cleans_description_into_shared_content(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    article = repo.create_openai_article(
        guid="openai-clean",
        title="OpenAI Clean",
        url="https://openai.com/clean",
        published_at=now,
        description="<p>Hello <strong>AI</strong></p>",
        category="news",
    )

    assert article is not None
    assert article.cleaned_content == "Hello AI"
    assert article.content_length == len("Hello AI")
    assert article.content_richness == "summary"
    assert article.content_source_type == "rss"


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


def test_mark_youtube_transcript_completed_upgrades_shared_content(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="vid-2",
        title="Video 2",
        url="https://youtube.com/watch?v=vid-2",
        channel_id="channel-1",
        published_at=now,
        description="<p>fallback summary</p>",
        transcript=None,
    )

    ok = repo.mark_youtube_transcript_completed("vid-2", "hello\n\nworld transcript")
    video = db_session.query(YouTubeVideo).filter_by(video_id="vid-2").first()

    assert ok is True
    assert video.cleaned_content == "hello world transcript"
    assert video.transcript_status == "completed"
    assert video.transcript_length == len("hello world transcript")
    assert video.transcript_failure_reason is None
    assert video.content_richness == "full"
    assert video.content_source_type == "transcript"


def test_mark_youtube_transcript_unavailable_preserves_summary_fallback(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="vid-3",
        title="Video 3",
        url="https://youtube.com/watch?v=vid-3",
        channel_id="channel-1",
        published_at=now,
        description="<p>Fallback summary</p>",
        transcript=None,
    )

    ok = repo.mark_youtube_transcript_unavailable("vid-3", "transcript_not_available")
    video = db_session.query(YouTubeVideo).filter_by(video_id="vid-3").first()

    assert ok is True
    assert video.transcript is None
    assert video.cleaned_content == "Fallback summary"
    assert video.transcript_status == "unavailable"
    assert video.transcript_failure_reason == "transcript_not_available"
    assert video.content_richness == "summary"
    assert video.content_source_type == "rss"


def test_mark_anthropic_markdown_completed_uses_cleaned_markdown(db_session):
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

    ok = repo.mark_anthropic_markdown_completed(
        "anthropic-2",
        "# Main Heading\n\nA [linked](https://example.com) paragraph.",
    )
    article = db_session.query(AnthropicArticle).filter_by(guid="anthropic-2").first()

    assert ok is True
    assert article.cleaned_content == "Main Heading A linked paragraph."
    assert article.markdown_status == "completed"
    assert article.markdown_length == len("Main Heading A linked paragraph.")
    assert article.markdown_failure_reason is None
    assert article.content_richness == "full"
    assert article.content_source_type == "markdown"


def test_mark_anthropic_markdown_unavailable_preserves_summary_fallback(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_anthropic_article(
        guid="anthropic-3",
        title="Anthropic 3",
        url="https://anthropic.com/a3",
        published_at=now,
        description="<p>Fallback article summary</p>",
        category="news",
    )

    ok = repo.mark_anthropic_markdown_unavailable("anthropic-3", "no_markdown_extracted")
    article = db_session.query(AnthropicArticle).filter_by(guid="anthropic-3").first()

    assert ok is True
    assert article.cleaned_content == "Fallback article summary"
    assert article.markdown is None
    assert article.markdown_status == "unavailable"
    assert article.markdown_failure_reason == "no_markdown_extracted"
    assert article.content_richness == "summary"
    assert article.content_source_type == "rss"


def test_get_recent_normalized_source_items_returns_cleaned_rows(db_session):
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
        video_id="yt-summary",
        title="YT Summary",
        url="https://youtube.com/watch?v=yt-summary",
        channel_id="c1",
        published_at=now - timedelta(minutes=1),
        description="<p>summary only</p>",
        transcript=None,
    )

    repo.create_youtube_video(
        video_id="yt-empty",
        title="YT Empty",
        url="https://youtube.com/watch?v=yt-empty",
        channel_id="c1",
        published_at=now - timedelta(minutes=2),
        description="",
        transcript=None,
    )

    repo.create_openai_article(
        guid="openai-ready",
        title="OpenAI Ready",
        url="https://openai.com/ready",
        published_at=now - timedelta(minutes=3),
        description="summary",
        category="news",
    )

    repo.create_anthropic_article(
        guid="anthropic-summary",
        title="Anthropic Summary",
        url="https://anthropic.com/summary",
        published_at=now - timedelta(minutes=4),
        description="desc",
        category="news",
    )

    repo.create_anthropic_article(
        guid="anthropic-empty",
        title="Anthropic Empty",
        url="https://anthropic.com/empty",
        published_at=now - timedelta(minutes=5),
        description="",
        category="news",
    )

    rows = repo.get_recent_normalized_source_items(hours=24)

    ids = {row.source_id for row in rows}
    assert ids == {"yt-ready", "yt-summary", "openai-ready", "anthropic-summary"}
    assert rows[0].source_id == "yt-ready"
    assert rows[0].cleaned_content == "full transcript"
    assert rows[1].source_id == "yt-summary"
    assert rows[1].content_richness == "summary"
    assert rows[1].content_source_type == "rss"


def test_upsert_user_profile_creates_and_updates_single_row(db_session):
    repo = Repository(session=db_session)

    created = repo.upsert_user_profile(
        slug="ali",
        name="Ali",
        title="AI Engineer",
        background="Builds AI systems",
        expertise_level="Intermediate",
        interests=["agents", "rag"],
        preferred_source_types=["openai", "youtube"],
        preferences={"prefer_practical": True},
        newsletter_top_n=7,
    )

    updated = repo.upsert_user_profile(
        slug="ali",
        name="Ali Jaffal",
        title="Senior AI Engineer",
        background="Builds production AI systems",
        expertise_level="Advanced",
        interests=["agents", "rag", "infra"],
        preferred_source_types=["openai"],
        preferences={"prefer_practical": True, "avoid_marketing_hype": True},
        newsletter_top_n=5,
    )

    rows = repo.list_user_profiles()

    assert created.id == updated.id
    assert len(rows) == 1
    assert rows[0].slug == "ali"
    assert rows[0].name == "Ali Jaffal"
    assert rows[0].newsletter_top_n == 5
    assert rows[0].is_active is True


def test_set_active_user_profile_switches_active_profile(db_session):
    repo = Repository(session=db_session)

    repo.upsert_user_profile(
        slug="ali",
        name="Ali",
        title="AI Engineer",
        background="Builds AI systems",
        expertise_level="Intermediate",
        interests=["agents"],
        preferred_source_types=["openai"],
        preferences={"prefer_practical": True},
        newsletter_top_n=5,
    )
    repo.upsert_user_profile(
        slug="team",
        name="Team",
        title="Research Team",
        background="Tracks AI news",
        expertise_level="Intermediate",
        interests=["research"],
        preferred_source_types=["anthropic"],
        preferences={"prefer_research_breakthroughs": True},
        newsletter_top_n=8,
    )

    activated = repo.set_active_user_profile("team")

    ali = repo.get_user_profile_by_slug("ali")
    team = repo.get_user_profile_by_slug("team")

    assert activated is not None
    assert activated.slug == "team"
    assert ali is not None and ali.is_active is False
    assert team is not None and team.is_active is True


def test_get_active_user_profile_returns_none_when_missing(db_session):
    repo = Repository(session=db_session)

    assert repo.get_active_user_profile() is None
    assert db_session.query(UserProfile).count() == 0
