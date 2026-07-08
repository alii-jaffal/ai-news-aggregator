from app import daily_runner


class FakePipelineRepository:
    def __init__(self):
        self.created_run = None
        self.runs = {}
        self.progress_updates = []
        self.completed = None
        self.failed = None
        self.stage_runs = []

    def create_pipeline_run(
        self,
        *,
        trigger_source,
        run_type="full_pipeline",
        requested_stage=None,
        retry_stage_run_id=None,
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
                "run_type": run_type,
                "requested_stage": requested_stage,
                "retry_stage_run_id": retry_stage_run_id,
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
        if self.runs[run_id].status == "cancelled":
            self.failed = (run_id, kwargs)
            return self.runs.get(run_id)
        self.failed = (run_id, kwargs)
        return self.runs.get(run_id)

    def is_pipeline_run_cancelled(self, run_id):
        run = self.runs.get(run_id)
        return run is not None and run.status == "cancelled"

    def cancel_pipeline_run(self, run_id, *, reason="Cancelled from dashboard"):
        run = self.runs.get(run_id)
        if run is None:
            return None
        run.status = "cancelled"
        for stage_run in self.stage_runs:
            if stage_run["status"] == "running":
                stage_run["status"] = "cancelled"
                stage_run["error_message"] = reason
        return run

    def start_pipeline_stage_run(self, pipeline_run_id, *, stage_name, retry_of_stage_run_id=None):
        stage_run = type(
            "PipelineStageRun",
            (),
            {
                "id": f"stage-{len(self.stage_runs) + 1}",
                "pipeline_run_id": pipeline_run_id,
                "stage_name": stage_name,
                "status": "running",
                "retry_of_stage_run_id": retry_of_stage_run_id,
            },
        )()
        self.stage_runs.append(
            {
                "id": stage_run.id,
                "stage_name": stage_name,
                "status": "running",
                "summary_json": {},
                "error_message": None,
                "retry_of_stage_run_id": retry_of_stage_run_id,
            }
        )
        return stage_run

    def complete_pipeline_stage_run(self, stage_run_id, *, summary_json=None):
        for stage_run in self.stage_runs:
            if stage_run["id"] == stage_run_id:
                stage_run["status"] = "completed"
                stage_run["summary_json"] = summary_json or {}
                return stage_run
        return None

    def fail_pipeline_stage_run(self, stage_run_id, *, error_message, summary_json=None):
        for stage_run in self.stage_runs:
            if stage_run["id"] == stage_run_id:
                stage_run["status"] = "failed"
                stage_run["error_message"] = error_message
                stage_run["summary_json"] = summary_json or {}
                return stage_run
        return None

    def cancel_pipeline_stage_run(self, stage_run_id, *, error_message, summary_json=None):
        for stage_run in self.stage_runs:
            if stage_run["id"] == stage_run_id:
                stage_run["status"] = "cancelled"
                stage_run["error_message"] = error_message
                stage_run["summary_json"] = summary_json or {}
                return stage_run
        return None

    def upsert_worker_heartbeat(
        self,
        worker_name,
        *,
        status,
        current_run_id=None,
        current_stage_name=None,
    ):
        return {
            "worker_name": worker_name,
            "status": status,
            "current_run_id": current_run_id,
            "current_stage_name": current_stage_name,
        }

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
    assert [stage["stage_name"] for stage in repo.stage_runs] == [
        "scraping",
        "anthropic_markdown",
        "youtube_transcripts",
        "story_clustering",
        "story_digests",
        "email",
    ]


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
    assert repo.stage_runs[1]["status"] == "failed"


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


def test_run_daily_pipeline_stops_after_cancelled_stage(monkeypatch):
    repo = FakePipelineRepository()

    monkeypatch.setattr(
        daily_runner,
        "get_runtime_user_profile",
        lambda repo=None: {"slug": "default"},
    )

    def fake_run_scrapers(hours):
        repo.cancel_pipeline_run("run-1")
        return {"youtube": [], "openai": [], "anthropic": []}

    monkeypatch.setattr(daily_runner, "run_scrapers", fake_run_scrapers)
    monkeypatch.setattr(
        daily_runner,
        "process_anthropic_markdown",
        lambda: {"total": 0, "processed": 0, "unavailable": 0, "failed": 0},
    )

    result = daily_runner.run_daily_pipeline(hours=24, repo=repo)

    assert result["success"] is False
    assert result["cancelled"] is True
    assert "cancelled" in result["error"].lower()
    assert [stage["stage_name"] for stage in repo.stage_runs] == ["scraping"]
    assert repo.stage_runs[0]["status"] == "cancelled"


def test_run_daily_pipeline_single_stage_retry_only_runs_requested_stage(monkeypatch):
    repo = FakePipelineRepository()
    calls = {
        "scraping": 0,
        "anthropic_markdown": 0,
        "youtube_transcripts": 0,
        "story_clustering": 0,
        "story_digests": 0,
        "email": 0,
    }

    retry_run = repo.create_pipeline_run(
        trigger_source="api",
        run_type="single_stage",
        requested_stage="story_digests",
        retry_stage_run_id="stage-failed-1",
        requested_hours=24,
        requested_top_n=None,
        profile_slug="default",
        send_email=False,
        status="queued",
    )

    monkeypatch.setattr(
        daily_runner,
        "run_scrapers",
        lambda hours: calls.__setitem__("scraping", calls["scraping"] + 1),
    )
    monkeypatch.setattr(
        daily_runner,
        "process_anthropic_markdown",
        lambda: calls.__setitem__("anthropic_markdown", calls["anthropic_markdown"] + 1),
    )
    monkeypatch.setattr(
        daily_runner,
        "process_youtube_transcripts",
        lambda: calls.__setitem__("youtube_transcripts", calls["youtube_transcripts"] + 1),
    )
    monkeypatch.setattr(
        daily_runner,
        "process_story_clusters",
        lambda hours, repo=None: calls.__setitem__(
            "story_clustering", calls["story_clustering"] + 1
        ),
    )

    def fake_story_digests(repo=None):
        calls["story_digests"] += 1
        return {
            "total": 1,
            "processed": 1,
            "failed": 0,
            "fallback_used": 0,
            "kept_existing": 0,
        }

    monkeypatch.setattr(daily_runner, "process_story_digests", fake_story_digests)
    monkeypatch.setattr(
        daily_runner,
        "run_email_stage",
        lambda **kwargs: calls.__setitem__("email", calls["email"] + 1),
    )

    result = daily_runner.run_daily_pipeline(
        hours=24,
        pipeline_run_id=retry_run.id,
        repo=repo,
    )

    assert result["success"] is True
    assert calls == {
        "scraping": 0,
        "anthropic_markdown": 0,
        "youtube_transcripts": 0,
        "story_clustering": 0,
        "story_digests": 1,
        "email": 0,
    }
    assert [stage["stage_name"] for stage in repo.stage_runs] == ["story_digests"]
    assert repo.stage_runs[0]["retry_of_stage_run_id"] == "stage-failed-1"
    assert repo.completed is not None
