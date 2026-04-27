from app.agent.curator_agent import RankedArticle
from app.agent.email_agent import EmailDigestResponse, EmailIntroduction, RankedArticleDetail
from app.database.repository import Repository
from app.services import process_email


class FakeRepositoryNoDigests:
    def get_recent_story_digest_candidates(self, hours=24):
        return []

    def close(self):
        return None


class FakeRepositoryWithDigests:
    def __init__(self):
        self.newsletter_runs = {}

    def get_recent_story_digest_candidates(self, hours=24):
        return [
            {
                "id": "story:story-1",
                "story_id": "story-1",
                "article_type": "story",
                "url": "https://openai.com/1",
                "title": "OpenAI Story Digest",
                "summary": "Summary text",
                "why_it_matters": "Why it matters text",
                "created_at": None,
                "story_source_count": 1,
                "source_types": ["openai"],
                "synthesis_mode": "single_source",
                "source_attribution_line": "Source: OpenAI",
            }
        ]

    def create_newsletter_run(self, **kwargs):
        run = type("NewsletterRun", (), {"id": "newsletter-1"})()
        self.newsletter_runs[run.id] = {"kwargs": kwargs, "sent": False}
        return run

    def mark_newsletter_run_sent(self, newsletter_run_id, sent=True):
        self.newsletter_runs[newsletter_run_id]["sent"] = sent
        return type("NewsletterRun", (), {"id": newsletter_run_id, "sent": sent})()

    def close(self):
        return None


class FakeCuratorAgentSuccess:
    last_user_profile = None

    def __init__(self, user_profile):
        FakeCuratorAgentSuccess.last_user_profile = user_profile
        self.user_profile = user_profile

    def rank_digests(self, digests):
        return [
            RankedArticle(
                digest_id="story:story-1",
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
    last_user_profile = None
    last_limit = None

    def __init__(self, user_profile):
        FakeEmailAgent.last_user_profile = user_profile
        self.user_profile = user_profile

    def create_email_digest_response(self, ranked_articles, total_ranked, limit):
        FakeEmailAgent.last_limit = limit
        return EmailDigestResponse(
            introduction=EmailIntroduction(
                greeting="Hey Ali, here is your digest for today.",
                introduction="One important story today.",
            ),
            articles=[
                RankedArticleDetail(
                    digest_id="story:story-1",
                    rank=1,
                    relevance_score=9.5,
                    title="OpenAI Story Digest",
                    summary="Summary text",
                    url="https://openai.com/1",
                    article_type="story",
                    reasoning="Highly relevant",
                    source_attribution_line="Source: OpenAI",
                )
            ],
            total_ranked=1,
            top_n=1,
        )


def fake_runtime_profile(newsletter_top_n=10):
    return {
        "id": "profile-1",
        "slug": "default",
        "name": "Ali Jaffal",
        "title": "AI Engineer",
        "background": "Builds AI systems",
        "expertise_level": "Intermediate",
        "interests": ["agents"],
        "preferred_source_types": ["openai", "youtube"],
        "preferences": {"prefer_practical": True},
        "newsletter_top_n": newsletter_top_n,
    }


def test_generate_email_digest_returns_none_when_no_digests(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryNoDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(
        process_email,
        "get_runtime_user_profile",
        lambda repo=None: fake_runtime_profile(),
    )

    result = process_email.generate_email_digest(hours=24, top_n=None)

    assert result is None


def test_send_digest_email_skips_when_no_digests(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryNoDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(
        process_email,
        "get_runtime_user_profile",
        lambda repo=None: fake_runtime_profile(),
    )

    result = process_email.send_digest_email(hours=24, top_n=None)

    assert result["success"] is True
    assert result["sent"] is False
    assert result["reason"] == "no_digests"


def test_send_digest_email_fails_when_ranking_fails(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryWithDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentFailure)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(
        process_email,
        "get_runtime_user_profile",
        lambda repo=None: fake_runtime_profile(),
    )

    result = process_email.send_digest_email(hours=24, top_n=None)

    assert result["success"] is False
    assert result["sent"] is False


def test_send_digest_email_happy_path(monkeypatch):
    sent = {"called": False}
    repo = FakeRepositoryWithDigests()

    def fake_send_email(subject, body_text, body_html=None, recipients=None):
        sent["called"] = True
        assert "Daily AI News Digest" in subject
        assert "OpenAI Story Digest" in body_text
        assert "Source: OpenAI" in body_text
        assert body_html is not None

    monkeypatch.setattr(process_email, "Repository", lambda: repo)
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(process_email, "send_email", fake_send_email)
    monkeypatch.setattr(
        process_email,
        "get_runtime_user_profile",
        lambda repo=None: fake_runtime_profile(),
    )

    result = process_email.send_digest_email(hours=24, top_n=10)

    assert sent["called"] is True
    assert result["success"] is True
    assert result["sent"] is True
    assert result["articles_count"] == 1
    assert repo.newsletter_runs["newsletter-1"]["sent"] is True


def test_generate_email_digest_uses_profile_default_top_n(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryWithDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(
        process_email,
        "get_runtime_user_profile",
        lambda repo=None: fake_runtime_profile(newsletter_top_n=3),
    )

    process_email.generate_email_digest(hours=24, top_n=None)

    assert FakeEmailAgent.last_limit == 3
    assert FakeCuratorAgentSuccess.last_user_profile["name"] == "Ali Jaffal"
    assert FakeCuratorAgentSuccess.last_user_profile["preferred_source_types"] == [
        "openai",
        "youtube",
    ]


def test_generate_email_digest_prefers_explicit_top_n_over_profile_default(monkeypatch):
    monkeypatch.setattr(process_email, "Repository", lambda: FakeRepositoryWithDigests())
    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(
        process_email,
        "get_runtime_user_profile",
        lambda repo=None: fake_runtime_profile(newsletter_top_n=5),
    )

    process_email.generate_email_digest(hours=24, top_n=1)

    assert FakeEmailAgent.last_limit == 1


def test_run_email_stage_persists_snapshot_without_sending(monkeypatch, db_session):
    repo = Repository(session=db_session)
    repo.get_recent_story_digest_candidates = lambda hours=24: [
        {
            "id": "story:story-1",
            "story_id": "story-1",
            "article_type": "story",
            "url": "https://openai.com/1",
            "title": "OpenAI Story Digest",
            "summary": "Summary text",
            "why_it_matters": "Why it matters text",
            "created_at": None,
            "story_source_count": 1,
            "source_types": ["openai"],
            "synthesis_mode": "single_source",
            "source_attribution_line": "Source: OpenAI",
        }
    ]

    monkeypatch.setattr(process_email, "CuratorAgent", FakeCuratorAgentSuccess)
    monkeypatch.setattr(process_email, "EmailAgent", FakeEmailAgent)
    monkeypatch.setattr(
        process_email,
        "get_runtime_user_profile",
        lambda repo=None: fake_runtime_profile(newsletter_top_n=4),
    )

    result = process_email.run_email_stage(
        hours=24,
        top_n=None,
        send_email_enabled=False,
        pipeline_run_id="run-1",
        repo=repo,
    )

    newsletters = repo.list_newsletter_runs(limit=10, offset=0)

    assert result["success"] is True
    assert result["sent"] is False
    assert result["reason"] == "send_disabled"
    assert newsletters["total"] == 1
    assert newsletters["items"][0]["sent"] is False
    assert newsletters["items"][0]["profile_slug"] == "default"
