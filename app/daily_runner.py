import logging
from datetime import datetime

from app.database.repository import Repository
from app.profiles.profile_store import get_runtime_user_profile
from app.runner import run_scrapers
from app.services.process_anthropic import process_anthropic_markdown
from app.services.process_email import run_email_stage
from app.services.process_story_clusters import process_story_clusters
from app.services.process_story_digests import process_story_digests
from app.services.process_youtube import process_youtube_transcripts

logger = logging.getLogger(__name__)


class PipelineRunCancelled(Exception):
    pass


def _touch_worker_heartbeat(
    repo: Repository,
    *,
    worker_name: str | None,
    status: str,
    pipeline_run_id: str | None,
    stage_name: str | None,
) -> None:
    if not worker_name or not hasattr(repo, "upsert_worker_heartbeat"):
        return

    repo.upsert_worker_heartbeat(
        worker_name,
        status=status,
        current_run_id=pipeline_run_id,
        current_stage_name=stage_name,
    )


def run_daily_pipeline(
    hours: int = 24,
    top_n: int | None = None,
    *,
    send_email: bool = True,
    trigger_source: str = "cli",
    pipeline_run_id: str | None = None,
    repo: Repository | None = None,
    worker_name: str | None = None,
) -> dict:
    created_repo = repo is None
    repo = repo or Repository()
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Starting Daily AI News Aggregator Pipeline")
    logger.info("=" * 60)

    results = {
        "start_time": start_time.isoformat(),
        "scraping": {},
        "processing": {},
        "digests": {},
        "email": {},
        "success": False,
    }

    try:
        user_profile = get_runtime_user_profile(repo=repo)
        if pipeline_run_id is None:
            pipeline_run = repo.create_pipeline_run(
                trigger_source=trigger_source,
                requested_hours=hours,
                requested_top_n=top_n,
                profile_slug=user_profile["slug"],
                send_email=send_email,
            )
            pipeline_run_id = pipeline_run.id
        else:
            pipeline_run = repo.get_pipeline_run(pipeline_run_id)
            if pipeline_run is None:
                raise ValueError(f"Pipeline run {pipeline_run_id} does not exist")

        results["pipeline_run_id"] = pipeline_run_id
        repo.mark_pipeline_run_running(pipeline_run_id)
        _touch_worker_heartbeat(
            repo,
            worker_name=worker_name,
            status="running",
            pipeline_run_id=pipeline_run_id,
            stage_name=None,
        )

        def ensure_run_not_cancelled(message: str = "Pipeline run was cancelled") -> None:
            if hasattr(repo, "is_pipeline_run_cancelled") and repo.is_pipeline_run_cancelled(
                pipeline_run_id
            ):
                raise PipelineRunCancelled(message)

        def execute_stage(
            stage_name: str,
            stage_index: int,
            stage_title: str,
            runner,
            *,
            stage_summary_builder=None,
            failure_detector=None,
            failure_message_builder=None,
            on_success=None,
        ):
            ensure_run_not_cancelled()
            logger.info("[%s/6] %s...", stage_index, stage_title)
            _touch_worker_heartbeat(
                repo,
                worker_name=worker_name,
                status="running",
                pipeline_run_id=pipeline_run_id,
                stage_name=stage_name,
            )
            stage_run = repo.start_pipeline_stage_run(
                pipeline_run_id,
                stage_name=stage_name,
            )
            try:
                raw_result = runner()
                stage_summary = (
                    stage_summary_builder(raw_result)
                    if stage_summary_builder is not None
                    else raw_result
                )
                serialized_summary = (
                    stage_summary if isinstance(stage_summary, dict) else {"result": stage_summary}
                )
                if hasattr(repo, "is_pipeline_run_cancelled") and repo.is_pipeline_run_cancelled(
                    pipeline_run_id
                ):
                    repo.cancel_pipeline_stage_run(
                        stage_run.id,
                        error_message="Pipeline run was cancelled",
                        summary_json=serialized_summary,
                    )
                    raise PipelineRunCancelled("Pipeline run was cancelled")
                if failure_detector is not None and failure_detector(raw_result):
                    repo.fail_pipeline_stage_run(
                        stage_run.id,
                        error_message=(
                            failure_message_builder(raw_result)
                            if failure_message_builder is not None
                            else "Stage failed"
                        ),
                        summary_json=serialized_summary,
                    )
                else:
                    repo.complete_pipeline_stage_run(
                        stage_run.id,
                        summary_json=serialized_summary,
                    )
                if on_success is not None:
                    on_success(raw_result, stage_summary)
                return raw_result
            except PipelineRunCancelled:
                raise
            except Exception as exc:
                repo.fail_pipeline_stage_run(
                    stage_run.id,
                    error_message=str(exc),
                )
                raise

        execute_stage(
            "scraping",
            1,
            "Scraping articles from sources",
            lambda: run_scrapers(hours=hours),
            stage_summary_builder=lambda raw: {
                "youtube": len(raw.get("youtube", [])),
                "openai": len(raw.get("openai", [])),
                "anthropic": len(raw.get("anthropic", [])),
            },
            on_success=lambda raw, summary: (
                results.__setitem__("scraping", summary),
                repo.update_pipeline_run_progress(pipeline_run_id, scraping_summary=results["scraping"]),
                logger.info(
                    "Scraped %s YouTube videos, %s OpenAI articles, %s Anthropic articles",
                    summary["youtube"],
                    summary["openai"],
                    summary["anthropic"],
                ),
            ),
        )

        execute_stage(
            "anthropic_markdown",
            2,
            "Processing Anthropic markdown",
            process_anthropic_markdown,
            on_success=lambda raw, summary: (
                results["processing"].__setitem__("anthropic", raw),
                repo.update_pipeline_run_progress(
                    pipeline_run_id,
                    processing_summary=results["processing"],
                ),
                logger.info(
                    "Processed %s Anthropic articles (%s unavailable, %s failed)",
                    raw["processed"],
                    raw["unavailable"],
                    raw["failed"],
                ),
            ),
        )

        execute_stage(
            "youtube_transcripts",
            3,
            "Processing YouTube transcripts",
            process_youtube_transcripts,
            on_success=lambda raw, summary: (
                results["processing"].__setitem__("youtube", raw),
                repo.update_pipeline_run_progress(
                    pipeline_run_id,
                    processing_summary=results["processing"],
                ),
                logger.info(
                    "Processed %s transcripts (%s unavailable, %s failed)",
                    raw["processed"],
                    raw["unavailable"],
                    raw["failed"],
                ),
            ),
        )

        execute_stage(
            "story_clustering",
            4,
            "Clustering source items into stories",
            lambda: process_story_clusters(hours=hours, repo=repo),
            on_success=lambda raw, summary: (
                results["processing"].__setitem__("stories", raw),
                repo.update_pipeline_run_progress(
                    pipeline_run_id,
                    processing_summary=results["processing"],
                ),
                logger.info(
                    "Clustered %s items into %s stories (%s multi-item, %s singleton)",
                    raw["items_considered"],
                    raw["stories"],
                    raw["multi_item_stories"],
                    raw["singleton_stories"],
                ),
            ),
        )

        execute_stage(
            "story_digests",
            5,
            "Creating canonical story digests",
            lambda: process_story_digests(repo=repo),
            on_success=lambda raw, summary: (
                results.__setitem__("digests", raw),
                repo.update_pipeline_run_progress(pipeline_run_id, digest_summary=results["digests"]),
                logger.info(
                    "Created %s story digests (%s failed, %s fallback out of %s total)",
                    raw["processed"],
                    raw["failed"],
                    raw["fallback_used"],
                    raw["total"],
                ),
            ),
        )

        email_result = execute_stage(
            "email",
            6,
            f"Generating and {'sending' if send_email else 'capturing'} email digest",
            lambda: run_email_stage(
                hours=hours,
                top_n=top_n,
                send_email_enabled=send_email,
                pipeline_run_id=pipeline_run_id,
                repo=repo,
            ),
            failure_detector=lambda raw: not raw.get("success", False),
            failure_message_builder=lambda raw: raw.get("error", "Email stage failed"),
            on_success=lambda raw, summary: (
                results.__setitem__("email", raw),
                repo.update_pipeline_run_progress(pipeline_run_id, email_summary=raw),
            ),
        )

        if email_result.get("success") and email_result.get("sent"):
            logger.info(
                "Email sent successfully with %s articles",
                email_result["articles_count"],
            )
            results["success"] = True
        elif email_result.get("success") and not email_result.get("sent"):
            logger.info("Email step skipped: %s", email_result.get("reason", "no_send_needed"))
            results["success"] = True
        else:
            logger.error("Failed to send email: %s", email_result.get("error", "Unknown error"))

    except PipelineRunCancelled as exc:
        logger.info("Pipeline cancelled: %s", exc)
        results["error"] = str(exc)
        results["cancelled"] = True
    except Exception as exc:
        logger.exception("Pipeline failed")
        results["error"] = str(exc)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration

    if pipeline_run_id is not None:
        if results["success"]:
            repo.complete_pipeline_run(
                pipeline_run_id,
                scraping_summary=results["scraping"],
                processing_summary=results["processing"],
                digest_summary=results["digests"],
                email_summary=results["email"],
            )
        else:
            repo.fail_pipeline_run(
                pipeline_run_id,
                error_message=results.get("error")
                or results.get("email", {}).get("error")
                or "Pipeline failed",
                scraping_summary=results["scraping"],
                processing_summary=results["processing"],
                digest_summary=results["digests"],
                email_summary=results["email"],
            )

    logger.info("=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)
    logger.info("Duration: %.1f seconds", duration)
    logger.info("Scraped: %s", results["scraping"])
    logger.info("Processed: %s", results["processing"])
    logger.info("Digests: %s", results["digests"])

    email_result = results.get("email", {})
    if email_result.get("success") and email_result.get("sent"):
        email_status = "Sent"
    elif email_result.get("success") and not email_result.get("sent"):
        email_status = "Skipped"
    else:
        email_status = "Failed"

    logger.info("Email: %s", email_status)
    logger.info("=" * 60)

    _touch_worker_heartbeat(
        repo,
        worker_name=worker_name,
        status="idle" if results["success"] or results.get("cancelled") else "error",
        pipeline_run_id=None,
        stage_name=None,
    )

    if created_repo:
        repo.close()

    return results


if __name__ == "__main__":
    result = run_daily_pipeline(hours=24, top_n=None)
    raise SystemExit(0 if result["success"] else 1)
