"""Daily push reminders for the Awarna website.

Vercel Cron calls this once a day (about 9 am India time). Browsers that turned
reminders on have saved rows of (date, how many papers, how many days before)
in Supabase; no document names ever reach this server. We send each browser
one short push for today's rows, drop browsers that have unsubscribed, and
delete what has been handled.
"""

import asyncio
import datetime as dt
import json
import logging
from collections import defaultdict

import httpx
from fastapi import APIRouter, Header, HTTPException
from pywebpush import WebPushException, webpush

from ..config import settings


logger = logging.getLogger("awarna.reminders")

router = APIRouter(prefix="/api/cron", tags=["cron"])

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _rest(table: str) -> str:
    return f"{settings.SUPABASE_URL}/rest/v1/{table}"


def _service_headers() -> dict[str, str]:
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def build_message(rows: list[dict]) -> dict:
    """One notification for all of a browser's reminders today, without names."""

    total = sum(int(r["papers"]) for r in rows)
    parts = []
    for r in sorted(rows, key=lambda r: int(r["lead_days"])):
        n, lead = int(r["papers"]), int(r["lead_days"])
        when = "today" if lead == 0 else "tomorrow" if lead == 1 else f"in {lead} days"
        parts.append(f"{n} {'is' if n == 1 else 'are'} due {when}")

    title = "1 paper needs attention" if total == 1 else f"{total} papers need attention"
    body = ", ".join(parts) + ". Open Awarna to see them."
    return {"title": title, "body": body[0].upper() + body[1:], "url": "/app/expiries"}


def _send(subscription: dict, message: dict) -> None:
    webpush(
        subscription_info=subscription,
        data=json.dumps(message),
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": settings.VAPID_SUBJECT},
        ttl=12 * 3600,
    )


@router.get("/reminders")
async def send_reminders(authorization: str | None = Header(default=None)):
    # Vercel Cron sends "Authorization: Bearer <CRON_SECRET>".
    if not settings.CRON_SECRET or authorization != f"Bearer {settings.CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Not allowed.")
    if not (settings.SUPABASE_SERVICE_ROLE_KEY and settings.VAPID_PRIVATE_KEY):
        raise HTTPException(status_code=503, detail="Push reminders are not configured.")

    today = dt.datetime.now(IST).date().isoformat()
    sent = expired = failed = 0

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            _rest("push_reminders"),
            params={"remind_on": f"eq.{today}", "select": "endpoint,subscription,papers,lead_days"},
            headers=_service_headers(),
        )
        response.raise_for_status()

        by_browser: dict[str, list[dict]] = defaultdict(list)
        for row in response.json():
            by_browser[row["endpoint"]].append(row)

        for endpoint, rows in by_browser.items():
            try:
                await asyncio.to_thread(_send, rows[0]["subscription"], build_message(rows))
                sent += 1
            except WebPushException as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in (404, 410):
                    # The browser unsubscribed or the subscription expired.
                    await client.delete(
                        _rest("push_reminders"),
                        params={"endpoint": f"eq.{endpoint}"},
                        headers=_service_headers(),
                    )
                    expired += 1
                else:
                    failed += 1
                    logger.warning("Push failed (status %s) for one browser", status)

        # Everything dated today or earlier has now been handled.
        await client.delete(
            _rest("push_reminders"),
            params={"remind_on": f"lte.{today}"},
            headers=_service_headers(),
        )

    logger.info("Reminders %s: sent=%s expired=%s failed=%s", today, sent, expired, failed)
    return {"date": today, "sent": sent, "expired": expired, "failed": failed}
