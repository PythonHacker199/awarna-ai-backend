import os


class Settings:
    # ---------------------------------------------------------
    # GEMINI
    # ---------------------------------------------------------

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Primary model
    GEMINI_TEXT_MODEL: str = os.getenv(
        "GEMINI_TEXT_MODEL",
        "gemini-3.6-flash",
    )

    # Fallback models. 3.8-flash goes last: in production it often stalled
    # until Google's own 504 DEADLINE_EXCEEDED, adding ~20s before a fallback.
    GEMINI_FALLBACK_MODELS: list[str] = [
        os.getenv("GEMINI_FALLBACK_MODEL_1", "gemini-3.5-flash-lite"),
        os.getenv("GEMINI_FALLBACK_MODEL_2", "gemini-3.8-flash"),
    ]

    # ---------------------------------------------------------
    # NVIDIA
    # ---------------------------------------------------------

    # Kept only so old configuration does not break.
    # NVIDIA is NOT used by the new text failover system.
    NVIDIA_NIM_API_KEY: str = os.getenv(
        "NVIDIA_NIM_API_KEY",
        "",
    )

    NVIDIA_BASE_URL: str = os.getenv(
        "NVIDIA_BASE_URL",
        "https://integrate.api.nvidia.com/v1",
    )

    NVIDIA_TEXT_MODEL: str = os.getenv(
        "NVIDIA_TEXT_MODEL",
        "",
    )

    NVIDIA_VISION_MODEL: str = os.getenv(
        "NVIDIA_VISION_MODEL",
        "",
    )

    # ---------------------------------------------------------
    # AI BEHAVIOUR
    # ---------------------------------------------------------

    PRIMARY_PROVIDER: str = os.getenv(
        "PRIMARY_PROVIDER",
        "gemini",
    ).lower()

    ENABLE_FALLBACK: bool = os.getenv(
        "ENABLE_FALLBACK",
        "true",
    ).lower() in (
                                "1",
                                "true",
                                "yes",
                                "on",
                            )

    # Number of retries for temporary provider errors
    GEMINI_RETRIES: int = int(
        os.getenv("GEMINI_RETRIES", "2")
    )

    # Delay between retries
    GEMINI_RETRY_DELAY_SECONDS: float = float(
        os.getenv("GEMINI_RETRY_DELAY_SECONDS", "2")
    )

    # ---------------------------------------------------------
    # REQUEST LIMITS
    # ---------------------------------------------------------

    REQUEST_TIMEOUT_SECONDS: float = float(
        os.getenv(
            "REQUEST_TIMEOUT_SECONDS",
            "90",
        )
    )

    # Hard limit for ONE Gemini call. Without it a stalled call hangs the
    # request forever (seen as 90s+ timeouts in the apps).
    GEMINI_CALL_TIMEOUT_SECONDS: float = float(
        os.getenv("GEMINI_CALL_TIMEOUT_SECONDS", "20")
    )

    # Total time for a whole analysis, across retries and fallback models.
    # Kept under serverless limits; the apps fall back to manual entry.
    ANALYZE_BUDGET_SECONDS: float = float(
        os.getenv("ANALYZE_BUDGET_SECONDS", "45")
    )

    MAX_IMAGE_MB: float = float(
        os.getenv(
            "MAX_IMAGE_MB",
            "10",
        )
    )

    MAX_OCR_CHARS: int = int(
        os.getenv(
            "MAX_OCR_CHARS",
            "50000",
        )
    )

    # ---------------------------------------------------------
    # CORS
    # ---------------------------------------------------------

    # Comma-separated list, e.g. "https://awarna.app,https://www.awarna.app".
    # Defaults to "*" (any origin) — safe here because no cookies or
    # credentials are accepted; tighten it once the website has a domain.
    CORS_ALLOW_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
        if origin.strip()
    ] or ["*"]

    # ---------------------------------------------------------
    # STATUS
    # ---------------------------------------------------------

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.NVIDIA_NIM_API_KEY)


settings = Settings()