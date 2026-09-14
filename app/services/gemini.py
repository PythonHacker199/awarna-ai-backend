import asyncio
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


def _extract_json(text: str) -> dict[str, Any]:
    """
    Convert Gemini's response into a Python dictionary.
    """

    if not text:
        raise GeminiError("Gemini returned an empty response.")

    text = text.strip()

    # Direct JSON
    try:
        value = json.loads(text)

        if isinstance(value, dict):
            return value

    except json.JSONDecodeError:
        pass

    # Remove markdown code fences if present
    cleaned = text

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1)
        cleaned = cleaned.replace("```", "", 1)
        cleaned = cleaned.strip()

    try:
        value = json.loads(cleaned)

        if isinstance(value, dict):
            return value

    except json.JSONDecodeError:
        pass

    # Last attempt: find first { and last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:

        candidate = cleaned[start : end + 1]

        try:
            value = json.loads(candidate)

            if isinstance(value, dict):
                return value

        except json.JSONDecodeError:
            pass

    raise GeminiError(
        "Gemini returned invalid JSON."
    )


def _is_retryable_error(exc: Exception) -> bool:
    """
    Identify temporary Gemini failures.

    503 / unavailable / overloaded / timeout
    should be retried.
    """

    text = str(exc).lower()

    retry_words = [
        "503",
        "unavailable",
        "high demand",
        "temporarily",
        "timeout",
        "timed out",
        "deadline exceeded",
        "rate limit",
        "429",
        "resource exhausted",
        "internal server error",
        "500",
    ]

    return any(
        word in text
        for word in retry_words
    )


async def _generate(
    client: genai.Client,
    model: str,
    prompt: str,
) -> str:

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:
        raise GeminiError(
            f"Gemini model '{model}' returned no text."
        )

    return text


async def _run_model(
    client: genai.Client,
    model: str,
    prompt: str,
) -> dict[str, Any]:

    last_error: Exception | None = None

    retries = max(
        1,
        settings.GEMINI_RETRIES,
    )

    for attempt in range(retries):

        try:

            logger.info(
                "Calling Gemini model=%s attempt=%s/%s",
                model,
                attempt + 1,
                retries,
            )

            text = await _generate(
                client,
                model,
                prompt,
            )

            return _extract_json(text)

        except Exception as exc:

            last_error = exc

            logger.exception(
                "Gemini model %s failed on attempt %s",
                model,
                attempt + 1,
            )

            # Don't retry permanent errors
            if not _is_retryable_error(exc):
                break

            # Retry delay
            if attempt < retries - 1:

                delay = (
                    settings.GEMINI_RETRY_DELAY_SECONDS
                    * (2 ** attempt)
                )

                logger.warning(
                    "Retrying Gemini model %s in %.1f seconds",
                    model,
                    delay,
                )

                await asyncio.sleep(delay)

    raise GeminiError(
        f"Gemini model '{model}' failed."
    ) from last_error


async def analyze_text(
    ocr_text: str,
) -> dict[str, Any]:

    if not settings.gemini_configured:
        raise GeminiError(
            "GEMINI_API_KEY is not configured."
        )

    if not ocr_text or not ocr_text.strip():
        raise GeminiError(
            "OCR text is empty."
        )

    # Prevent unnecessarily huge requests
    ocr_text = ocr_text[
        : settings.MAX_OCR_CHARS
    ]

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY
    )

    prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + build_text_prompt(ocr_text)
    )

    # ---------------------------------------------------------
    # MODEL CHAIN
    # ---------------------------------------------------------

    models = [
        settings.GEMINI_TEXT_MODEL,
        *settings.GEMINI_FALLBACK_MODELS,
    ]

    # Remove duplicates while preserving order
    unique_models = []

    for model in models:
        if model and model not in unique_models:
            unique_models.append(model)

    last_error: Exception | None = None

    for index, model in enumerate(
        unique_models
    ):

        try:

            logger.info(
                "Trying Gemini provider model=%s",
                model,
            )

            result = await _run_model(
                client,
                model,
                prompt,
            )

            logger.info(
                "Gemini success using model=%s",
                model,
            )

            # Include internal metadata for orchestrator
            result["_provider"] = "gemini"
            result["_model"] = model
            result["_fallback_used"] = index > 0

            return result

        except Exception as exc:

            last_error = exc

            logger.exception(
                "Gemini model chain failed for model=%s",
                model,
            )

            if not settings.ENABLE_FALLBACK:
                break

    raise GeminiError(
        "All Gemini models failed."
    ) from last_error