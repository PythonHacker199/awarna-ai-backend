"""Vercel entrypoint: serves the same FastAPI app that runs on Render.

vercel.json rewrites every path here, and FastAPI still sees the original
path (/api/health, /api/v1/analyze/text, ...), so URLs stay identical.
"""

from app.main import app  # noqa: F401  (Vercel looks for `app`)
