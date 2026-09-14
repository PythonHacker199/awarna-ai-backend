import os


class Settings:
    # =========================
    # Gemini
    # =========================

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    GEMINI_TEXT_MODEL: str = os.getenv(
        "GEMINI_TEXT_MODEL",
        "gemini-3.8-flash",
    )

    GEMINI_VISION_MODEL: str = os.getenv(
        "GEMINI_VISION_MODEL",
        "gemini-3.8-flash",
    )

    # =========================
    # NVIDIA / DeepSeek
    # =========================

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
        "deepseek-ai/deepseek-v4-pro-0813",
    )

    NVIDIA_VISION_MODEL: str = os.getenv(
        "NVIDIA_VISION_MODEL",
        "meta/muse-glimmer-30b",
    )

    # =========================
    # AI routing
    # =========================

    PRIMARY_PROVIDER: str = os.getenv(
        "PRIMARY_PROVIDER",
        "gemini",
    ).lower()

    ENABLE_FALLBACK: bool = os.getenv(
        "ENABLE_FALLBACK",
        "true",
    ).lower() in ("1", "true", "yes", "on")

    # =========================
    # Limits
    # =========================

    REQUEST_TIMEOUT_SECONDS: float = float(
        os.getenv("REQUEST_TIMEOUT_SECONDS", "90")
    )

    MAX_IMAGE_MB: float = float(
        os.getenv("MAX_IMAGE_MB", "10")
    )

    MAX_OCR_CHARS: int = int(
        os.getenv("MAX_OCR_CHARS", "50000")
    )

    # =========================
    # CORS
    # =========================

    CORS_ALLOW_ORIGINS: list[str] = [
        x.strip()
        for x in os.getenv(
            "CORS_ALLOW_ORIGINS",
            "*",
        ).split(",")
        if x.strip()
    ]

    @property
    def gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.NVIDIA_NIM_API_KEY)


settings = Settings()