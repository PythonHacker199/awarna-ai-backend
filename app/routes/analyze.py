from fastapi import APIRouter, HTTPException

from ..config import settings
from ..schemas import AnalyzeResponse, AnalyzeTextRequest
from ..services.ai import AIError, analyze_text
from ..services.normalizer import normalize_extraction


router = APIRouter(
    prefix="/api/v1/analyze",
    tags=["analyze"],
)


@router.post(
    "/text",
    response_model=AnalyzeResponse,
)
async def analyze_text_route(
    body: AnalyzeTextRequest,
) -> AnalyzeResponse:

    try:

        (
            raw,
            provider,
            model,
            fallback_used,
        ) = await analyze_text(
            body.ocr_text
        )

    except AIError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    extraction = normalize_extraction(raw)

    return AnalyzeResponse(
        mode="text",
        provider=provider,
        model=model,
        fallback_used=fallback_used,
        extraction=extraction,
    )