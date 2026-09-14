from __future__ import annotations

import logging
from typing import Any

from ..config import settings
from . import gemini
from . import nim

logger = logging.getLogger("awarna.ai")


class AIError(Exception):
    pass


async def analyze_text(
    ocr_text: str,
) -> tuple[dict[str, Any], str, str, bool]:

    providers = []

    if settings.PRIMARY_PROVIDER == "gemini":

        if settings.gemini_configured:
            providers.append("gemini")

        if (
            settings.ENABLE_FALLBACK
            and settings.nvidia_configured
        ):
            providers.append("nvidia")

    else:

        if settings.nvidia_configured:
            providers.append("nvidia")

        if (
            settings.ENABLE_FALLBACK
            and settings.gemini_configured
        ):
            providers.append("gemini")

    if not providers:
        raise AIError(
            "No AI provider is configured."
        )

    last_error = None

    for index, provider in enumerate(providers):

        fallback_used = index > 0

        try:

            if provider == "gemini":

                result = await gemini.analyze_text(
                    ocr_text
                )

                return (
                    result,
                    "gemini",
                    settings.GEMINI_TEXT_MODEL,
                    fallback_used,
                )

            if provider == "nvidia":

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

            logger.warning(
                "%s provider failed: %s",
                provider,
                type(exc).__name__,
            )

            if index + 1 < len(providers):
                logger.warning(
                    "Trying fallback provider..."
                )

    raise AIError(
        "All configured AI providers failed."
    ) from last_error