import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routes.analyze import router as analyze_router
from .schemas import HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("awarna")

app = FastAPI(
    title="Awarna AI Backend",
    description="Structured document understanding via NVIDIA NIM, for the Awarna app.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces or internal details to the client.
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"ok": False, "error": "Something went wrong. Please try again."})


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        nvidia_configured=settings.nvidia_configured,
        text_model=settings.NVIDIA_TEXT_MODEL,
        vision_model=settings.NVIDIA_VISION_MODEL,
    )


@app.get("/")
async def root():
    return {"ok": True, "service": "Awarna AI Backend", "docs": "/docs"}
