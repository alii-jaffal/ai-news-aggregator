import logging
import sys
from typing import Any, Optional

from app.agent.story_digest_agent import StoryDigestAgent
from app.database.repository import Repository
from app.story_digesting import select_story_digest_sources

logger = logging.getLogger(__name__)


def process_story_digests(
    limit: Optional[int] = None,
    repo: Optional[Repository] = None,
    agent: Optional[StoryDigestAgent] = None,
) -> dict[str, Any]:
    repo = repo or Repository()
    agent = agent or StoryDigestAgent()

    stories = repo.get_stories_pending_story_digest(limit=limit)
    total = len(stories)
    processed = 0
    failed = 0
    fallback_used = 0
    kept_existing = 0

    logger.info("Starting story digest processing for %s stories", total)

    for idx, story in enumerate(stories, 1):
        logger.info(
            "[%s/%s] Processing story %s with %s source(s)",
            idx,
            total,
            story.story_id,
            story.source_count,
        )

        representative = next(
            (member for member in story.members if member.is_primary),
            story.members[0],
        )
        primary_sources = (
            [representative]
            if story.source_count == 1
            else select_story_digest_sources(story.members)
        )
        synthesis_mode = "single_source" if story.source_count == 1 else "multi_source"

        result = agent.generate_digest(
            story_title=story.story_title,
            sources=primary_sources,
            synthesis_mode=synthesis_mode,
            available_source_count=story.source_count,
        )

        if result is None and story.source_count > 1:
            logger.warning(
                "Multi-source story digest failed for %s; retrying with representative source only",
                story.story_id,
            )
            result = agent.generate_digest(
                story_title=story.story_title,
                sources=[representative],
                synthesis_mode="fallback_single_source",
                available_source_count=story.source_count,
            )
            if result is not None:
                synthesis_mode = "fallback_single_source"
                primary_sources = [representative]
                fallback_used += 1

        if result is not None:
            repo.upsert_story_digest(
                story_id=story.story_id,
                title=result.title,
                summary=result.summary,
                why_it_matters=result.why_it_matters,
                disagreement_notes=result.disagreement_notes,
                synthesis_mode=synthesis_mode,
                available_source_count=story.source_count,
                used_source_count=len(primary_sources),
                generated_input_hash=story.story_digest_input_hash,
            )
            processed += 1
            continue

        current_story_digest = repo.get_current_story_digest(story.story_id)
        if current_story_digest is not None:
            repo.upsert_story_digest(
                story_id=story.story_id,
                title=current_story_digest.title,
                summary=current_story_digest.summary,
                why_it_matters=current_story_digest.why_it_matters,
                disagreement_notes=current_story_digest.disagreement_notes,
                synthesis_mode=current_story_digest.synthesis_mode,
                available_source_count=current_story_digest.available_source_count,
                used_source_count=current_story_digest.used_source_count,
                generated_input_hash=current_story_digest.generated_input_hash,
            )
            kept_existing += 1
            logger.warning(
                "Keeping existing matching story digest for %s after generation failure",
                story.story_id,
            )
            continue

        failed += 1
        repo.mark_story_digest_failed(story.story_id, "story_digest_generation_failed")
        logger.warning("Failed to generate story digest for %s", story.story_id)

    logger.info(
        "Story digest processing complete: %s processed, %s failed, %s fallback, %s kept_existing "
        "out of %s total",
        processed,
        failed,
        fallback_used,
        kept_existing,
        total,
    )

    return {
        "total": total,
        "processed": processed,
        "failed": failed,
        "fallback_used": fallback_used,
        "kept_existing": kept_existing,
    }


if __name__ == "__main__":
    digest_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    process_story_digests(limit=digest_limit)
    raise SystemExit(0)
