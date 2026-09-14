from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
    ocr_text: str = Field(
        ...,
        min_length=1,
        description="Raw OCR text extracted by ML Kit",
    )

    source: str = "ml_kit"


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
    def valid_category(cls, value: str) -> str:
        if value not in ALLOWED_CATEGORIES:
            return "Other"
        return value

    @field_validator(
        "document_date",
        "due_date",
        "expiry_date",
    )
    @classmethod
    def valid_date(
        cls,
        value: Optional[str],
    ) -> Optional[str]:

        if value is None:
            return None

        value = value.strip()

        if not _DATE_RE.match(value):
            return None

        try:
            date.fromisoformat(value)
        except ValueError:
            return None

        return value

    @field_validator("confidence")
    @classmethod
    def valid_confidence(cls, value: float) -> float:

        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(0.0, min(1.0, value))

    @field_validator("amount")
    @classmethod
    def valid_amount(
        cls,
        value: Optional[float],
    ) -> Optional[float]:

        if value is None:
            return None

        try:
            value = float(value)
        except (TypeError, ValueError):
            return None

        if value < 0 or value > 100_000_000:
            return None

        return round(value, 2)


class AnalyzeResponse(BaseModel):
    ok: bool = True
    mode: str
    provider: str
    model: str
    fallback_used: bool = False
    extraction: Extraction


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "Awarna AI Backend"

    gemini_configured: bool
    nvidia_configured: bool

    primary_provider: str

    gemini_model: str
    nvidia_model: str