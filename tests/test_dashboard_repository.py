from datetime import datetime, timedelta, timezone

from app.database.repository import Repository


def _seed_story_archive(repo: Repository, now: datetime) -> None:
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
                        "similarity_to_primary": 0.92,
                        "is_primary": False,
                    },
                ],
            }
        ]
    )
    repo.upsert_story_digest(
        story_id="story-1",
        title="OpenAI Story Digest",
        summary="A synthesized summary.",
        why_it_matters="It matters for builders.",
        disagreement_notes=None,
        synthesis_mode="multi_source",
        available_source_count=2,
        used_source_count=2,
        generated_input_hash=repo.get_stories_pending_story_digest(limit=1)[0].story_digest_input_hash,
    )


def test_pipeline_and_newsletter_run_lifecycle(db_session):
    repo = Repository(session=db_session)

    pipeline_run = repo.create_pipeline_run(
        trigger_source="cli",
        requested_hours=24,
        requested_top_n=10,
        profile_slug="default",
        send_email=True,
    )
    repo.mark_pipeline_run_running(pipeline_run.id)
    repo.update_pipeline_run_progress(
        pipeline_run.id,
        scraping_summary={"youtube": 1},
        processing_summary={"youtube": {"processed": 1}},
    )
    repo.complete_pipeline_run(
        pipeline_run.id,
        scraping_summary={"youtube": 1},
        processing_summary={"youtube": {"processed": 1}},
        digest_summary={"processed": 1},
        email_summary={"success": True, "sent": True},
    )

    newsletter_run = repo.create_newsletter_run(
        pipeline_run_id=pipeline_run.id,
        profile_slug="default",
        window_hours=24,
        resolved_top_n=5,
        subject="Daily AI News Digest - April 27, 2026",
        greeting="Hey Ali, here is your digest for April 27, 2026.",
        introduction="Two strong stories today.",
        sent=False,
        article_count=2,
        payload_json={"articles": [{"title": "Story 1"}]},
    )
    repo.mark_newsletter_run_sent(newsletter_run.id)

    listed_runs = repo.list_pipeline_runs(limit=10, offset=0)
    listed_newsletters = repo.list_newsletter_runs(limit=10, offset=0)

    assert listed_runs["total"] == 1
    assert listed_runs["items"][0]["status"] == "completed"
    assert listed_runs["items"][0]["email_summary"]["sent"] is True
    assert listed_newsletters["total"] == 1
    assert listed_newsletters["items"][0]["sent"] is True
    assert listed_newsletters["items"][0]["pipeline_run_id"] == pipeline_run.id


def test_source_and_story_archive_queries(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="yt-failed",
        title="Transcript Missing",
        url="https://youtube.com/watch?v=yt-failed",
        channel_id="channel-2",
        published_at=now - timedelta(hours=1),
        description="Fallback",
        transcript=None,
    )
    repo.mark_youtube_transcript_failed("yt-failed", "timeout")
    _seed_story_archive(repo, now)

    sources = repo.list_source_archive(source_type="youtube", status="failed", limit=10, offset=0)
    stories = repo.list_story_archive(q="OpenAI", limit=10, offset=0)
    story_detail = repo.get_story_archive_item("story-1")

    assert sources["total"] == 1
    assert sources["items"][0]["failure_reason"] == "timeout"
    assert stories["total"] == 1
    assert stories["items"][0]["digest_title"] == "OpenAI Story Digest"
    assert story_detail is not None
    assert story_detail["digest"]["summary"] == "A synthesized summary."
    assert len(story_detail["sources"]) == 2


def test_dashboard_overview_and_failures(db_session):
    repo = Repository(session=db_session)
    now = datetime.now(timezone.utc)

    repo.create_youtube_video(
        video_id="yt-unavailable",
        title="No Transcript",
        url="https://youtube.com/watch?v=yt-unavailable",
        channel_id="channel-3",
        published_at=now - timedelta(hours=2),
        description="Video summary",
        transcript=None,
    )
    repo.mark_youtube_transcript_unavailable("yt-unavailable", "transcript_not_available")

    repo.create_anthropic_article(
        guid="anthropic-failed",
        title="Anthropic Failure",
        url="https://anthropic.com/failure",
        published_at=now - timedelta(hours=2),
        description="Anthropic summary",
        category="news",
    )
    repo.mark_anthropic_markdown_failed("anthropic-failed", "DoclingError")
    _seed_story_archive(repo, now)
    repo.mark_story_digest_failed("story-1", "story_digest_generation_failed")

    pipeline_run = repo.create_pipeline_run(
        trigger_source="api",
        requested_hours=24,
        requested_top_n=None,
        profile_slug="default",
        send_email=False,
    )
    repo.fail_pipeline_run(
        pipeline_run.id,
        error_message="dashboard rerun failed",
        scraping_summary={},
        processing_summary={},
        digest_summary={},
        email_summary={},
    )

    overview = repo.get_dashboard_overview(hours=24)
    failures = repo.get_failure_summary(hours=168)

    assert overview["source_counts"]["youtube"] >= 1
    assert overview["story_counts"]["total"] >= 1
    assert overview["latest_pipeline_run"]["status"] == "failed"
    assert failures["summary"]["youtube_unavailable"] == 1
    assert failures["summary"]["anthropic_failed"] == 1
    assert failures["summary"]["story_digest_failed"] == 1
    assert failures["summary"]["pipeline_failed"] == 1
