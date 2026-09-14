from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from ..config import settings
from .prompts import SYSTEM_PROMPT, build_text_prompt

logger = logging.getLogger("awarna.gemini")


class GeminiError(Exception):
    pass


def _client() -> genai.Client:

    if not settings.gemini_configured:
        raise GeminiError(
            "Gemini API is not configured."
        )

    return genai.Client(
        api_key=settings.GEMINI_API_KEY
    )


def _extract_json(text: str) -> dict[str, Any]:

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise GeminiError(
            "Gemini returned invalid JSON."
        )

    try:
        return json.loads(
            text[start:end + 1]
        )
    except json.JSONDecodeError as exc:
        raise GeminiError(
            "Gemini returned unreadable JSON."
        ) from exc


async def analyze_text(
    ocr_text: str,
) -> dict[str, Any]:

    if not ocr_text.strip():
        raise GeminiError(
            "OCR text is empty."
        )

    try:

        client = _client()

        response = client.models.generate_content(
            model=settings.GEMINI_TEXT_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=(
                                SYSTEM_PROMPT
                                + "\n\n"
                                + build_text_prompt(ocr_text)
                            )
                        )
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )

        if not response.text:
            raise GeminiError(
                "Gemini returned an empty response."
            )

        return _extract_json(response.text)

    except GeminiError:
        raise

    except Exception as exc:

        logger.exception(
            "Gemini text analysis failed"
        )

        raise GeminiError(
            "Gemini AI service failed."
        ) from exc