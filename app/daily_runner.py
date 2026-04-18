import logging
from datetime import datetime

from app.runner import run_scrapers
from app.services.process_anthropic import process_anthropic_markdown
from app.services.process_email import send_digest_email
from app.services.process_story_clusters import process_story_clusters
from app.services.process_story_digests import process_story_digests
from app.services.process_youtube import process_youtube_transcripts

logger = logging.getLogger(__name__)


def run_daily_pipeline(hours: int = 24, top_n: int = 10) -> dict:
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
        logger.info("[1/6] Scraping articles from sources...")
        scraping_results = run_scrapers(hours=hours)
        results["scraping"] = {
            "youtube": len(scraping_results.get("youtube", [])),
            "openai": len(scraping_results.get("openai", [])),
            "anthropic": len(scraping_results.get("anthropic", [])),
        }
        logger.info(
            "Scraped %s YouTube videos, %s OpenAI articles, %s Anthropic articles",
            results["scraping"]["youtube"],
            results["scraping"]["openai"],
            results["scraping"]["anthropic"],
        )

        logger.info("[2/6] Processing Anthropic markdown...")
        anthropic_result = process_anthropic_markdown()
        results["processing"]["anthropic"] = anthropic_result
        logger.info(
            "Processed %s Anthropic articles (%s unavailable, %s failed)",
            anthropic_result["processed"],
            anthropic_result["unavailable"],
            anthropic_result["failed"],
        )

        logger.info("[3/6] Processing YouTube transcripts...")
        youtube_result = process_youtube_transcripts()
        results["processing"]["youtube"] = youtube_result
        logger.info(
            "Processed %s transcripts (%s unavailable, %s failed)",
            youtube_result["processed"],
            youtube_result["unavailable"],
            youtube_result["failed"],
        )

        logger.info("[4/6] Clustering source items into stories...")
        story_result = process_story_clusters(hours=hours)
        results["processing"]["stories"] = story_result
        logger.info(
            "Clustered %s items into %s stories (%s multi-item, %s singleton)",
            story_result["items_considered"],
            story_result["stories"],
            story_result["multi_item_stories"],
            story_result["singleton_stories"],
        )

        logger.info("[5/6] Creating canonical story digests...")
        digest_result = process_story_digests()
        results["digests"] = digest_result
        logger.info(
            "Created %s story digests (%s failed, %s fallback out of %s total)",
            digest_result["processed"],
            digest_result["failed"],
            digest_result["fallback_used"],
            digest_result["total"],
        )

        logger.info("[6/6] Generating and sending email digest...")
        email_result = send_digest_email(hours=hours, top_n=top_n)
        results["email"] = email_result

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

    except Exception as exc:
        logger.exception("Pipeline failed")
        results["error"] = str(exc)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration

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

    return results


if __name__ == "__main__":
    result = run_daily_pipeline(hours=24, top_n=10)
    raise SystemExit(0 if result["success"] else 1)
