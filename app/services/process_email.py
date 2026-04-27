import logging
from dataclasses import dataclass
from typing import Any, List

from app.agent.curator_agent import CuratorAgent
from app.agent.email_agent import EmailAgent, EmailDigestResponse, RankedArticleDetail
from app.database.repository import Repository
from app.profiles.profile_store import get_runtime_user_profile
from app.services.email_service import digest_to_html, send_email

logger = logging.getLogger(__name__)


@dataclass
class EmailDigestPackage:
    response: EmailDigestResponse
    user_profile: dict[str, Any]
    resolved_top_n: int
    subject: str


def _build_subject(email_digest: EmailDigestResponse) -> str:
    greeting = email_digest.introduction.greeting
    date_part = greeting.split("for ", 1)[-1] if "for " in greeting else "Today"
    return f"Daily AI News Digest - {date_part}"


def build_email_digest_package(
    hours: int = 24,
    top_n: int | None = None,
    *,
    repo: Repository | None = None,
) -> EmailDigestPackage | None:
    created_repo = repo is None
    repo = repo or Repository()
    try:
        user_profile = get_runtime_user_profile(repo=repo)
        curator = CuratorAgent(user_profile)
        email_agent = EmailAgent(user_profile)
        resolved_top_n = top_n if top_n is not None else user_profile["newsletter_top_n"]

        digests = repo.get_recent_story_digest_candidates(hours=hours)
        if not digests:
            logger.info(
                "No digests found from the last %s hours while generating email digest.",
                hours,
            )
            return None

        total = len(digests)
        digest_map = {digest["id"]: digest for digest in digests}

        logger.info("Ranking %s digests for email generation", total)
        ranked_articles = curator.rank_digests(digests)
        if not ranked_articles:
            logger.error("Failed to rank digests")
            raise ValueError("Failed to rank articles")

        ranked_articles = sorted(ranked_articles, key=lambda article: article.rank)
        article_details: List[RankedArticleDetail] = []
        missing = 0

        for ranked_article in ranked_articles:
            digest = digest_map.get(ranked_article.digest_id)
            if not digest:
                missing += 1
                digest = {}

            article_details.append(
                RankedArticleDetail(
                    digest_id=ranked_article.digest_id,
                    rank=ranked_article.rank,
                    relevance_score=ranked_article.relevance_score,
                    reasoning=getattr(ranked_article, "reasoning", None),
                    title=digest.get("title", ""),
                    summary=digest.get("summary", ""),
                    url=digest.get("url", ""),
                    article_type=digest.get("article_type", ""),
                    source_attribution_line=digest.get("source_attribution_line"),
                )
            )

        if missing:
            logger.warning("%s ranked items were not found in digest_map (ID mismatch?)", missing)

        email_digest = email_agent.create_email_digest_response(
            ranked_articles=article_details,
            total_ranked=len(ranked_articles),
            limit=resolved_top_n,
        )

        logger.info("Email digest generated successfully")
        logger.info("=== Email Introduction ===")
        logger.info(email_digest.introduction.greeting)
        logger.info(email_digest.introduction.introduction)

        return EmailDigestPackage(
            response=email_digest,
            user_profile=user_profile,
            resolved_top_n=resolved_top_n,
            subject=_build_subject(email_digest),
        )
    finally:
        if created_repo:
            repo.close()


def generate_email_digest(
    hours: int = 24,
    top_n: int | None = None,
    *,
    repo: Repository | None = None,
) -> EmailDigestResponse | None:
    package = build_email_digest_package(hours=hours, top_n=top_n, repo=repo)
    return package.response if package is not None else None


def run_email_stage(
    hours: int = 24,
    top_n: int | None = None,
    *,
    send_email_enabled: bool = True,
    pipeline_run_id: str | None = None,
    repo: Repository | None = None,
) -> dict[str, Any]:
    created_repo = repo is None
    repo = repo or Repository()
    try:
        package = build_email_digest_package(hours=hours, top_n=top_n, repo=repo)
        if package is None:
            logger.info("No email digest content available. Skipping email send.")
            return {
                "success": True,
                "sent": False,
                "reason": "no_digests",
                "subject": None,
                "articles_count": 0,
                "profile_slug": None,
                "resolved_top_n": None,
                "newsletter_run_id": None,
            }

        response = package.response
        newsletter_run = repo.create_newsletter_run(
            pipeline_run_id=pipeline_run_id,
            profile_slug=package.user_profile["slug"],
            window_hours=hours,
            resolved_top_n=package.resolved_top_n,
            subject=package.subject,
            greeting=response.introduction.greeting,
            introduction=response.introduction.introduction,
            sent=False,
            article_count=len(response.articles),
            payload_json=response.model_dump(mode="json"),
        )

        markdown_content = response.to_markdown()
        html_content = digest_to_html(response)

        if send_email_enabled:
            send_email(
                subject=package.subject,
                body_text=markdown_content,
                body_html=html_content,
            )
            repo.mark_newsletter_run_sent(newsletter_run.id, sent=True)
            logger.info("Email sent successfully!")
            return {
                "success": True,
                "sent": True,
                "subject": package.subject,
                "articles_count": len(response.articles),
                "profile_slug": package.user_profile["slug"],
                "resolved_top_n": package.resolved_top_n,
                "newsletter_run_id": newsletter_run.id,
            }

        logger.info("Email delivery skipped because send_email_enabled is False")
        return {
            "success": True,
            "sent": False,
            "reason": "send_disabled",
            "subject": package.subject,
            "articles_count": len(response.articles),
            "profile_slug": package.user_profile["slug"],
            "resolved_top_n": package.resolved_top_n,
            "newsletter_run_id": newsletter_run.id,
        }
    except ValueError as exc:
        logger.error("Error sending email: %s", exc)
        return {
            "success": False,
            "sent": False,
            "error": str(exc),
        }
    except Exception:
        logger.exception("Unexpected error sending email")
        return {
            "success": False,
            "sent": False,
            "error": "Unexpected error during email sending",
        }
    finally:
        if created_repo:
            repo.close()


def send_digest_email(hours: int = 24, top_n: int | None = None) -> dict[str, Any]:
    return run_email_stage(hours=hours, top_n=top_n, send_email_enabled=True)
