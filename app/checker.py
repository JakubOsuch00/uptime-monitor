import time
from datetime import UTC, datetime

import httpx

from app.db import Check, Target


def check_url(client: httpx.Client, target: Target) -> Check:
    start = time.perf_counter()
    try:
        resp = client.get(target.url)
        elapsed = (time.perf_counter() - start) * 1000
        return Check(
            target_id=target.id,
            checked_at=datetime.now(UTC),
            status_code=resp.status_code,
            response_ms=round(elapsed, 1),
            ok=resp.status_code < 400,
        )
    except httpx.HTTPError as exc:
        return Check(
            target_id=target.id,
            checked_at=datetime.now(UTC),
            ok=False,
            error=f"{type(exc).__name__}: {exc}"[:300],
        )
