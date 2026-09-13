from __future__ import annotations

import base64
import json
import logging
from typing import Optional

import httpx

from ..config import settings
from .prompts import SYSTEM_PROMPT, build_text_user_prompt, build_vision_user_prompt

logger = logging.getLogger("awarna.nim")


class NimError(Exception):
    """Raised for any failure talking to NVIDIA NIM. The message is always
    safe to show to an end user — never includes the API key or raw
    upstream stack traces."""


def _extract_json_object(raw: str) -> dict:
    """Model responses occasionally wrap JSON in markdown fences or add
    stray text around it despite instructions. Try straight parsing first,
    then fall back to locating the outermost {...} block."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise NimError("The AI response was not valid JSON.")
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        raise NimError("The AI response could not be parsed as JSON.") from e


async def _chat_completion(messages: list[dict], model: str) -> dict:
    if not settings.nvidia_configured:
        raise NimError("AI is not configured on the server yet.")

    url = f"{settings.NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.NVIDIA_NIM_API_KEY}",
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
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise NimError("The AI service timed out. Please try again.") from e
    except httpx.ConnectError as e:
        raise NimError("Could not reach the AI service. Please try again shortly.") from e
    except httpx.HTTPError as e:
        raise NimError("A network error occurred while contacting the AI service.") from e

    if resp.status_code >= 500:
        logger.error("NVIDIA NIM upstream 5xx: %s", resp.status_code)
        raise NimError("The AI service is temporarily unavailable. Please try again shortly.")
    if resp.status_code >= 400:
        logger.error("NVIDIA NIM upstream 4xx: %s %s", resp.status_code, resp.text[:500])
        raise NimError("The AI service rejected the request.")

    try:
        data = resp.json()
    except ValueError as e:
        raise NimError("The AI service returned an unreadable response.") from e

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise NimError("The AI service returned an empty response.") from e

    if not content or not content.strip():
        raise NimError("The AI service returned an empty response.")

    return _extract_json_object(content)


async def analyze_text(ocr_text: str) -> dict:
    text = ocr_text.strip()
    if not text:
        raise NimError("No OCR text was provided.")
    if len(text) > settings.MAX_OCR_CHARS:
        text = text[: settings.MAX_OCR_CHARS]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_text_user_prompt(text)},
    ]
    return await _chat_completion(messages, settings.NVIDIA_TEXT_MODEL)


async def analyze_image(image_bytes: bytes, content_type: str) -> dict:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{b64}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": build_vision_user_prompt()},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]
    return await _chat_completion(messages, settings.NVIDIA_VISION_MODEL)
