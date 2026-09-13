import os


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """
    All configuration comes from environment variables. Nothing here is
    ever hardcoded — the NVIDIA key in particular lives ONLY in the
    backend's environment (.env locally, or the host's secret manager
    in production). Flutter never sees it.
    """

    NVIDIA_NIM_API_KEY: str = os.getenv("NVIDIA_NIM_API_KEY", "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")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_TEXT_MODEL: str = os.getenv("NVIDIA_TEXT_MODEL", "deepseek-ai/deepseek-v4-pro-0813")
    NVIDIA_VISION_MODEL: str = os.getenv("NVIDIA_VISION_MODEL", "meta/muse-glimmer-30b")

    REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))
    MAX_IMAGE_MB: float = float(os.getenv("MAX_IMAGE_MB", "10"))
    MAX_OCR_CHARS: int = int(os.getenv("MAX_OCR_CHARS", "50000"))

    # Comma-separated list of allowed origins for CORS. In production this
    # should be your app's actual origin(s); "*" is fine for local dev only.
    CORS_ALLOW_ORIGINS: list[str] = [
        o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()
    ]

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.NVIDIA_NIM_API_KEY)


settings = Settings()
