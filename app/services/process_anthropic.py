import logging
from typing import Optional
from app.scrapers.anthropic import AnthropicScraper
from app.database.repository import Repository

logger = logging.getLogger(__name__)


def process_anthropic_markdown(limit: Optional[int] = None) -> dict:
    scraper = AnthropicScraper()
    repo = Repository()

    logger.info("Starting Anthropic markdown processing")

    articles = repo.get_anthropic_articles_pending_markdown(limit=limit)
    processed = 0
    failed = 0
    unavailable = 0

    for article in articles:
        try:
            markdown = scraper.url_to_markdown(article.url)

            if markdown:
                repo.mark_anthropic_markdown_completed(article.guid, markdown)
                processed += 1
            else:
                repo.mark_anthropic_markdown_unavailable(article.guid, "no_markdown_extracted")
                unavailable += 1

        except Exception as e:
            repo.mark_anthropic_markdown_failed(article.guid, type(e).__name__)
            failed += 1
            logger.exception("Error processing Anthropic article %s", article.guid)
            continue

    logger.info(
        "Anthropic markdown processing complete: total=%s processed=%s unavailable=%s failed=%s",
        len(articles),
        processed,
        unavailable,
        failed,
    )

    return {
        "total": len(articles),
        "processed": processed,
        "unavailable": unavailable,
        "failed": failed,
    }
