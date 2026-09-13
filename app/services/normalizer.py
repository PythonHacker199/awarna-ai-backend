from __future__ import annotations

from pydantic import ValidationError

from ..schemas import Extraction


def _clean_str(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s and s.lower() not in ("null", "none", "n/a", "unknown") else None


def normalize_extraction(raw: dict) -> Extraction:
    """Takes whatever dict the model produced and coerces it into a valid
    Extraction, never trusting field types or presence blindly."""
    if not isinstance(raw, dict):
        raw = {}

    cleaned = {
        "title": _clean_str(raw.get("title")),
        "category": _clean_str(raw.get("category")) or "Other",
        "vendor": _clean_str(raw.get("vendor")),
        "document_number": _clean_str(raw.get("document_number")),
        "document_date": _clean_str(raw.get("document_date")),
        "due_date": _clean_str(raw.get("due_date")),
        "expiry_date": _clean_str(raw.get("expiry_date")),
        "amount": raw.get("amount"),
        "currency": _clean_str(raw.get("currency")),
        "summary": _clean_str(raw.get("summary")),
        "key_details": raw.get("key_details") if isinstance(raw.get("key_details"), list) else [],
        "confidence": raw.get("confidence", 0.0),
        "warnings": raw.get("warnings") if isinstance(raw.get("warnings"), list) else [],
    }
    # Drop any non-string junk that might have ended up in list fields.
    cleaned["key_details"] = [str(x) for x in cleaned["key_details"] if str(x).strip()][:6]
    cleaned["warnings"] = [str(x) for x in cleaned["warnings"] if str(x).strip()]

    try:
        return Extraction(**cleaned)
    except ValidationError:
        # Last-resort safe fallback — never let a malformed AI response
        # turn into a 500 error for the user.
        return Extraction(
            title=cleaned.get("title"),
            category="Other",
            confidence=0.0,
            warnings=["AI response could not be fully validated; some fields may be missing."],
        )
