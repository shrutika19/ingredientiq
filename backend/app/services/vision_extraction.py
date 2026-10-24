
import logging

from google.genai import types

from app.core.config import get_settings
from app.services.gemini_client import create_gemini_client

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
Extract only the ingredient list visibly printed on this skincare
product label.

Rules:
- Transcribe ingredient names in their original order.
- Preserve spelling as closely as possible.
- Do not invent, correct, or infer missing ingredients.
- Do not analyze safety, benefits, or ingredient functions.
- Ignore marketing text, directions, and brand names.
- If no readable ingredient list is present, return an empty string.
- Return only the ingredient list as plain text.
"""


def extract_ingredient_text(image_bytes: bytes, mime_type: str) -> str:
    settings = get_settings()

    with create_gemini_client() as client:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                EXTRACTION_PROMPT,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type,
                ),
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=2048,
            ),
        )

    return (response.text or "").strip()
