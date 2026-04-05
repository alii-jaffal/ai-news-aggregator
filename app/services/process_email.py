import logging
from typing import List
from app.agent.email_agent import EmailAgent, RankedArticleDetail, EmailDigestResponse
from app.agent.curator_agent import CuratorAgent
from app.profiles.user_profile import USER_PROFILE
from app.database.repository import Repository
from app.services.email_service import send_email, digest_to_html


logger = logging.getLogger(__name__)


def generate_email_digest(
    hours: int = 24, top_n: int = 10
) -> EmailDigestResponse | None:
    curator = CuratorAgent(USER_PROFILE)
    email_agent = EmailAgent(USER_PROFILE)
    repo = Repository()

    digests = repo.get_recent_digests(hours=hours)
    if not digests:
        logger.info(
            "No digests found from the last %s hours while generating email digest.",
            hours,
        )
        return None

    total = len(digests)

    digest_map = {d["id"]: d for d in digests}

    logger.info("Ranking %s digests for email generation", total)
    ranked_articles = curator.rank_digests(digests)

    if not ranked_articles:
        logger.error("Failed to rank digests")
        raise ValueError("Failed to rank articles")

    ranked_articles = sorted(ranked_articles, key=lambda a: a.rank)

    article_details: List[RankedArticleDetail] = []
    missing = 0

    for a in ranked_articles:
        d = digest_map.get(a.digest_id)
        if not d:
            missing += 1
            d = {}

        article_details.append(
            RankedArticleDetail(
                digest_id=a.digest_id,
                rank=a.rank,
                relevance_score=a.relevance_score,
                reasoning=getattr(a, "reasoning", None),
                title=d.get("title", ""),
                summary=d.get("summary", ""),
                url=d.get("url", ""),
                article_type=d.get("article_type", ""),
            )
        )

    if missing:
        logger.warning(
            "%s ranked items were not found in digest_map (ID mismatch?)", missing
        )

    email_digest = email_agent.create_email_digest_response(
        ranked_articles=article_details,
        total_ranked=len(ranked_articles),
        limit=top_n,
    )

    logger.info("Email digest generated successfully")
    logger.info("=== Email Introduction ===")
    logger.info(email_digest.introduction.greeting)
    logger.info(email_digest.introduction.introduction)

    return email_digest


def send_digest_email(hours: int = 24, top_n: int = 10) -> dict:
    try:
        result = generate_email_digest(hours=hours, top_n=top_n)

        if result is None:
            logger.info("No email digest content available. Skipping email send.")
            return {
                "success": True,
                "sent": False,
                "reason": "no_digests",
                "subject": None,
                "articles_count": 0,
            }

        markdown_content = result.to_markdown()
        html_content = digest_to_html(result)

        greeting = result.introduction.greeting
        date_part = greeting.split("for ", 1)[-1] if "for " in greeting else "Today"
        subject = f"Daily AI News Digest - {date_part}"

        send_email(
            subject=subject,
            body_text=markdown_content,
            body_html=html_content,
        )

        logger.info("Email sent successfully!")
        return {
            "success": True,
            "sent": True,
            "subject": subject,
            "articles_count": len(result.articles),
        }

    except ValueError as e:
        logger.error("Error sending email: %s", e)
        return {
            "success": False,
            "sent": False,
            "error": str(e),
        }
    except Exception:
        logger.exception("Unexpected error sending email")
        return {
            "success": False,
            "sent": False,
            "error": "Unexpected error during email sending",
        }
