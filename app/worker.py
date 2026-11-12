# Checks all targets every CHECK_INTERVAL seconds and exposes prometheus metrics.
# python -m app.worker

import logging
import signal
import time

import httpx
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from sqlalchemy import select

from app import config
from app.checker import check_url
from app.db import SessionLocal, Target, init_db, seed_targets

log = logging.getLogger("worker")

TARGET_UP = Gauge("uptime_target_up", "1 if the last check was ok", ["target"])
RESPONSE_TIME = Histogram(
    "uptime_response_seconds",
    "Response time of checked targets",
    ["target"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)
CHECKS = Counter("uptime_checks_total", "Number of checks", ["target", "result"])

running = True


def stop(*_):
    global running
    running = False


def run_once(client: httpx.Client) -> int:
    with SessionLocal() as session:
        targets = session.scalars(select(Target)).all()
        for target in targets:
            result = check_url(client, target)
            session.add(result)
            TARGET_UP.labels(target.name).set(1 if result.ok else 0)
            CHECKS.labels(target.name, "ok" if result.ok else "fail").inc()
            if result.response_ms is not None:
                RESPONSE_TIME.labels(target.name).observe(result.response_ms / 1000)
            log.info(
                "%s %s ok=%s %sms", target.name, result.status_code, result.ok, result.response_ms
            )
        session.commit()
    return len(targets)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    init_db()
    with SessionLocal() as session:
        seed_targets(session, config.DEFAULT_TARGETS)
    start_http_server(config.WORKER_METRICS_PORT)
    log.info("worker started, interval %ss", config.CHECK_INTERVAL)

    headers = {"User-Agent": config.USER_AGENT}  # some sites (wikipedia) block requests without it
    with httpx.Client(
        timeout=config.CHECK_TIMEOUT, follow_redirects=True, headers=headers
    ) as client:
        while running:
            try:
                run_once(client)
            except Exception:
                # db can be unavailable for a moment (e.g. on startup), try again next round
                log.exception("check round failed")
            for _ in range(config.CHECK_INTERVAL):
                if not running:
                    break
                time.sleep(1)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
