from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Exact category list from the product spec — the AI must pick one of
# these, never invent a new one. "Other" is always the safe fallback.
ALLOWED_CATEGORIES = [
    "Receipt",
    "Bill",
    "Invoice",
    "Warranty",
    "Certificate",
    "Insurance",
    "Identity",
    "Banking",
    "Tax",
    "Medical",
    "Education",
    "Legal",
    "Property",
    "Vehicle",
    "Other",
]

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AnalyzeTextRequest(BaseModel):
    ocr_text: str = Field(..., min_length=1, description="Raw text extracted locally by ML Kit")
    source: str = Field(default="ml_kit")


class Extraction(BaseModel):
    title: Optional[str] = None
    category: str = "Other"
    vendor: Optional[str] = None
    document_number: Optional[str] = None
    document_date: Optional[str] = None
    due_date: Optional[str] = None
    expiry_date: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    summary: Optional[str] = None
    key_details: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v: str) -> str:
        if v not in ALLOWED_CATEGORIES:
            return "Other"
        return v

    @field_validator("document_date", "due_date", "expiry_date")
    @classmethod
    def date_must_be_iso_or_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not _DATE_RE.match(v):
            return None
        try:
            date.fromisoformat(v)
        except ValueError:
            return None
        return v

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, v))

    @field_validator("amount")
    @classmethod
    def amount_must_be_sane(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        try:
            v = float(v)
        except (TypeError, ValueError):
            return None
        # Reject absurd values that are almost certainly a misread field
        # (phone number, account number, etc. picked up as an "amount").
        if v < 0 or v > 100_000_000:
            return None
        return round(v, 2)


class AnalyzeResponse(BaseModel):
    ok: bool = True
    mode: str
    model: str
    extraction: Extraction


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "Awarna AI Backend"
    nvidia_configured: bool
    text_model: str
    vision_model: str


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
