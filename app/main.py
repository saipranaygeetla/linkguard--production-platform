import os
import logging
import string
import random
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
import redis

# ---------------------------------------------------------------------------
# Structured logging to stdout — this is what `kubectl logs` will show later.
# We use a simple key=value format now; JSON is an easy upgrade path if a
# log aggregator (e.g. Cloud Logging) needs to parse it structurally.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="ts=%(asctime)s level=%(levelname)s msg=%(message)s",
)
log = logging.getLogger("linkguard")

# ---------------------------------------------------------------------------
# Configuration — read from environment only. This is deliberate: nothing
# here is hardcoded, because in M3 these same variable names get populated
# by a ConfigMap (non-sensitive) or a Secret (sensitive) instead of a .env
# file. The app code does not need to know or care which one supplies it.
# ---------------------------------------------------------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")  # sensitive -> Secret later
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))  # ConfigMap later
VALID_API_KEYS = set(
    k.strip() for k in os.getenv("API_KEYS", "dev-key-123").split(",") if k.strip()
)  # sensitive -> Secret later

BASE62 = string.ascii_letters + string.digits

# ---------------------------------------------------------------------------
# Redis client. decode_responses=True means we get Python strings back
# instead of bytes — simpler code, tiny performance cost we accept here.
# ---------------------------------------------------------------------------
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD or None,
    decode_responses=True,
    socket_connect_timeout=2,  # fail fast instead of hanging a request
)

app = FastAPI(title="LinkGuard", version="0.1.0")


class ShortenRequest(BaseModel):
    url: str


def generate_code(length: int = 7) -> str:
    return "".join(random.choices(BASE62, k=length))


def check_api_key(x_api_key: str | None) -> str:
    if not x_api_key or x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
    return x_api_key


def check_rate_limit(api_key: str) -> None:
    """
    Fixed-window rate limiting: one counter per API key per calendar minute.
    Simple and honest about its limitation (bursts at window boundaries) —
    that limitation is itself a good interview talking point re: sliding
    window vs. fixed window trade-offs.
    """
    window = int(time.time() // 60)
    key = f"ratelimit:{api_key}:{window}"
    current = r.incr(key)
    if current == 1:
        r.expire(key, 60)
    if current > RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="rate limit exceeded")


@app.get("/healthz")
def healthz():
    # Liveness: is the process itself alive and able to respond?
    # Deliberately does NOT check Redis — a Redis outage should not cause
    # Kubernetes to kill and restart otherwise-healthy app pods.
    return {"status": "alive"}


@app.get("/ready")
def ready():
    # Readiness: can this pod actually serve real traffic right now?
    # Checking Redis here means Kubernetes stops routing traffic to this
    # pod the moment Redis becomes unreachable — exactly the behavior
    # we want, without killing the pod.
    try:
        r.ping()
        return {"status": "ready"}
    except redis.exceptions.RedisError as e:
        log.warning(f"readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="redis unreachable")


@app.post("/shorten")
def shorten(body: ShortenRequest, x_api_key: str | None = Header(default=None)):
    api_key = check_api_key(x_api_key)
    check_rate_limit(api_key)

    code = generate_code()
    r.set(f"url:{code}", body.url)
    r.set(f"created:{code}", datetime.now(timezone.utc).isoformat())
    r.set(f"stats:{code}", 0)

    log.info(f"shortened url code={code} api_key={api_key}")
    return {"code": code, "short_url": f"/{code}"}


@app.get("/{code}")
def redirect(code: str):
    original = r.get(f"url:{code}")
    if not original:
        raise HTTPException(status_code=404, detail="short code not found")
    r.incr(f"stats:{code}")
    return RedirectResponse(url=original, status_code=302)


@app.get("/stats/{code}")
def stats(code: str, x_api_key: str | None = Header(default=None)):
    check_api_key(x_api_key)
    clicks = r.get(f"stats:{code}")
    created = r.get(f"created:{code}")
    if clicks is None:
        raise HTTPException(status_code=404, detail="short code not found")
    return {"code": code, "clicks": int(clicks), "created_at": created}