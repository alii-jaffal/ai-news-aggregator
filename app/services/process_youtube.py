import logging
from typing import Optional
from app.scrapers.youtube import YouTubeScraper
from app.database.repository import Repository

logger = logging.getLogger(__name__)


def process_youtube_transcripts(limit: Optional[int] = None) -> dict:
    scraper = YouTubeScraper()
    repo = Repository()

    logger.info("Starting YouTube transcript processing")

    videos = repo.get_youtube_videos_pending_transcript(limit=limit)
    processed = 0
    unavailable = 0
    failed = 0

    for video in videos:
        try:
            transcript_result = scraper.get_transcript(video.video_id)

            if transcript_result:
                repo.mark_youtube_transcript_completed(video.video_id, transcript_result.text)
                processed += 1
            else:
                repo.mark_youtube_transcript_unavailable(video.video_id, "transcript_not_available")
                unavailable += 1
                logger.warning("Transcript unavailable for video %s", video.video_id)

        except Exception as e:
            repo.mark_youtube_transcript_failed(video.video_id, type(e).__name__)
            failed += 1
            logger.exception("Error processing video %s", video.video_id)

    logger.info(
        "YouTube transcript processing complete: total=%s processed=%s unavailable=%s failed=%s",
        len(videos),
        processed,
        unavailable,
        failed,
    )

    return {
        "total": len(videos),
        "processed": processed,
        "unavailable": unavailable,
        "failed": failed,
    }
