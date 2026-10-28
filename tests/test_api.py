from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "Awarna AI Backend"
    assert "nvidia_configured" in body
    assert "text_model" in body


def test_analyze_text_requires_ocr_text():
    r = client.post("/api/v1/analyze/text", json={})
    assert r.status_code == 422  # Pydantic validation error, not a crash


def test_analyze_text_empty_string_rejected():
    r = client.post("/api/v1/analyze/text", json={"ocr_text": ""})
    assert r.status_code == 422


def test_analyze_image_rejects_bad_content_type():
    r = client.post(
        "/api/v1/analyze/image",
        files={"file": ("doc.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 415


def test_normalizer_never_crashes_on_garbage():
    from app.services.normalizer import normalize_extraction

    result = normalize_extraction({"amount": "not a number", "category": "MadeUpCategory", "confidence": "high"})
    assert result.category == "Other"
    assert result.amount is None
    assert 0.0 <= result.confidence <= 1.0


def test_normalizer_rejects_absurd_amount():
    from app.services.normalizer import normalize_extraction

    result = normalize_extraction({"amount": 999999999})
    assert result.amount is None


def test_stalled_ai_returns_504_quickly(monkeypatch):
    """A hung Gemini call must not hang the request (was 90s+ in production)."""
    import asyncio
    import time

    from app.config import settings
    from app.services import gemini

    async def stalled(_text):
        await asyncio.sleep(10)

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "ANALYZE_BUDGET_SECONDS", 0.3)
    monkeypatch.setattr(gemini, "analyze_text", stalled)

    start = time.monotonic()
    r = client.post("/api/v1/analyze/text", json={"ocr_text": "Electricity bill due 15/11/2026"})
    assert r.status_code == 504
    assert time.monotonic() - start < 3
