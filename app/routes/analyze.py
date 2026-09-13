from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import settings
from ..schemas import AnalyzeResponse, AnalyzeTextRequest
from ..services.nim import NimError, analyze_image, analyze_text
from ..services.normalizer import normalize_extraction

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


@router.post("/text", response_model=AnalyzeResponse)
async def analyze_text_route(body: AnalyzeTextRequest) -> AnalyzeResponse:
    try:
        raw = await analyze_text(body.ocr_text)
    except NimError as e:
        raise HTTPException(status_code=502, detail=str(e))

    extraction = normalize_extraction(raw)
    return AnalyzeResponse(mode="text", model=settings.NVIDIA_TEXT_MODEL, extraction=extraction)


@router.post("/image", response_model=AnalyzeResponse)
async def analyze_image_route(file: UploadFile = File(...)) -> AnalyzeResponse:
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type. Please use JPG, PNG, or WEBP.",
        )

    image_bytes = await file.read()
    max_bytes = int(settings.MAX_IMAGE_MB * 1024 * 1024)
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="The uploaded image was empty.")
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image is too large. Maximum size is {settings.MAX_IMAGE_MB} MB.",
        )

    try:
        raw = await analyze_image(image_bytes, content_type)
    except NimError as e:
        raise HTTPException(status_code=502, detail=str(e))

    extraction = normalize_extraction(raw)
    return AnalyzeResponse(mode="image", model=settings.NVIDIA_VISION_MODEL, extraction=extraction)
