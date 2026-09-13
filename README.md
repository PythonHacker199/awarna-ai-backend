# Awarna AI Backend

FastAPI service that sits between the Awarna Flutter app and NVIDIA NIM.
The NVIDIA API key lives only here — it is never sent to or stored in the
mobile app.

## Pipeline

```
Flutter (ML Kit OCR text)
    → POST /api/v1/analyze/text
        → NVIDIA NIM (deepseek-ai/deepseek-v4-pro-0813)
            → structured JSON (validated with Pydantic)
    → back to Flutter → Supabase
```

An image-based path also exists for when you want the AI to read the
document directly instead of (or in addition to) ML Kit's OCR text:

```
Flutter (image)
    → POST /api/v1/analyze/image
        → NVIDIA NIM vision model (NVIDIA_VISION_MODEL)
            → same structured JSON shape
```

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your real NVIDIA_NIM_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check it's alive:

```bash
curl http://localhost:8000/api/health
```

Interactive docs: http://localhost:8000/docs

## Run tests

```bash
python -m pytest
```

The tests don't call the real NVIDIA API (no key needed to run them) —
they check request validation, error handling, and the normalizer's
safety rails (rejecting invented categories, absurd amounts, etc.).

## Deploy to Render

1. Push this `backend/` folder to a git repo (or the repo root — Render
   just needs `dockerfilePath` to point at it).
2. In Render: **New → Blueprint**, point it at the repo. `render.yaml`
   defines the service already.
3. Render will prompt you for `NVIDIA_NIM_API_KEY` (marked `sync: false`
   in `render.yaml` so it's never stored in the blueprint file itself) —
   paste your real key there, in Render's dashboard only.
4. Once deployed, your backend URL will be something like
   `https://awarna-ai-backend.onrender.com`. Use that as the Flutter
   app's `AWARNA_BACKEND_URL`.

## Environment variables

See `.env.example` for the full list. Nothing here needs to change
unless you want a different NVIDIA model or looser/stricter limits.

## Notes on the vision model

`NVIDIA_VISION_MODEL` defaults to a placeholder-style env var
(`meta/muse-glimmer-30b`) as specified — swap it for whatever
vision-capable model your NVIDIA NIM account actually has access to.
`deepseek-ai/deepseek-v4-pro-0813` is treated as text-only; the code
never assumes it can read images.
