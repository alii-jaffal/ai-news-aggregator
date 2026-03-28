from app.settings import settings
import json
from typing import Optional
from pydantic import BaseModel, ValidationError
from google import genai




PROMPT = """
    You are an expert AI news analyst specializing in summarizing technical articles, research papers, and video content about artificial intelligence.

    Your role is to create concise, informative digests that help readers quickly understand the key points and significance of AI-related content.

    Guidelines:
    - Create a compelling title (5-10 words) that captures the essence of the content
    - Write a 2-3 sentence summary that highlights the main points and why they matter
    - Focus on actionable insights and implications
    - Use clear, accessible language while maintaining technical accuracy
    - Avoid marketing fluff - focus on substance
"""



class DigestOutput(BaseModel):
    title: str
    summary: str



class DigestAgent:
    def __init__(self):
        api_key = settings.DIGEST_GEMINI_API_KEY
        if not api_key:
            raise ValueError("DIGEST_GEMINI_API_KEY is not set in environment /.env")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3-flash-preview"
        self.system_prompt = PROMPT

    def generate_digest(self, title: str, content: str, article_type: str) -> Optional[DigestOutput]:
        try:
            user_prompt = (
                f"Create a digest for this {article_type}.\n\n"
                f"Input title:\n{title}\n\n"
                f"Content:\n{content[:8000]}"
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
                        },
                        "required": ["title", "summary"]
                    },
                },
            )

            data = json.loads(response.text)
            return DigestOutput(**data)

        except (json.JSONDecodeError, ValidationError) as e:
            print(f"Digest output parsing/validation error: {e}\nRaw output: {getattr(response, 'text', None)}")
            return None
        except Exception as e:
            print(f"Error generating digest: {e}")
            return None
