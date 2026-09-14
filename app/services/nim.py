from __future__ import annotations

import base64
import json
import logging

import httpx

from ..config import settings
from .prompts import (
    SYSTEM_PROMPT,
    build_text_prompt,
    build_image_prompt,
)

logger = logging.getLogger("awarna.nim")


class NimError(Exception):
    """NVIDIA NIM provider error."""


def _extract_json(raw: str) -> dict:
    """Extract JSON even if the model adds markdown fences or extra text."""

    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise NimError(
            "NVIDIA returned invalid JSON."
        )

    try:
        return json.loads(
            raw[start:end + 1]
        )
    except json.JSONDecodeError as exc:
        raise NimError(
            "NVIDIA returned unreadable JSON."
        ) from exc


async def _chat_completion(
    messages: list[dict],
    model: str,
) -> dict:

    if not settings.nvidia_configured:
        raise NimError(
            "NVIDIA NIM is not configured."
        )

    url = (
        f"{settings.NVIDIA_BASE_URL.rstrip('/')}"
        "/chat/completions"
    )

    headers = {
        "Authorization": (
            f"Bearer {settings.NVIDIA_NIM_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 1500,
    }

    try:

        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT_SECONDS
        ) as client:

            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )

    except httpx.TimeoutException as exc:

        raise NimError(
            "NVIDIA AI service timed out."
        ) from exc

    except httpx.ConnectError as exc:

        raise NimError(
            "Could not connect to NVIDIA AI service."
        ) from exc

    except httpx.HTTPError as exc:

        raise NimError(
            "NVIDIA network error."
        ) from exc

    if response.status_code >= 500:

        logger.error(
            "NVIDIA upstream 5xx: %s",
            response.status_code,
        )

        raise NimError(
            "NVIDIA AI service is temporarily unavailable."
        )

    if response.status_code >= 400:

        logger.error(
            "NVIDIA upstream %s: %s",
            response.status_code,
            response.text[:500],
        )

        raise NimError(
            "NVIDIA AI service rejected the request."
        )

    try:

        data = response.json()

    except ValueError as exc:

        raise NimError(
            "NVIDIA returned an unreadable response."
        ) from exc

    try:

        content = (
            data["choices"][0]
            ["message"]["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:

        raise NimError(
            "NVIDIA returned an empty response."
        ) from exc

    if not content or not content.strip():

        raise NimError(
            "NVIDIA returned an empty response."
        )

    return _extract_json(content)


async def analyze_text(
    ocr_text: str,
) -> dict:

    text = ocr_text.strip()

    if not text:
        raise NimError(
            "No OCR text was provided."
        )

    if len(text) > settings.MAX_OCR_CHARS:

        text = text[
            :settings.MAX_OCR_CHARS
        ]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_text_prompt(text),
        },
    ]

    return await _chat_completion(
        messages,
        settings.NVIDIA_TEXT_MODEL,
    )


async def analyze_image(
    image_bytes: bytes,
    content_type: str,
) -> dict:

    if not image_bytes:
        raise NimError(
            "Image is empty."
        )

    encoded = base64.b64encode(
        image_bytes
    ).decode("ascii")

    data_url = (
        f"data:{content_type};base64,{encoded}"
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": build_image_prompt(),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_url,
                    },
                },
            ],
        },
    ]

    return await _chat_completion(
        messages,
        settings.NVIDIA_VISION_MODEL,
    )