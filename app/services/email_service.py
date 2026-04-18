import html as html_lib
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import markdown

from app.settings import settings

logger = logging.getLogger(__name__)

EMAIL = settings.EMAIL
APP_PASSWORD = settings.APP_PASSWORD


def _wrap_html_body(inner_html: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 24px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        p {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        strong {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        em {{
            font-style: italic;
            color: #666;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 20px 0;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 12px;
        }}
        .introduction {{
            color: #4a4a4a;
            margin-bottom: 20px;
        }}
        .article-link {{
            display: inline-block;
            margin-top: 8px;
            color: #0066cc;
            font-size: 14px;
        }}
        .greeting p {{
            margin: 0;
        }}
        .introduction p {{
            margin: 0;
        }}
        .attribution {{
            color: #666;
            font-size: 13px;
            font-style: italic;
        }}
        div {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        div p {{
            margin: 4px 0;
        }}
    </style>
</head>
<body>
{inner_html}
</body>
</html>"""


def send_email(
    subject: str,
    body_text: str,
    body_html: str | None = None,
    recipients: list[str] | None = None,
) -> None:
    if recipients is None:
        if not EMAIL:
            raise ValueError("EMAIL environment variable is not set")
        recipients = [EMAIL]

    recipients = [recipient.strip() for recipient in recipients if recipient and recipient.strip()]
    if not recipients:
        raise ValueError("No valid recipients provided")

    if not EMAIL:
        raise ValueError("EMAIL environment variable is not set")
    if not APP_PASSWORD:
        raise ValueError("APP_PASSWORD environment variable is not set")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        logger.info("Sending email to %s recipient(s)", len(recipients))
        smtp.login(EMAIL, APP_PASSWORD)
        smtp.sendmail(EMAIL, recipients, msg.as_string())
        logger.info("SMTP send completed successfully")


def markdown_to_html(markdown_text: str) -> str:
    html_body = markdown.markdown(markdown_text, extensions=["extra", "nl2br"])
    return _wrap_html_body(html_body)


def digest_to_html(digest_response) -> str:
    from app.agent.email_agent import EmailDigestResponse

    if not isinstance(digest_response, EmailDigestResponse):
        md = (
            digest_response.to_markdown()
            if hasattr(digest_response, "to_markdown")
            else str(digest_response)
        )
        return markdown_to_html(md)

    html_parts: list[str] = []

    greeting_html = markdown.markdown(
        digest_response.introduction.greeting,
        extensions=["extra", "nl2br"],
    )
    introduction_html = markdown.markdown(
        digest_response.introduction.introduction,
        extensions=["extra", "nl2br"],
    )

    html_parts.append(f'<div class="greeting">{greeting_html}</div>')
    html_parts.append(f'<div class="introduction">{introduction_html}</div>')
    html_parts.append("<hr>")

    for article in digest_response.articles:
        html_parts.append(f"<h3>{html_lib.escape(article.title)}</h3>")

        if article.source_attribution_line:
            html_parts.append(
                f'<p class="attribution">{html_lib.escape(article.source_attribution_line)}</p>'
            )

        summary_html = markdown.markdown(article.summary, extensions=["extra", "nl2br"])
        html_parts.append(f"<div>{summary_html}</div>")

        safe_url = html_lib.escape(article.url)
        html_parts.append(f'<p><a href="{safe_url}" class="article-link">Read more -&gt;</a></p>')
        html_parts.append("<hr>")

    return _wrap_html_body("\n".join(html_parts))


def send_email_to_self(subject: str, body_markdown_or_text: str) -> None:
    if not EMAIL:
        raise ValueError("EMAIL environment variable is not set. Please set it in your .env file.")

    body_html = markdown_to_html(body_markdown_or_text)
    send_email(
        subject=subject,
        body_text=body_markdown_or_text,
        body_html=body_html,
        recipients=[EMAIL],
    )
