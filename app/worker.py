import logging
import time

from app.daily_runner import run_daily_pipeline
from app.database.repository import Repository

logger = logging.getLogger(__name__)

DEFAULT_WORKER_NAME = "dashboard-worker"


def run_next_queued_pipeline_run(
    *,
    worker_name: str = DEFAULT_WORKER_NAME,
    repo: Repository | None = None,
) -> bool:
    created_repo = repo is None
    repo = repo or Repository()

    try:
        repo.upsert_worker_heartbeat(
            worker_name,
            status="idle",
            current_run_id=None,
            current_stage_name=None,
        )
        pipeline_run = repo.claim_next_queued_pipeline_run()
        if pipeline_run is None:
            return False

        logger.info("Worker %s claimed pipeline run %s", worker_name, pipeline_run.id)
        repo.upsert_worker_heartbeat(
            worker_name,
            status="running",
            current_run_id=pipeline_run.id,
            current_stage_name=None,
        )
        run_daily_pipeline(
            hours=pipeline_run.requested_hours,
            top_n=pipeline_run.requested_top_n,
            send_email=pipeline_run.send_email,
            trigger_source=pipeline_run.trigger_source,
            pipeline_run_id=pipeline_run.id,
            repo=repo,
            worker_name=worker_name,
        )
        return True
    finally:
        if created_repo:
            repo.close()


def run_worker_loop(
    *,
    worker_name: str = DEFAULT_WORKER_NAME,
    poll_interval_seconds: float = 3.0,
) -> None:
    logger.info(
        "Starting pipeline worker %s with poll interval %.1fs",
        worker_name,
        poll_interval_seconds,
    )
    while True:
        processed = run_next_queued_pipeline_run(worker_name=worker_name)
        if not processed:
            time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    run_worker_loop()
