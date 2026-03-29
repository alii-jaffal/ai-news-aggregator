import logging
from typing import List
from .config import YOUTUBE_CHANNELS
from .scrapers.youtube import YouTubeScraper, ChannelVideo
from .scrapers.openai import OpenAIScraper, OpenAIArticle
from .scrapers.anthropic import AnthropicScraper, AnthropicArticle
from .database.repository import Repository

logger = logging.getLogger(__name__)

def run_scrapers(hours: int = 24) -> dict:
    youtube_scraper = YouTubeScraper()
    openai_scraper = OpenAIScraper()
    anthropic_scraper = AnthropicScraper()
    repo = Repository()
    
    youtube_videos = []
    video_dicts = []

    logger.info("Starting scraper run for the last %s hours", hours)

    for channel_id in YOUTUBE_CHANNELS:
        videos = youtube_scraper.get_latest_videos(channel_id, hours=hours)
        logger.info("Scraped %s YouTube videos from channel %s", len(videos), channel_id)
        youtube_videos.extend(videos)
        video_dicts.extend([
            {
                "video_id": v.video_id,
                "title": v.title,
                "url": v.url,
                "channel_id": channel_id,
                "published_at": v.published_at,
                "description": v.description,
                "transcript": v.transcript
            }
            for v in videos
        ])
    
    openai_articles = openai_scraper.get_articles(hours=hours)
    logger.info("Scraped %s OpenAI articles", len(openai_articles))

    anthropic_articles = anthropic_scraper.get_articles(hours=hours)
    logger.info("Scraped %s Anthropic articles", len(anthropic_articles))

    
    if video_dicts:
        repo.bulk_create_youtube_videos(video_dicts)
    
    if openai_articles:
        article_dicts = [
            {
                "guid": a.guid,
                "title": a.title,
                "url": a.url,
                "published_at": a.published_at,
                "description": a.description,
                "category": a.category
            }
            for a in openai_articles
        ]
        repo.bulk_create_openai_articles(article_dicts)
    
    if anthropic_articles:
        article_dicts = [
            {
                "guid": a.guid,
                "title": a.title,
                "url": a.url,
                "published_at": a.published_at,
                "description": a.description,
                "category": a.category
            }
            for a in anthropic_articles
        ]
        repo.bulk_create_anthropic_articles(article_dicts)
    
    logger.info(
        "Scraper run complete: youtube=%s openai=%s anthropic=%s",
        len(youtube_videos),
        len(openai_articles),
        len(anthropic_articles),
    )
    
    return {
        "youtube": youtube_videos,
        "openai": openai_articles,
        "anthropic": anthropic_articles,
    }
