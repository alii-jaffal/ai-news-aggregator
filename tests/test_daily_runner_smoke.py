from app import daily_runner


def test_run_daily_pipeline_happy_path(monkeypatch):
    monkeypatch.setattr(
        daily_runner,
        "run_scrapers",
        lambda hours: {"youtube": [1], "openai": [1], "anthropic": [1]},
    )
    monkeypatch.setattr(
        daily_runner,
        "process_anthropic_markdown",
        lambda: {"total": 1, "processed": 1, "unavailable": 0, "failed": 0},
    )
    monkeypatch.setattr(
        daily_runner,
        "process_youtube_transcripts",
        lambda: {"total": 1, "processed": 1, "unavailable": 0, "failed": 0},
    )
    monkeypatch.setattr(
        daily_runner,
        "process_story_clusters",
        lambda hours: {
            "window_hours": 72,
            "items_considered": 2,
            "stories": 1,
            "multi_item_stories": 1,
            "singleton_stories": 0,
            "links_created": 2,
            "links_updated": 0,
            "stories_created": 1,
            "stories_updated": 0,
        },
    )
    monkeypatch.setattr(
        daily_runner,
        "process_story_digests",
        lambda: {
            "total": 2,
            "processed": 2,
            "failed": 0,
            "fallback_used": 0,
            "kept_existing": 0,
        },
    )
    monkeypatch.setattr(
        daily_runner,
        "send_digest_email",
        lambda hours, top_n: {
            "success": True,
            "sent": True,
            "subject": "Daily AI News Digest - Today",
            "articles_count": 2,
        },
    )

    result = daily_runner.run_daily_pipeline(hours=24, top_n=10)

    assert result["success"] is True
    assert result["scraping"]["youtube"] == 1
    assert result["processing"]["stories"]["stories"] == 1
    assert result["digests"]["processed"] == 2


def test_run_daily_pipeline_handles_stage_exception(monkeypatch):
    monkeypatch.setattr(
        daily_runner,
        "run_scrapers",
        lambda hours: {"youtube": [], "openai": [], "anthropic": []},
    )

    def boom():
        raise RuntimeError("anthropic stage failed")

    monkeypatch.setattr(daily_runner, "process_anthropic_markdown", boom)

    result = daily_runner.run_daily_pipeline(hours=24, top_n=10)

    assert result["success"] is False
    assert "anthropic stage failed" in result["error"]


def test_run_daily_pipeline_uses_profile_default_top_n_when_omitted(monkeypatch):
    captured = {"top_n": "unset"}

    monkeypatch.setattr(
        daily_runner,
        "run_scrapers",
        lambda hours: {"youtube": [], "openai": [], "anthropic": []},
    )
    monkeypatch.setattr(
        daily_runner,
        "process_anthropic_markdown",
        lambda: {"total": 0, "processed": 0, "unavailable": 0, "failed": 0},
    )
    monkeypatch.setattr(
        daily_runner,
        "process_youtube_transcripts",
        lambda: {"total": 0, "processed": 0, "unavailable": 0, "failed": 0},
    )
    monkeypatch.setattr(
        daily_runner,
        "process_story_clusters",
        lambda hours: {
            "window_hours": 72,
            "items_considered": 0,
            "stories": 0,
            "multi_item_stories": 0,
            "singleton_stories": 0,
            "links_created": 0,
            "links_updated": 0,
            "stories_created": 0,
            "stories_updated": 0,
        },
    )
    monkeypatch.setattr(
        daily_runner,
        "process_story_digests",
        lambda: {
            "total": 0,
            "processed": 0,
            "failed": 0,
            "fallback_used": 0,
            "kept_existing": 0,
        },
    )

    def fake_send_digest_email(hours, top_n):
        captured["top_n"] = top_n
        return {
            "success": True,
            "sent": False,
            "reason": "no_digests",
            "subject": None,
            "articles_count": 0,
        }

    monkeypatch.setattr(daily_runner, "send_digest_email", fake_send_digest_email)

    result = daily_runner.run_daily_pipeline(hours=24)

    assert result["success"] is True
    assert captured["top_n"] is None
