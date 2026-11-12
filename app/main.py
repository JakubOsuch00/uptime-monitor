import html
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, HttpUrl
from sqlalchemy import case, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.db import Check, SessionLocal, Target, init_db, seed_targets

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["path"])


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as session:
        seed_targets(session, config.DEFAULT_TARGETS)
    yield


app = FastAPI(title="uptime-monitor", lifespan=lifespan)


def get_db():
    with SessionLocal() as session:
        yield session


DB = Annotated[Session, Depends(get_db)]


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    # route template instead of real path, otherwise /api/targets/1, /2... each get own label
    route = request.scope.get("route")
    path = route.path if route else "unknown"
    REQUESTS.labels(request.method, path, response.status_code).inc()
    LATENCY.labels(path).observe(time.perf_counter() - start)
    return response


class TargetIn(BaseModel):
    name: str
    url: HttpUrl


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: DB):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database not available") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/targets")
def list_targets(db: DB):
    targets = db.scalars(select(Target).order_by(Target.name)).all()
    return [{"id": t.id, "name": t.name, "url": t.url} for t in targets]


@app.post("/api/targets", status_code=201)
def add_target(body: TargetIn, db: DB):
    target = Target(name=body.name, url=str(body.url))
    db.add(target)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="target with this name already exists") from exc
    return {"id": target.id, "name": target.name, "url": target.url}


@app.delete("/api/targets/{target_id}", status_code=204)
def delete_target(target_id: int, db: DB):
    target = db.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="not found")
    db.query(Check).filter(Check.target_id == target_id).delete()
    db.delete(target)
    db.commit()


@app.get("/api/status")
def status(db: DB):
    since = datetime.now(UTC) - timedelta(hours=24)
    result = []
    for t in db.scalars(select(Target).order_by(Target.name)).all():
        last = db.scalar(
            select(Check).where(Check.target_id == t.id).order_by(Check.checked_at.desc()).limit(1)
        )
        total, ok = db.execute(
            select(func.count(), func.sum(case((Check.ok, 1), else_=0))).where(
                Check.target_id == t.id, Check.checked_at >= since
            )
        ).one()
        result.append(
            {
                "name": t.name,
                "url": t.url,
                "up": last.ok if last else None,
                "status_code": last.status_code if last else None,
                "response_ms": last.response_ms if last else None,
                "last_check": last.checked_at.isoformat() if last else None,
                "uptime_24h": round(100 * (ok or 0) / total, 2) if total else None,
            }
        )
    return result


@app.get("/", response_class=HTMLResponse)
def index(db: DB):
    rows = []
    for s in status(db):
        state = {True: "UP", False: "DOWN", None: "?"}[s["up"]]
        color = {"UP": "#2e7d32", "DOWN": "#c62828", "?": "#777"}[state]
        uptime = f"{s['uptime_24h']}%" if s["uptime_24h"] is not None else "-"
        ms = f"{s['response_ms']} ms" if s["response_ms"] is not None else "-"
        rows.append(
            f"<tr><td>{html.escape(s['name'])}</td>"
            f'<td><a href="{html.escape(s["url"])}">{html.escape(s["url"])}</a></td>'
            f'<td style="color:{color};font-weight:bold">{state}</td>'
            f"<td>{ms}</td><td>{uptime}</td></tr>"
        )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>uptime-monitor</title>
<meta http-equiv="refresh" content="30">
<style>body{{font-family:sans-serif;margin:40px}}td,th{{padding:6px 14px;text-align:left}}</style>
</head><body><h1>Status</h1>
<table><tr><th>name</th><th>url</th><th>state</th><th>response</th><th>uptime 24h</th></tr>
{"".join(rows)}</table></body></html>"""
