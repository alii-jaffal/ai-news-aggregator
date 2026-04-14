from datetime import datetime, timezone
from types import SimpleNamespace

from app.content_normalization import NormalizedSourceItem
from app.services import process_digest


class FakeRepository:
    def __init__(self):
        self.created = []
        self.completed = []
        self.failed = []

    def get_articles_pending_digest(self, limit=None):
        return [
            NormalizedSourceItem(
                source_type="openai",
                source_id="openai-1",
                url="https://openai.com/1",
                raw_title="OpenAI RSS Story",
                raw_summary="Summary",
                cleaned_content="Summary",
                published_at=datetime.now(timezone.utc),
                content_length=len("Summary"),
                content_richness="summary",
                content_source_type="rss",
            )
        ]

    def create_digest(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(**kwargs)

    def mark_digest_completed(self, article_type, article_id):
        self.completed.append((article_type, article_id))
        return True

    def mark_digest_failed(self, article_type, article_id, reason):
        self.failed.append((article_type, article_id, reason))
        return True


class FakeDigestAgent:
    def __init__(self):
        self.calls = []

    def generate_digest(
        self,
        title,
        content,
        article_type,
        content_source_type,
        content_richness,
    ):
        self.calls.append(
            {
                "title": title,
                "content": content,
                "article_type": article_type,
                "content_source_type": content_source_type,
                "content_richness": content_richness,
            }
        )
        return SimpleNamespace(title="Digest Title", summary="Digest Summary")


def test_process_digests_passes_normalized_metadata(monkeypatch):
    fake_repo = FakeRepository()
    fake_agent = FakeDigestAgent()

    monkeypatch.setattr(process_digest, "Repository", lambda: fake_repo)
    monkeypatch.setattr(process_digest, "DigestAgent", lambda: fake_agent)

    result = process_digest.process_digests()

    assert result == {"total": 1, "processed": 1, "failed": 0}
    assert fake_agent.calls == [
        {
            "title": "OpenAI RSS Story",
            "content": "Summary",
            "article_type": "openai",
            "content_source_type": "rss",
            "content_richness": "summary",
        }
    ]
    assert fake_repo.created[0]["article_type"] == "openai"
    assert fake_repo.completed == [("openai", "openai-1")]
