from app.database.repository import Repository
from app.worker import run_next_queued_pipeline_run


def test_worker_claims_queued_run_and_updates_heartbeat(db_session, monkeypatch):
    repo = Repository(session=db_session)
    pipeline_run = repo.create_pipeline_run(
        trigger_source="api",
        requested_hours=24,
        requested_top_n=5,
        profile_slug="default",
        send_email=False,
    )
    captured = {}

    def fake_run_daily_pipeline(**kwargs):
        captured.update(kwargs)
        kwargs["repo"].complete_pipeline_run(
            kwargs["pipeline_run_id"],
            scraping_summary={"youtube": 1},
            processing_summary={},
            digest_summary={},
            email_summary={"success": True, "sent": False},
        )
        kwargs["repo"].upsert_worker_heartbeat(
            kwargs["worker_name"],
            status="idle",
            current_run_id=None,
            current_stage_name=None,
        )
        return {"success": True}

    monkeypatch.setattr("app.worker.run_daily_pipeline", fake_run_daily_pipeline)

    processed = run_next_queued_pipeline_run(worker_name="test-worker", repo=repo)
    run_detail = repo.get_pipeline_run_detail(pipeline_run.id)
    worker_status = repo.get_worker_status()

    assert processed is True
    assert captured["pipeline_run_id"] == pipeline_run.id
    assert captured["send_email"] is False
    assert run_detail["status"] == "completed"
    assert worker_status["worker_name"] == "test-worker"
    assert worker_status["status"] == "idle"
