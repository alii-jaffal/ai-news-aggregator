import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, Sequence

from google import genai
from google.genai import types

from app.content_normalization import NormalizedSourceItem
from app.settings import settings

CLUSTER_VERSION = "story-cluster-v1"
EMBEDDING_OUTPUT_DIMENSIONALITY = 768
HIGH_SIMILARITY_THRESHOLD = 0.84
MEDIUM_SIMILARITY_THRESHOLD = 0.78
TITLE_OVERLAP_THRESHOLD = 0.25
TITLE_TOKEN_RE = re.compile(r"[a-z0-9]+")
RICHNESS_PRIORITY = {"missing": 0, "summary": 1, "full": 2}
SOURCE_TYPE_PRIORITY = {"rss": 0, "markdown": 1, "transcript": 2}


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        ...


@dataclass(frozen=True)
class StoryCluster:
    members: List[NormalizedSourceItem]
    representative: NormalizedSourceItem
    similarity_by_source_key: Dict[str, float]


class GeminiEmbeddingProvider:
    def __init__(self):
        self.client = genai.Client(api_key=settings.CURATOR_GEMINI_API_KEY)
        self.model = settings.STORY_EMBEDDING_MODEL

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []

        response = self.client.models.embed_content(
            model=self.model,
            contents=list(texts),
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_OUTPUT_DIMENSIONALITY,
            ),
        )
        return [embedding.values for embedding in response.embeddings]


class StoryClusterer:
    def __init__(self, embedding_provider: Optional[EmbeddingProvider] = None):
        self.embedding_provider = embedding_provider or GeminiEmbeddingProvider()

    def cluster_items(self, items: Sequence[NormalizedSourceItem]) -> List[StoryCluster]:
        if not items:
            return []

        embeddings = self.embedding_provider.embed_texts(
            [build_embedding_text(item) for item in items]
        )
        if len(embeddings) != len(items):
            raise ValueError("Embedding response length did not match candidate item count")

        parent = list(range(len(items)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                if not within_story_time_window(items[left], items[right]):
                    continue

                similarity = cosine_similarity(embeddings[left], embeddings[right])
                overlap = title_token_overlap(items[left].raw_title, items[right].raw_title)
                if should_link_items(similarity, overlap):
                    union(left, right)

        clusters_by_root: Dict[int, List[int]] = {}
        for index in range(len(items)):
            clusters_by_root.setdefault(find(index), []).append(index)

        story_clusters: List[StoryCluster] = []
        for cluster_indexes in clusters_by_root.values():
            cluster_items = [items[index] for index in cluster_indexes]
            representative = choose_representative(cluster_items)
            representative_source_key = build_source_key(
                representative.source_type,
                representative.source_id,
            )
            representative_index = next(
                index
                for index in cluster_indexes
                if build_source_key(items[index].source_type, items[index].source_id)
                == representative_source_key
            )
            similarity_map = {
                build_source_key(item.source_type, item.source_id): cosine_similarity(
                    embeddings[representative_index],
                    embeddings[item_index],
                )
                for item_index, item in zip(cluster_indexes, cluster_items)
            }
            similarity_map[
                build_source_key(
                    representative.source_type,
                    representative.source_id,
                )
            ] = 1.0
            ordered_items = sorted(
                cluster_items,
                key=lambda item: (
                    item is representative,
                    similarity_map[build_source_key(item.source_type, item.source_id)],
                    normalize_datetime(item.published_at),
                ),
                reverse=True,
            )
            story_clusters.append(
                StoryCluster(
                    members=ordered_items,
                    representative=representative,
                    similarity_by_source_key=similarity_map,
                )
            )

        story_clusters.sort(
            key=lambda cluster: normalize_datetime(cluster.representative.published_at),
            reverse=True,
        )
        return story_clusters


def build_source_key(source_type: str, source_id: str) -> str:
    return f"{source_type}:{source_id}"


def build_embedding_text(item: NormalizedSourceItem) -> str:
    return f"{item.raw_title}\n\n{item.cleaned_content[:2000]}"


def normalize_datetime(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def normalize_title_tokens(title: str) -> set[str]:
    return set(TITLE_TOKEN_RE.findall(title.lower()))


def title_token_overlap(left: str, right: str) -> float:
    left_tokens = normalize_title_tokens(left)
    right_tokens = normalize_title_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0

    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    return len(intersection) / len(union)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right:
        return 0.0

    numerator = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0

    return numerator / (left_norm * right_norm)


def within_story_time_window(
    left: NormalizedSourceItem,
    right: NormalizedSourceItem,
    window_hours: int = 72,
) -> bool:
    return abs(normalize_datetime(left.published_at) - normalize_datetime(right.published_at)) <= (
        window_hours * 3600
    )


def should_link_items(similarity: float, title_overlap: float) -> bool:
    return similarity >= HIGH_SIMILARITY_THRESHOLD or (
        similarity >= MEDIUM_SIMILARITY_THRESHOLD and title_overlap >= TITLE_OVERLAP_THRESHOLD
    )

def choose_representative(items: Sequence[NormalizedSourceItem]) -> NormalizedSourceItem:
    if not items:
        raise ValueError("Cannot choose a representative from an empty cluster")

    return sorted(
        items,
        key=lambda item: (
            -RICHNESS_PRIORITY.get(item.content_richness, 0),
            -SOURCE_TYPE_PRIORITY.get(item.content_source_type, 0),
            -normalize_datetime(item.published_at),
            build_source_key(item.source_type, item.source_id),
        ),
    )[0]
