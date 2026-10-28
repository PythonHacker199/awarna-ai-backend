import asyncio
import logging

from ..config import settings
from . import gemini


logger = logging.getLogger("awarna.ai")


class AIError(Exception):
    pass


class AITimeoutError(AIError):
    pass


async def analyze_text(
    ocr_text: str,
):

    if not ocr_text or not ocr_text.strip():
        raise AIError(
            "OCR text cannot be empty."
        )

    # ---------------------------------------------------------
    # GEMINI
    # ---------------------------------------------------------

    if settings.gemini_configured:

        try:

            logger.info(
                "Using Gemini AI provider."
            )

            result = await asyncio.wait_for(
                gemini.analyze_text(ocr_text),
                timeout=settings.ANALYZE_BUDGET_SECONDS,
            )

            provider = result.pop(
                "_provider",
                "gemini",
            )

            model = result.pop(
                "_model",
                settings.GEMINI_TEXT_MODEL,
            )

            fallback_used = result.pop(
                "_fallback_used",
                False,
            )

            return (
                result,
                provider,
                model,
                fallback_used,
            )

        except asyncio.TimeoutError as exc:

            logger.error(
                "Gemini analysis exceeded %.0fs budget.",
                settings.ANALYZE_BUDGET_SECONDS,
            )

            raise AITimeoutError(
                "AI analysis took too long. Please try again or enter the details manually."
            ) from exc

        except Exception as exc:

            logger.exception(
                "Gemini provider failed completely."
            )

    else:

        logger.error(
            "Gemini API key is not configured."
        )

    # ---------------------------------------------------------
    # NO OLD NVIDIA FALLBACK
    # ---------------------------------------------------------

    raise AIError(
        "All configured AI providers failed."
    )