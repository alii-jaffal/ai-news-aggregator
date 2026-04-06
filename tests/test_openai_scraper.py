from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.scrapers.openai import OpenAIScraper


class AttrDict(dict):
    __getattr__ = dict.get


def test_openai_scraper_returns_only_recent_articles(monkeypatch):
    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=1)
    old = now - timedelta(hours=48)

    feed = SimpleNamespace(
        entries=[
            AttrDict(
                title="Recent Article",
                description="Recent description",
                link="https://openai.com/recent",
                id="recent-1",
                published_parsed=recent.timetuple(),
                tags=[{"term": "news"}],
            ),
            AttrDict(
                title="Old Article",
                description="Old description",
                link="https://openai.com/old",
                id="old-1",
                published_parsed=old.timetuple(),
                tags=[{"term": "news"}],
            ),
            AttrDict(
                title="No Date",
                description="No date description",
                link="https://openai.com/no-date",
                id="no-date",
            ),
        ]
    )

    monkeypatch.setattr("app.scrapers.openai.feedparser.parse", lambda _: feed)

    scraper = OpenAIScraper()
    articles = scraper.get_articles(hours=24)

    assert len(articles) == 1
    assert articles[0].guid == "recent-1"
    assert articles[0].title == "Recent Article"
    assert articles[0].category == "news"
