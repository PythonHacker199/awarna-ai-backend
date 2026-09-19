import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes.analyze import router as analyze_router
from .schemas import HealthResponse


logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Awarna AI Backend",
    description=(
        "AI document understanding backend "
        "for Awarna."
    ),
    version="2.0.0",
)

# Browsers (the Awarna website) must pass a CORS preflight before they can
# POST JSON here. Native apps don't, which is why the phone app always worked.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
    allow_credentials=False,
    max_age=86400,
)

app.include_router(analyze_router)


@app.get(
    "/api/health",
    response_model=HealthResponse,
)
async def health():

    return HealthResponse(
        gemini_configured=settings.gemini_configured,
        nvidia_configured=settings.nvidia_configured,
        primary_provider=settings.PRIMARY_PROVIDER,
        gemini_model=settings.GEMINI_TEXT_MODEL,
        nvidia_model=settings.NVIDIA_TEXT_MODEL,
    )


@app.get("/")
async def root():

    return {
        "ok": True,
        "service": "Awarna AI Backend",
        "docs": "/docs",
    }