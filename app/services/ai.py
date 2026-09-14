from __future__ import annotations

import logging
from typing import Any

from ..config import settings
from . import gemini
from . import nim

logger = logging.getLogger("awarna.ai")


class AIError(Exception):
    """Raised when all configured AI providers fail."""


async def analyze_text(
    ocr_text: str,
) -> tuple[dict[str, Any], str, str, bool]:

    if not ocr_text.strip():
        raise AIError(
            "OCR text is empty."
        )

    providers: list[str] = []

    # ==========================================
    # PRIMARY: GEMINI
    # ==========================================

    if settings.PRIMARY_PROVIDER == "gemini":

        if settings.gemini_configured:
            providers.append("gemini")

        if (
            settings.ENABLE_FALLBACK
            and settings.nvidia_configured
        ):
            providers.append("nvidia")

    # ==========================================
    # PRIMARY: NVIDIA
    # ==========================================

    else:

        if settings.nvidia_configured:
            providers.append("nvidia")

        if (
            settings.ENABLE_FALLBACK
            and settings.gemini_configured
        ):
            providers.append("gemini")

    # ==========================================
    # NO PROVIDERS
    # ==========================================

    if not providers:

        raise AIError(
            "No AI provider is configured."
        )

    last_error: Exception | None = None

    # ==========================================
    # TRY PROVIDERS
    # ==========================================

    for index, provider in enumerate(providers):

        fallback_used = index > 0

        try:

            # ----------------------------------
            # GEMINI
            # ----------------------------------

            if provider == "gemini":

                logger.info(
                    "Using Gemini AI provider."
                )

                result = await gemini.analyze_text(
                    ocr_text
                )

                return (
                    result,
                    "gemini",
                    settings.GEMINI_TEXT_MODEL,
                    fallback_used,
                )

            # ----------------------------------
            # NVIDIA
            # ----------------------------------

            if provider == "nvidia":

                logger.info(
                    "Using NVIDIA NIM provider."
                )

                result = await nim.analyze_text(
                    ocr_text
                )

                return (
                    result,
                    "nvidia",
                    settings.NVIDIA_TEXT_MODEL,
                    fallback_used,
                )



        except Exception as exc:

            last_error = exc

            logger.exception("%s provider failed", provider)
            # Try next provider automatically.

            if index + 1 < len(providers):

                logger.info(
                    "Switching to fallback provider."
                )

    # ==========================================
    # EVERYTHING FAILED
    # ==========================================

    raise AIError(
        "All configured AI providers failed."
    ) from last_error