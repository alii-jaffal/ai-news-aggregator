import json
import logging
from typing import Optional, Sequence

from google import genai
from pydantic import BaseModel, ValidationError

from app.settings import settings
from app.story_digesting import MAX_STORY_DIGEST_SOURCE_CHARS, StoryDigestSource

logger = logging.getLogger(__name__)


PROMPT = """
You are an expert AI news analyst specializing in story-level synthesis.

Your role is to produce one clean digest for a news story using one or more source items.

Rules:
- Stay grounded in the provided source material only.
- Be honest about source depth and confidence.
- If this is a single-source digest, do not write as if multiple sources confirmed the story.
- If this is a multi-source digest, synthesize shared facts and clearly note
  meaningful disagreements.
- Avoid marketing language and unsupported claims.
- Keep the title concise and specific.
- Keep the summary to 2-3 sentences.
- Keep "why_it_matters" to 1-2 sentences focused on significance or practical implications.
""".strip()


class StoryDigestOutput(BaseModel):
    title: str
    summary: str
    why_it_matters: str
    disagreement_notes: str | None = None


class StoryDigestAgent:
    def __init__(self):
        api_key = settings.DIGEST_GEMINI_API_KEY
        if not api_key:
            raise ValueError("DIGEST_GEMINI_API_KEY is not set in environment /.env")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3-flash-preview"
        self.system_prompt = PROMPT

    def generate_digest(
        self,
        *,
        story_title: str,
        sources: Sequence[StoryDigestSource],
        synthesis_mode: str,
        available_source_count: int,
    ) -> Optional[StoryDigestOutput]:
        try:
            source_payload = [
                {
                    "source_type": source.source_type,
                    "source_id": source.source_id,
                    "url": source.url,
                    "raw_title": source.raw_title,
                    "published_at": source.published_at.isoformat(),
                    "content_source_type": source.content_source_type,
                    "content_richness": source.content_richness,
                    "is_primary": source.is_primary,
                    "cleaned_content": source.cleaned_content[:MAX_STORY_DIGEST_SOURCE_CHARS],
                }
                for source in sources
            ]

            if synthesis_mode == "single_source":
                mode_instruction = (
                    "This is a single-source story digest. "
                    "Do not imply cross-source confirmation or consensus."
                )
            elif synthesis_mode == "fallback_single_source":
                mode_instruction = (
                    "This story has multiple linked sources, but this digest is based only on "
                    "the representative source because broader synthesis failed. "
                    "Acknowledge uncertainty and do not imply full multi-source synthesis."
                )
            else:
                mode_instruction = (
                    "This is a multi-source story digest. Synthesize only claims that are "
                    "supported by the provided sources. If the sources disagree in a meaningful "
                    "way, summarize that in disagreement_notes."
                )

            user_prompt = (
                f"Create a story digest for: {story_title}\n\n"
                f"Synthesis mode: {synthesis_mode}\n"
                f"Available source count: {available_source_count}\n"
                f"Prompt source count: {len(source_payload)}\n\n"
                f"{mode_instruction}\n\n"
                "Return JSON with keys: title, summary, why_it_matters, disagreement_notes.\n"
                "Use null or an empty string for disagreement_notes if there is no meaningful "
                "disagreement.\n\n"
                f"Sources:\n{json.dumps(source_payload, ensure_ascii=True, indent=2)}"
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config={
                    "system_instruction": self.system_prompt,
                    "temperature": 0.3,
                    "response_mime_type": "application/json",
                    "response_schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "why_it_matters": {"type": "string"},
                            "disagreement_notes": {"type": "string"},
                        },
                        "required": ["title", "summary", "why_it_matters"],
                    },
                },
            )

            data = json.loads(response.text)
            output = StoryDigestOutput(**data)
            if output.disagreement_notes is not None and not output.disagreement_notes.strip():
                output.disagreement_notes = None
            return output

        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning(
                "Story digest parsing/validation error: %s | raw_output=%s",
                exc,
                getattr(response, "text", None),
            )
            return None
        except Exception as exc:
            logger.warning("Error generating story digest: %s", exc)
            return None
