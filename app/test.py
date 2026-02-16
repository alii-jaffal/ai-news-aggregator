from .database.repository import Repository
from .scrapers.youtube import YouTubeScraper, ChannelVideo
from .config import YOUTUBE_CHANNELS
from typing import List


if __name__ == "__main__":
    repo = Repository()
    scraper = YouTubeScraper()

    total_inserted = 0
    total_fetched = 0

    for channel_id in YOUTUBE_CHANNELS:
        videos: List[ChannelVideo] = scraper.get_latest_videos(channel_id, hours=200)
        total_fetched += len(videos)

        for video in videos:
            created = repo.create_youtube_video(
                video_id=video.video_id,
                title=video.title,
                url=video.url,
                channel_id=channel_id,
                published_at=video.published_at,
                description=video.description,
                transcript=video.transcript
            )

            if created:
                print(f"Inserted: {video.title}")
                total_inserted += 1
            else:
                print(f"Skipped (already exists): {video.title}")

    print(f"\nFetched: {total_fetched}")
    print(f"Inserted: {total_inserted}")
