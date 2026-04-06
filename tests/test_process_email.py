from app.agent.curator_agent import RankedArticle
from app.agent.email_agent import EmailDigestResponse, EmailIntroduction, RankedArticleDetail
from app.services import process_email


class FakeRepositoryNoDigests:
    def get_recent_digests(self, hours=24):
        return []


class FakeRepositoryWithDigests:
    def get_recent_digests(self, hours=24):
        return [
            {
                "id": "openai:1",
                "article_type": "openai",
                "article_id": "1",
                "url": "https://openai.com/1",
                "title": "OpenAI Story",
                "summary": "Summary text",
                "created_at": None,
            }
        ]


class FakeCuratorAgentSuccess:
    def __init__(self, user_profile):
        self.user_profile = user_profile

    def rank_digests(self, digests):
        return [
            RankedArticle(
                digest_id="openai:1",
                relevance_score=9.5,
                rank=1,
                reasoning="Highly relevant",
            )
        ]


class FakeCuratorAgentFailure:
    def __init__(self, user_profile):
        self.user_profile = user_profile

    def rank_digests(self, digests):
        return []


class FakeEmailAgent:
    def __init__(self, user_profile):
        self.user_profile = user_profile

    def create_email_digest_response(self, ranked_articles, total_ranked, limit):
        return EmailDigestResponse(
            introduction=EmailIntroduction(
                greeting="Hey Ali, here is your digest for today.",
                introduction="One important story today.",
            ),
            articles=[
                RankedArticleDetail(
                    digest_id="openai:1",
                    rank=1,
                    relevance_score=9.5,
                    title="OpenAI Story",
                    summary="Summary text",
                    url="https://openai.com/1",
                    article_type="openai",
                    reasoning="Highly relevant",
                )
            ],
            total_ranked=1,
            top_n=1,
        )


def test_generate_email_digest_returns_none_when_no_digests(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryNoDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)

    result = process_email.generate_email_digest(hours=24, top_n=10)

    assert result is None


def test_send_digest_email_skips_when_no_digests(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryNoDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)

    result = process_email.send_digest_email(hours=24, top_n=10)

    assert result["success"] is True
    assert result["sent"] is False
    assert result["reason"] == "no_digests"


def test_send_digest_email_fails_when_ranking_fails(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryWithDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentFailure)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)

    result = process_email.send_digest_email(hours=24, top_n=10)

    assert result["success"] is False
    assert result["sent"] is False


def test_send_digest_email_happy_path(monkeypatch):
    sent = {"called": False}

    def fake_send_email(subject, body_text, body_html=None, recipients=None):
        sent["called"] = True
        assert "Daily AI News Digest" in subject
        assert "OpenAI Story" in body_text
        assert body_html is not None

    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryWithDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(process_email, "send_email", fake_send_email)

    result = process_email.send_digest_email(hours=24, top_n=10)

    assert sent["called"] is True
    assert result["success"] is True
    assert result["sent"] is True
    assert result["articles_count"] == 1
