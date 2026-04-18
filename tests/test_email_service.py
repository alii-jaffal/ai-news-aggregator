from app.agent.email_agent import EmailDigestResponse, EmailIntroduction, RankedArticleDetail
from app.services import email_service


def test_markdown_to_html_wraps_html():
    html = email_service.markdown_to_html("## Title\n\nHello world")

    assert "<html>" in html
    assert "<h2>" in html
    assert "Title" in html
    assert "Hello world" in html


def test_digest_to_html_renders_email_digest_response():
    digest = EmailDigestResponse(
        introduction=EmailIntroduction(
            greeting="Hey Ali, here is your digest.",
            introduction="Top stories today.",
        ),
        articles=[
            RankedArticleDetail(
                digest_id="openai:1",
                rank=1,
                relevance_score=9.5,
                title="OpenAI Story",
                summary="A useful summary.",
                url="https://openai.com/story",
                article_type="story",
                reasoning="Very relevant",
                source_attribution_line="Source: OpenAI",
            )
        ],
        total_ranked=1,
        top_n=1,
    )

    html = email_service.digest_to_html(digest)

    assert "Hey Ali, here is your digest." in html
    assert "OpenAI Story" in html
    assert "A useful summary." in html
    assert "Source: OpenAI" in html
    assert "https://openai.com/story" in html


def test_send_email_calls_smtp(monkeypatch):
    calls = {"login": None, "sendmail": None}

    class FakeSMTP:
        def __init__(self, host, port):
            assert host == "smtp.gmail.com"
            assert port == 465

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, email, password):
            calls["login"] = (email, password)

        def sendmail(self, sender, recipients, message):
            calls["sendmail"] = (sender, recipients, message)

    monkeypatch.setattr(email_service, "EMAIL", "sender@example.com")
    monkeypatch.setattr(email_service, "APP_PASSWORD", "app-password")
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", FakeSMTP)

    email_service.send_email(
        subject="Test Subject",
        body_text="plain body",
        body_html="<p>html body</p>",
        recipients=["receiver@example.com"],
    )

    assert calls["login"] == ("sender@example.com", "app-password")
    assert calls["sendmail"][0] == "sender@example.com"
    assert calls["sendmail"][1] == ["receiver@example.com"]
    assert "Test Subject" in calls["sendmail"][2]


def test_send_email_raises_for_empty_recipients(monkeypatch):
    monkeypatch.setattr(email_service, "EMAIL", "sender@example.com")
    monkeypatch.setattr(email_service, "APP_PASSWORD", "app-password")

    try:
        email_service.send_email(
            subject="Test Subject",
            body_text="plain body",
            recipients=[],
        )
    except ValueError as e:
        assert str(e) == "No valid recipients provided"
    else:
        raise AssertionError("Expected ValueError for empty recipients")
