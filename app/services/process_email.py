import logging
from dotenv import load_dotenv

load_dotenv()

from app.agent.email_agent import EmailAgent, RankedArticleDetail, EmailDigestResponse
from app.agent.curator_agent import CuratorAgent
from app.profiles.user_profile import USER_PROFILE
from app.database.repository import Repository
from app.services.email_service import send_email, digest_to_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_email_digest(hours: int = 24, top_n: int = 10) -> EmailDigestResponse:
    curator = CuratorAgent(USER_PROFILE)
    email_agent = EmailAgent(USER_PROFILE)
    repo = Repository()

    digests = repo.get_recent_digests(hours=hours)
    total = len(digests)

    if total == 0:
        logger.warning(f"No digests found from the last {hours} hours")
        raise ValueError("No digests available")

    digest_map = {d["id"]: d for d in digests}

    logger.info(f"Ranking {total} digests for email generation")
    ranked_articles = curator.rank_digests(digests)

    if not ranked_articles:
        logger.error("Failed to rank digests")
        raise ValueError("Failed to rank articles")

    ranked_articles = sorted(ranked_articles, key=lambda a: a.rank)

    logger.info(f"Generating email digest with top {top_n} articles")

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
        logger.warning(f"{missing} ranked items were not found in digest_map (ID mismatch?)")

    email_digest = email_agent.create_email_digest_response(
        ranked_articles=article_details,
        total_ranked=len(ranked_articles),
        limit=top_n,
    )

    logger.info("Email digest generated successfully")
    logger.info("\n=== Email Introduction ===")
    logger.info(email_digest.introduction.greeting)
    logger.info(f"\n{email_digest.introduction.introduction}")

    return email_digest


def send_digest_email(hours: int = 24, top_n: int = 10) -> dict:
    try:
        result = generate_email_digest(hours=hours, top_n=top_n)

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
            "subject": subject,
            "articles_count": len(result.articles),
        }

    except ValueError as e:
        logger.error(f"Error sending email: {e}")
        return {
            "success": False,
            "error": str(e),
        }
    except Exception as e:
        logger.exception(f"Unexpected error sending email: {e}")
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
        }


if __name__ == "__main__":
    result = send_digest_email(hours=24, top_n=10)
    if result.get("success"):
        print("\n=== Email Digest Sent ===")
        print(f"Subject: {result['subject']}")
        print(f"Articles: {result['articles_count']}")
    else:
        print(f"Error: {result.get('error')}")