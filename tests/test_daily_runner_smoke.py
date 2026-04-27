from app import daily_runner


class FakePipelineRepository:
    def __init__(self):
        self.created_run = None
        self.runs = {}
        self.progress_updates = []
        self.completed = None
        self.failed = None

    def create_pipeline_run(
        self,
        *,
        trigger_source,
        requested_hours,
        requested_top_n,
        profile_slug,
        send_email,
        status="queued",
    ):
        run = type(
            "PipelineRun",
            (),
            {
                "id": "run-1",
                "trigger_source": trigger_source,
                "requested_hours": requested_hours,
                "requested_top_n": requested_top_n,
                "profile_slug": profile_slug,
                "send_email": send_email,
                "status": status,
            },
        )()
        self.created_run = run
        self.runs[run.id] = run
        return run

    def get_pipeline_run(self, run_id):
        return self.runs.get(run_id)

    def mark_pipeline_run_running(self, run_id):
        return self.runs.get(run_id)

    def update_pipeline_run_progress(self, run_id, **kwargs):
        self.progress_updates.append(kwargs)
        return self.runs.get(run_id)

    def complete_pipeline_run(self, run_id, **kwargs):
        self.completed = (run_id, kwargs)
        return self.runs.get(run_id)

    def fail_pipeline_run(self, run_id, **kwargs):
        self.failed = (run_id, kwargs)
        return self.runs.get(run_id)

    def close(self):
        return None


def test_run_daily_pipeline_happy_path(monkeypatch):
    repo = FakePipelineRepository()
    captured = {"send_email_enabled": None, "pipeline_run_id": None}

    monkeypatch.setattr(
        daily_runner,
        "get_runtime_user_profile",
        lambda repo=None: {"slug": "default"},
    )
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
        lambda hours, repo=None: {
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
        lambda repo=None: {
            "total": 2,
            "processed": 2,
            "failed": 0,
            "fallback_used": 0,
            "kept_existing": 0,
        },
    )

    def fake_run_email_stage(hours, top_n, send_email_enabled, pipeline_run_id, repo=None):
        captured["send_email_enabled"] = send_email_enabled
        captured["pipeline_run_id"] = pipeline_run_id
        return {
            "success": True,
            "sent": True,
            "subject": "Daily AI News Digest - Today",
            "articles_count": 2,
        }

    monkeypatch.setattr(daily_runner, "run_email_stage", fake_run_email_stage)

    result = daily_runner.run_daily_pipeline(hours=24, top_n=10, repo=repo)

    assert result["success"] is True
    assert result["pipeline_run_id"] == "run-1"
    assert result["scraping"]["youtube"] == 1
    assert result["processing"]["stories"]["stories"] == 1
    assert result["digests"]["processed"] == 2
    assert captured["send_email_enabled"] is True
    assert captured["pipeline_run_id"] == "run-1"
    assert repo.completed is not None


def test_run_daily_pipeline_handles_stage_exception(monkeypatch):
    repo = FakePipelineRepository()

    monkeypatch.setattr(
        daily_runner,
        "get_runtime_user_profile",
        lambda repo=None: {"slug": "default"},
    )
    monkeypatch.setattr(
        daily_runner,
        "run_scrapers",
        lambda hours: {"youtube": [], "openai": [], "anthropic": []},
    )

    def boom():
        raise RuntimeError("anthropic stage failed")

    monkeypatch.setattr(daily_runner, "process_anthropic_markdown", boom)

    result = daily_runner.run_daily_pipeline(hours=24, top_n=10, repo=repo)

    assert result["success"] is False
    assert "anthropic stage failed" in result["error"]
    assert repo.failed is not None


def test_run_daily_pipeline_uses_profile_default_top_n_when_omitted(monkeypatch):
    repo = FakePipelineRepository()
    captured = {"top_n": "unset"}

    monkeypatch.setattr(
        daily_runner,
        "get_runtime_user_profile",
        lambda repo=None: {"slug": "default"},
    )
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
        lambda hours, repo=None: {
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
        lambda repo=None: {
            "total": 0,
            "processed": 0,
            "failed": 0,
            "fallback_used": 0,
            "kept_existing": 0,
        },
    )

    def fake_run_email_stage(hours, top_n, send_email_enabled, pipeline_run_id, repo=None):
        captured["top_n"] = top_n
        return {
            "success": True,
            "sent": False,
            "reason": "no_digests",
            "subject": None,
            "articles_count": 0,
        }

    monkeypatch.setattr(daily_runner, "run_email_stage", fake_run_email_stage)

    result = daily_runner.run_daily_pipeline(hours=24, repo=repo)

    assert result["success"] is True
    assert captured["top_n"] is None


def test_run_daily_pipeline_dashboard_rerun_skips_email_delivery(monkeypatch):
    repo = FakePipelineRepository()
    captured = {"send_email_enabled": None}

    monkeypatch.setattr(
        daily_runner,
        "get_runtime_user_profile",
        lambda repo=None: {"slug": "default"},
    )
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
        lambda hours, repo=None: {
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
        lambda repo=None: {
            "total": 0,
            "processed": 0,
            "failed": 0,
            "fallback_used": 0,
            "kept_existing": 0,
        },
    )

    def fake_run_email_stage(hours, top_n, send_email_enabled, pipeline_run_id, repo=None):
        captured["send_email_enabled"] = send_email_enabled
        return {
            "success": True,
            "sent": False,
            "reason": "send_disabled",
            "subject": "Daily AI News Digest - Today",
            "articles_count": 0,
        }

    monkeypatch.setattr(daily_runner, "run_email_stage", fake_run_email_stage)

    result = daily_runner.run_daily_pipeline(hours=24, send_email=False, repo=repo)

    assert result["success"] is True
    assert captured["send_email_enabled"] is False
