import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from app.database.repository import Repository
from app.settings import settings
from app.story_clustering import CLUSTER_VERSION, StoryCluster, StoryClusterer, build_source_key

logger = logging.getLogger(__name__)


def process_story_clusters(
    hours: Optional[int] = None,
    repo: Optional[Repository] = None,
    clusterer: Optional[StoryClusterer] = None,
) -> dict[str, Any]:
    repo = repo or Repository()
    clusterer = clusterer or StoryClusterer()

    requested_hours = hours or settings.STORY_CLUSTER_WINDOW_HOURS
    cluster_window_hours = max(requested_hours, settings.STORY_CLUSTER_WINDOW_HOURS)
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=cluster_window_hours)

    logger.info(
        "Starting story clustering for the last %s hours",
        cluster_window_hours,
    )

    items = repo.get_recent_normalized_source_items(hours=cluster_window_hours)
    items_considered = len(items)
    if not items:
        logger.info("No normalized source items available for story clustering")
        return {
            "window_hours": cluster_window_hours,
            "items_considered": 0,
            "stories": 0,
            "multi_item_stories": 0,
            "singleton_stories": 0,
            "links_created": 0,
            "links_updated": 0,
            "stories_created": 0,
            "stories_updated": 0,
        }

    story_link_context = repo.get_story_link_context(hours=cluster_window_hours)
    clusters = clusterer.cluster_items(items)

    story_payloads = []
    reused_story_ids = 0
    for cluster in clusters:
        story_id, reused = choose_story_id(cluster, story_link_context)
        if reused:
            reused_story_ids += 1

        representative = cluster.representative
        links = []
        for member in cluster.members:
            source_key = build_source_key(member.source_type, member.source_id)
            links.append(
                {
                    "source_type": member.source_type,
                    "source_id": member.source_id,
                    "published_at": member.published_at,
                    "similarity_to_primary": cluster.similarity_by_source_key[source_key],
                    "is_primary": source_key
                    == build_source_key(
                        representative.source_type,
                        representative.source_id,
                    ),
                }
            )

        logger.info(
            "Story cluster selected representative %s for %s members",
            build_source_key(representative.source_type, representative.source_id),
            len(cluster.members),
        )
        story_payloads.append(
            {
                "story_id": story_id,
                "title": representative.raw_title,
                "representative_source_type": representative.source_type,
                "representative_source_id": representative.source_id,
                "representative_published_at": representative.published_at,
                "cluster_version": CLUSTER_VERSION,
                "window_start": window_start,
                "window_end": window_end,
                "links": links,
            }
        )

    persistence_result = repo.upsert_story_clusters(story_payloads)

    multi_item_stories = sum(1 for cluster in clusters if len(cluster.members) > 1)
    singleton_stories = sum(1 for cluster in clusters if len(cluster.members) == 1)

    logger.info(
        "Story clustering complete: items=%s stories=%s multi_item=%s singleton=%s "
        "reused_story_ids=%s links_created=%s links_updated=%s",
        items_considered,
        len(clusters),
        multi_item_stories,
        singleton_stories,
        reused_story_ids,
        persistence_result["links_created"],
        persistence_result["links_updated"],
    )

    return {
        "window_hours": cluster_window_hours,
        "items_considered": items_considered,
        "stories": len(clusters),
        "multi_item_stories": multi_item_stories,
        "singleton_stories": singleton_stories,
        "links_created": persistence_result["links_created"],
        "links_updated": persistence_result["links_updated"],
        "stories_created": persistence_result["stories_created"],
        "stories_updated": persistence_result["stories_updated"],
    }


def choose_story_id(
    cluster: StoryCluster,
    story_link_context: Dict[str, dict[str, Any]],
) -> tuple[str, bool]:
    existing_story_ids = []
    for member in cluster.members:
        source_key = build_source_key(member.source_type, member.source_id)
        context = story_link_context.get(source_key)
        if context:
            existing_story_ids.append((context["story_id"], normalize_context_time(context)))

    if not existing_story_ids:
        return str(uuid4()), False

    story_id, _ = sorted(existing_story_ids, key=lambda entry: (entry[1], entry[0]))[0]
    return story_id, True


def normalize_context_time(context: dict[str, Any]) -> float:
    created_at = context.get("story_created_at")
    if created_at is None:
        return float("inf")
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at.timestamp()


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else settings.STORY_CLUSTER_WINDOW_HOURS
    process_story_clusters(hours=hours)
    raise SystemExit(0)
