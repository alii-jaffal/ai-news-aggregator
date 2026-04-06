from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.scrapers.youtube import YouTubeScraper


class AttrDict(dict):
    __getattr__ = dict.get


class FakeSnippet:
    def __init__(self, text):
        self.text = text


class FakeTranscript:
    def __init__(self, texts):
        self.snippets = [FakeSnippet(t) for t in texts]


def test_extract_video_id_handles_common_url_shapes(monkeypatch):
    monkeypatch.setattr("app.scrapers.youtube.settings.PROXY_USERNAME", None)
    monkeypatch.setattr("app.scrapers.youtube.settings.PROXY_PASSWORD", None)

    scraper = YouTubeScraper()

    assert scraper._extract_video_id("https://www.youtube.com/watch?v=abc123") == "abc123"
    assert scraper._extract_video_id("https://www.youtube.com/shorts/short123") == "short123"
    assert scraper._extract_video_id("https://youtu.be/xyz999") == "xyz999"


def test_get_transcript_joins_snippets(monkeypatch):
    monkeypatch.setattr("app.scrapers.youtube.settings.PROXY_USERNAME", None)
    monkeypatch.setattr("app.scrapers.youtube.settings.PROXY_PASSWORD", None)

    scraper = YouTubeScraper()
    monkeypatch.setattr(
        scraper.transcript_api,
        "fetch",
        lambda video_id: FakeTranscript(["hello", "world"]),
    )

    transcript = scraper.get_transcript("abc123")

    assert transcript is not None
    assert transcript.text == "hello world"


def test_get_latest_videos_skips_old_items_and_shorts(monkeypatch):
    monkeypatch.setattr("app.scrapers.youtube.settings.PROXY_USERNAME", None)
    monkeypatch.setattr("app.scrapers.youtube.settings.PROXY_PASSWORD", None)

    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=1)
    old = now - timedelta(hours=48)

    feed = SimpleNamespace(
        entries=[
            AttrDict(
                title="Recent Normal Video",
                link="https://www.youtube.com/watch?v=video123",
                published_parsed=recent.timetuple(),
                summary="recent summary",
            ),
            AttrDict(
                title="Short Video",
                link="https://www.youtube.com/shorts/short123",
                published_parsed=recent.timetuple(),
                summary="short summary",
            ),
            AttrDict(
                title="Old Video",
                link="https://www.youtube.com/watch?v=old123",
                published_parsed=old.timetuple(),
                summary="old summary",
            ),
        ]
    )

    monkeypatch.setattr("app.scrapers.youtube.feedparser.parse", lambda _: feed)

    scraper = YouTubeScraper()
    videos = scraper.get_latest_videos("channel-1", hours=24)

    assert len(videos) == 1
    assert videos[0].video_id == "video123"
    assert videos[0].title == "Recent Normal Video"
