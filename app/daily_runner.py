import logging
from datetime import datetime
from app.runner import run_scrapers
from app.services.process_anthropic import process_anthropic_markdown
from app.services.process_youtube import process_youtube_transcripts
from app.services.process_digest import process_digests
from app.services.process_email import send_digest_email


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
        logger.info("[1/5] Scraping articles from sources...")
        scraping_results = run_scrapers(hours=hours)
        results["scraping"] = {
            "youtube": len(scraping_results.get("youtube", [])),
            "openai": len(scraping_results.get("openai", [])),
            "anthropic": len(scraping_results.get("anthropic", [])),
        }
        logger.info(
            f"✓ Scraped {results['scraping']['youtube']} YouTube videos, "
            f"{results['scraping']['openai']} OpenAI articles, "
            f"{results['scraping']['anthropic']} Anthropic articles"
        )

        logger.info("[2/5] Processing Anthropic markdown...")
        anthropic_result = process_anthropic_markdown()
        results["processing"]["anthropic"] = anthropic_result
        logger.info(
            f"✓ Processed {anthropic_result['processed']} Anthropic articles "
            f"({anthropic_result['unavailable']} unavailable, {anthropic_result['failed']} failed)"
        )

        logger.info("[3/5] Processing YouTube transcripts...")
        youtube_result = process_youtube_transcripts()
        results["processing"]["youtube"] = youtube_result
        logger.info(
            f"✓ Processed {youtube_result['processed']} transcripts "
            f"({youtube_result['unavailable']} unavailable)"
        )

        logger.info("[4/5] Creating digests for articles...")
        digest_result = process_digests()
        results["digests"] = digest_result
        logger.info(
            f"✓ Created {digest_result['processed']} digests "
            f"({digest_result['failed']} failed out of {digest_result['total']} total)"
        )

        logger.info("[5/5] Generating and sending email digest...")
        email_result = send_digest_email(hours=hours, top_n=top_n)
        results["email"] = email_result

        if email_result.get("success") and email_result.get("sent"):
            logger.info(
                "✓ Email sent successfully with %s articles",
                email_result["articles_count"],
            )
            results["success"] = True
        elif email_result.get("success") and not email_result.get("sent"):
            logger.info(
                "✓ Email step skipped: %s", email_result.get("reason", "no_send_needed")
            )
            results["success"] = True
        else:
            logger.error(
                "✗ Failed to send email: %s", email_result.get("error", "Unknown error")
            )

    except Exception as e:
        logger.exception("Pipeline failed")
        results["error"] = str(e)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration

    logger.info("=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"Scraped: {results['scraping']}")
    logger.info(f"Processed: {results['processing']}")
    logger.info(f"Digests: {results['digests']}")

    email_result = results.get("email", {})

    if email_result.get("success") and email_result.get("sent"):
        email_status = "Sent"
    elif email_result.get("success") and not email_result.get("sent"):
        email_status = "Skipped"
    else:
        email_status = "Failed"

    logger.info(f"Email: {email_status}")

    logger.info("=" * 60)

    return results


if __name__ == "__main__":
    result = run_daily_pipeline(hours=24, top_n=10)
    exit(0 if result["success"] else 1)
