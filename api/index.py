"""Vercel entrypoint: serves the same FastAPI app that runs on Render.

Vercel's FastAPI support routes every path to this app, so the URLs are
identical to Render's (/api/health, /api/v1/analyze/text, ...).
"""

from app.main import app  # noqa: F401  (Vercel looks for `app`)
