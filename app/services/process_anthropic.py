import logging
from typing import Optional
from app.scrapers.anthropic import AnthropicScraper
from app.database.repository import Repository

logger = logging.getLogger(__name__)

def process_anthropic_markdown(limit: Optional[int] = None) -> dict:
    scraper = AnthropicScraper()
    repo = Repository()

    logger.info("Starting Anthropic markdown processing")

    articles = repo.get_anthropic_articles_without_markdown(limit=limit)
    processed = 0
    failed = 0

    for article in articles:
        try:
            markdown = scraper.url_to_markdown(article.url)
            if markdown:
                repo.update_anthropic_article_markdown(article.guid, markdown)
                processed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception("Error processing Anthropic article %s", article.guid)
            continue
    
    logger.info(
        "Anthropic markdown processing complete: total=%s processed=%s failed=%s",
        len(articles),
        processed,
        failed,
    )

    return {
        "total": len(articles),
        "processed": processed,
        "failed": failed
    }


if __name__ == "__main__":
    result = process_anthropic_markdown()
    print(result)