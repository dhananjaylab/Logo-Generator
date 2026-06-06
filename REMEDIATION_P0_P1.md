# Remediation Guide — P0 and P1 Fixes

**Applies to:** LogoForge AI v2.1.0  
**Issues addressed:** 2 P0 critical + 4 P1 high from the architecture review  
**Format:** Each fix shows the exact file, the change, and a verification step

---

## Fix 1 (P0) — WebSocket: replace server-side polling with Redis Pub/Sub

**Files:** `backend/dalle_worker.py`, `backend/gemini_worker.py`, `backend/routers.py`  
**Problem:** The WebSocket handler polls Redis up to 3 times per 0.5–4 s per open connection. At 500 concurrent connections this creates ~1,500 Redis operations per second minimum, growing O(n) with users.  
**Solution:** Workers publish a completion event to a per-job Redis channel. The WebSocket handler subscribes and receives a single push when the job finishes.

---

### Step 1a — Add a helper to both workers

Add `import json` at the top of `dalle_worker.py` and `gemini_worker.py`, then change the task function body:

**`backend/dalle_worker.py`** — `generate_dalle_task`:

```python
# Before
async def generate_dalle_task(ctx, user_ip: str, user_id: str, **kwargs):
    llm = ctx.get("llm_dalle") if hasattr(ctx, "get") else None
    if not llm:
        openai_client = Clients.get_openai_client()
        llm = LLMService(None, openai_client)
    print(f"[DALL-E Worker] Starting generation for {kwargs.get('text')}")
    try:
        path, prompt = await llm.generate_logo_with_dalle(user_ip=user_ip, user_id=user_id, **kwargs)
        return {"result": [path], "generator": "dall-e-3", "prompt": prompt, "status": "completed"}
    except Exception as exc:
        logger.error(f"[DALL-E Worker] Generation failed: {exc}")
        return {"status": "failed", "error": str(exc)}
```

```python
# After
import json

async def generate_dalle_task(ctx, user_ip: str, user_id: str, **kwargs):
    llm = ctx.get("llm_dalle") if hasattr(ctx, "get") else None
    if not llm:
        openai_client = Clients.get_openai_client()
        llm = LLMService(None, openai_client)

    job_id = ctx.get("job_id")
    redis = ctx.get("redis")

    logger.info(f"[DALL-E Worker] Starting generation for '{kwargs.get('text')}' (job={job_id})")
    try:
        path, prompt = await llm.generate_logo_with_dalle(user_ip=user_ip, user_id=user_id, **kwargs)
        result = {"result": [path], "generator": "dall-e-3", "prompt": prompt, "status": "completed"}

        # Notify WebSocket subscribers — replaces server-side polling
        if job_id and redis:
            event = json.dumps({
                "status": "completed",
                "user_id": user_id,  # for ownership validation in WS handler
                "result": {
                    "result": result["result"],
                    "generator": result["generator"],
                    "prompt": result["prompt"],
                    "brand": kwargs.get("text", ""),
                    "style": kwargs.get("style", ""),
                    "palette": kwargs.get("palette", ""),
                }
            })
            await redis.publish(f"job:complete:{job_id}", event)

        return result

    except Exception as exc:
        logger.error(f"[DALL-E Worker] Generation failed: {exc}")
        error_event = json.dumps({"status": "failed", "error": str(exc), "user_id": user_id})
        if job_id and redis:
            await redis.publish(f"job:complete:{job_id}", error_event)
        return {"status": "failed", "error": str(exc)}
```

Apply the identical change to `gemini_worker.py` (`generate_gemini_task`), adjusting the `"generator"` value to `"gemini"`.

---

### Step 1b — Rewrite the WebSocket handler in `routers.py`

Replace the entire `ws_progress` function. The new version subscribes first, then checks for an already-completed job (avoiding the race condition), then awaits a single push.

```python
# Add to top of routers.py
import json

# Replace the ws_progress function entirely:
@router.websocket("/ws/progress/{job_id}")
async def ws_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint. Uses Redis Pub/Sub push instead of polling.
    Scales to thousands of concurrent connections.
    Token passed as query param: ?token=<value>
    """
    from arq.jobs import Job
    from urllib.parse import unquote

    # ── Auth ───────────────────────────────────────────────────────────────
    raw_token = websocket.query_params.get("token")
    if raw_token:
        raw_token = unquote(raw_token)
    try:
        user = await validate_token_string(raw_token)
        user_id = user.get("sub", "anonymous")
    except HTTPException as exc:
        await websocket.close(code=1008, reason=exc.detail)
        return

    await websocket.accept()
    redis = websocket.app.state.redis
    channel = f"job:complete:{job_id}"
    pubsub = None

    try:
        # Subscribe FIRST — before checking job status — to eliminate the
        # race condition where the job completes between our check and subscribe.
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)

        # Check if job already completed while we were subscribing.
        queues = ["dalle_queue", "gemini_queue", "arq:queue"]
        for q in queues:
            job_obj = Job(job_id, redis, _queue_name=q)
            status = await job_obj.status()
            status_str = status.value if hasattr(status, "value") else str(status)
            if status_str == "complete":
                info = await job_obj.result_info()
                job_owner = info.kwargs.get("user_id") if info else None
                if job_owner and job_owner != user_id and user_id != "developer":
                    await websocket.send_json({"status": "failed", "error": "Unauthorized"})
                    return
                if info and info.result:
                    res = info.result
                    if res.get("status") == "failed":
                        await websocket.send_json({"status": "failed", "error": res.get("error")})
                    else:
                        await websocket.send_json({
                            "status": "completed",
                            "result": {
                                "result": res.get("result"),
                                "generator": res.get("generator"),
                                "prompt": res.get("prompt"),
                                "brand": info.kwargs.get("text"),
                                "style": info.kwargs.get("style"),
                                "palette": info.kwargs.get("palette"),
                            }
                        })
                return  # done — already had the result

        # Job is still pending — tell the client and wait for the pub/sub push.
        await websocket.send_json({"status": "queued"})

        try:
            async with asyncio.timeout(300):  # 5-minute hard ceiling
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    data = json.loads(message["data"])

                    # Ownership check on streamed result
                    published_owner = data.pop("user_id", None)
                    if published_owner and published_owner != user_id and user_id != "developer":
                        await websocket.send_json({"status": "failed", "error": "Unauthorized"})
                        break

                    await websocket.send_json(data)
                    break  # single-shot — one event per job

        except asyncio.TimeoutError:
            await websocket.send_json({"status": "failed", "error": "Job timed out waiting for result"})

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"[WS] Unexpected error for job {job_id}: {e}")
        try:
            await websocket.send_json({"status": "error", "error": str(e)})
        except Exception:
            pass
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass
```

**Verification:**
```bash
# Start backend, enqueue a job, open two simultaneous WebSocket connections
# to the same job_id. Both should receive exactly one message on completion
# with zero additional Redis traffic between "queued" and "completed".
redis-cli monitor | grep "PUBLISH\|SUBSCRIBE"
# Should see: SUBSCRIBE job:complete:<id>  then  PUBLISH job:complete:<id> <payload>
# NOT: repeated STATUS calls every 0.5–4 seconds
```

---

## Fix 2 (P0) — R2 upload: raise on failure instead of returning sentinel strings

**File:** `backend/services.py`  
**Problem:** `upload_to_r2` returns `"LOCAL_FALLBACK/..."` or `"UPLOAD_FAILED/..."` on failure. These strings are stored as `image_url` values in the database, producing permanent broken-image records with no error surface to the user.

```python
# Before (services.py)
def upload_to_r2(data: bytes, filename: str, content_type: str = "image/png") -> str:
    client = get_r2_client()
    if not client or not R2_BUCKET_NAME:
        print("[R2] ⚠ R2 client or bucket not configured; falling back to local simulation")
        return f"LOCAL_FALLBACK/{filename}"           # ← silently stored as a URL
    try:
        client.put_object(...)
        ...
    except Exception as exc:
        print(f"[R2] ⚠ Upload failed: {exc}")
        return f"UPLOAD_FAILED/{filename}"             # ← silently stored as a URL
```

```python
# After (services.py)
def upload_to_r2(data: bytes, filename: str, content_type: str = "image/png") -> str:
    """
    Upload bytes to R2. Raises RuntimeError on any failure so the caller
    (worker task) can mark the job as failed and surface a real error.
    """
    client = get_r2_client()
    if not client or not R2_BUCKET_NAME:
        raise RuntimeError(
            "R2 upload failed: storage client not configured. "
            "Set R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME."
        )
    try:
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=filename,
            Body=data,
            ContentType=content_type,
        )
        if R2_PUBLIC_DOMAIN:
            return f"{R2_PUBLIC_DOMAIN}/{filename}"
        return f"{R2_ENDPOINT_URL}/{R2_BUCKET_NAME}/{filename}"
    except Exception as exc:
        raise RuntimeError(f"R2 upload failed for '{filename}': {exc}") from exc
```

The worker's existing `except Exception` block already returns `{"status": "failed", "error": str(exc)}`, so no worker changes are needed — the raised `RuntimeError` propagates cleanly.

**Verification:**
```bash
# Temporarily unset R2 credentials and trigger a generation.
# Expect: job.status == "failed" with a clear error message
# NOT: job "completed" with a broken image URL stored in the DB
unset R2_ACCESS_KEY_ID && curl -X POST .../api/generate ...
```

---

## Fix 3 (P1) — JWT validation: extract shared function (DRY)

**File:** `backend/dependencies.py`, `backend/routers.py`  
**Problem:** The 40-line JWT validation block is duplicated in the WebSocket handler, meaning two independent code paths to maintain for any JWT policy change.

### Step 3a — Add `validate_token_string` to `dependencies.py`

```python
# Add after the existing validate_clerk_token function in dependencies.py

async def validate_token_string(token: str | None) -> dict:
    """
    Validate a raw token string (for use by endpoints that receive tokens
    outside the standard Authorization header — e.g. WebSocket query params).
    Raises HTTPException on failure, returns the JWT payload dict on success.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_production = os.getenv("ENV") == "production"
    dev_token = os.getenv("DEV_TOKEN")

    # Dev token bypass (non-production only)
    if dev_token and token == dev_token:
        if is_production:
            logger.error("[AUTH] ❌ DEV_TOKEN used in production — rejecting")
            raise HTTPException(status_code=403, detail="Dev tokens not allowed in production")
        logger.info("[AUTH] ✅ Authorized via DEV_TOKEN (dev mode)")
        return {"sub": "developer", "status": "verified_via_dev_token"}

    # Clerk JWT validation
    jwks = await ClerkAuthProvider.get_jwks()
    if not jwks:
        if is_production:
            raise HTTPException(status_code=500, detail="Authentication service unavailable")
        logger.warning("[AUTH] ⚠ Skipping validation — JWKS not configured (dev mode)")
        return {"sub": "anonymous", "status": "unverified"}

    try:
        audience = os.getenv("CLERK_AUDIENCE", "http://localhost:3000")
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=audience if is_production else None,
            options={"verify_aud": is_production},
        )
        logger.info(f"[AUTH] ✅ JWT validated for user: {payload.get('sub')}")
        return payload
    except Exception as e:
        logger.warning(f"[AUTH] ❌ Token validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### Step 3b — Simplify `validate_clerk_token` to delegate

```python
# Before
async def validate_clerk_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    is_production = os.getenv("ENV") == "production"
    dev_token = os.getenv("DEV_TOKEN")
    # ... 30 more lines ...

# After
async def validate_clerk_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency. Validates the Authorization: Bearer <token> header."""
    return await validate_token_string(credentials.credentials)
```

### Step 3c — Simplify the WebSocket auth block in `routers.py`

Replace the ~40-line auth section in `ws_progress` (already shown in Fix 1) with:

```python
from dependencies import validate_token_string  # import at top of file

# Inside ws_progress, replace the entire auth section with:
raw_token = websocket.query_params.get("token")
if raw_token:
    raw_token = unquote(raw_token)
try:
    user = await validate_token_string(raw_token)
    user_id = user.get("sub", "anonymous")
except HTTPException as exc:
    await websocket.close(code=1008, reason=exc.detail)
    return
```

**Verification:**
```bash
# Both paths should behave identically:
# HTTP endpoint with invalid token → 401
curl -H "Authorization: Bearer invalid" http://localhost:8000/api/history
# WebSocket with invalid token → close code 1008
wscat -c "ws://localhost:8000/api/ws/progress/test-job?token=invalid"
# HTTP endpoint with valid dev token → 200
curl -H "Authorization: Bearer logo-forge-dev-2026" http://localhost:8000/api/history
# WebSocket with valid dev token → accepts connection
wscat -c "ws://localhost:8000/api/ws/progress/test-job?token=logo-forge-dev-2026"
```

---

## Fix 4 (P1) — Database engine: disable echo in production

**File:** `backend/database.py`  
**Problem:** `create_async_engine(DATABASE_URL, echo=True)` emits every SQL statement to stdout in production, flooding structured logs and adding I/O overhead. No pool sizing is configured.

```python
# Before (database.py)
if engine := create_async_engine(DATABASE_URL, echo=True) if DATABASE_URL else None:
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

```python
# After (database.py)
import os

_echo_sql = os.getenv("ENV", "development") != "production"

if engine := create_async_engine(
    DATABASE_URL,
    echo=_echo_sql,
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_pre_ping=True,   # detect stale connections without a query failure
) if DATABASE_URL else None:
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

Also update `init_db` to guard `create_all` to development only:

```python
# Before
async def init_db():
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

# After
async def init_db():
    if not engine:
        return
    env = os.getenv("ENV", "development")
    if env == "production":
        # Production schema is managed by Alembic migrations.
        # Run `alembic upgrade head` before starting the server.
        logger.info("[DB] Production mode — schema managed by Alembic. Skipping create_all.")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[DB] ✓ Tables created/verified (development mode)")
```

**Verification:**
```bash
# In production (ENV=production), start the server and confirm no SQL in logs:
grep "SELECT\|INSERT\|CREATE" /var/log/logo-generator/backend.log
# Should be empty (or contain only deliberate app-level log lines, not SQL echo)
```

---

## Fix 5 (P1) — Logging: propagate request ID to log records via contextvars

**Files:** `backend/observability.py`, `backend/logging_config.py`  
**Problem:** `RequestIDFilter` reads `getattr(record, "request_id", "N/A")` but nothing ever sets this on the log record. The request ID is stored on `request.state` but never injected into the logging context. Every log line shows `request_id = "N/A"`, making per-request log tracing non-functional.

### Step 5a — Add a `ContextVar` to `observability.py`

```python
# Add near the top of observability.py, after imports:
from contextvars import ContextVar

# Stores the current request ID for the duration of each async request.
# Set by metrics_middleware; read by RequestIDFilter in logging_config.py.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="N/A")
```

### Step 5b — Set the `ContextVar` in `metrics_middleware`

```python
# Before (observability.py — metrics_middleware)
async def metrics_middleware(request, call_next):
    start_time = time.time()
    request_id = request.headers.get("x-request-id", f"req_{id(request)}")
    request.state.request_id = request_id
    # ... rest of function

# After
async def metrics_middleware(request, call_next):
    start_time = time.time()
    request_id = request.headers.get("x-request-id", f"req_{id(request)}")
    request.state.request_id = request_id
    request_id_ctx.set(request_id)   # ← inject into logging context
    # ... rest of function unchanged
```

### Step 5c — Read the `ContextVar` in `RequestIDFilter`

```python
# Before (logging_config.py)
class RequestIDFilter(logging.Filter):
    def __init__(self, request_id_var: str = "request_id"):
        self.request_id_var = request_id_var

    def filter(self, record):
        record.request_id = getattr(record, "request_id", "N/A")   # ← always "N/A"
        return True

# After
from observability import request_id_ctx   # add this import

class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get()   # ← reads the async context
        return True
```

**Verification:**
```bash
# Make two simultaneous requests and check that each log line carries a
# distinct request_id matching the x-request-id header sent:
curl -H "x-request-id: req-aaa" http://localhost:8000/api/health &
curl -H "x-request-id: req-bbb" http://localhost:8000/api/health
# In development logs, look for:
# [2026-06-05 10:00:00] INFO  [routers.py:40] ... request_id=req-aaa
# [2026-06-05 10:00:00] INFO  [routers.py:40] ... request_id=req-bbb
```

---

## Fix 6 (P1) — Add Alembic for production database migrations

**Files:** `backend/requirements.txt`, new `backend/alembic.ini`, new `backend/alembic/env.py`  
**Problem:** `create_all` cannot handle schema changes in production. `alembic` is referenced in deployment docs but absent from `requirements.txt` and no migration files exist.

### Step 6a — Add Alembic to `requirements.txt`

```
# Add this line to backend/requirements.txt:
alembic==1.13.1
```

### Step 6b — Initialise Alembic

```bash
cd backend
alembic init alembic
```

This creates `alembic.ini` and `alembic/`. Edit `alembic.ini` to read the URL from the environment:

```ini
# alembic.ini — change this line:
sqlalchemy.url = driver://user:pass@localhost/dbname

# To this (reads from env at migration time):
sqlalchemy.url =
```

### Step 6c — Configure `alembic/env.py` for async SQLAlchemy

Replace the generated `alembic/env.py` with:

```python
"""Alembic environment — configured for async SQLAlchemy."""
import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from dotenv import load_dotenv

# Make sure the backend package is importable from the alembic/ subdirectory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

# Import the declarative Base that holds all table metadata
from database import Base  # noqa: E402

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://", 1),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Step 6d — Generate and apply the initial migration

```bash
# Auto-generate from the current models.py schema
alembic revision --autogenerate -m "initial schema: logo_generations table"

# Review the generated file in alembic/versions/ before applying
# Then apply:
alembic upgrade head
```

### Step 6e — Add to the production deployment checklist

In `PRODUCTION_DEPLOYMENT.md`, add this step before starting the server:

```bash
# Run before every deployment that touches models.py
alembic upgrade head
```

**Verification:**
```bash
# After running alembic upgrade head:
alembic current
# Should show: <revision_id> (head)

# Create a new column in LogoGeneration, autogenerate a migration:
# alembic revision --autogenerate -m "add style_raw column"
# Then apply — this should work without downtime (additive change):
# alembic upgrade head
```

---

## Corrected Mermaid Architecture Diagram

The original diagram in `mermaid_architecture` contains three inaccuracies:

| Line | Original | Problem |
|------|----------|---------|
| 40 | `node_http_routes →"delegates"→ node_llm_service` | Routes never instantiate or call `LLMService`. This relationship doesn't exist in `routers.py`. |
| 44 | `node_llm_service →"queues jobs"→ node_redis_queue` | `LLMService` has no reference to Redis. Queueing is done in `routers.py` via `redis.enqueue_job(...)`. |
| 49–54 | Workers shown calling external APIs, R2, and DB directly | Workers call `LLMService`, which in turn calls these. The diagram skips the service layer. |

Replace the edge section (lines 33–55) with the corrected version:

```mermaid
flowchart TD

subgraph group_frontend["Next.js frontend"]
  node_frontend_shell["App shell<br/>Next.js app<br/>[layout.tsx]"]
  node_frontend_page["Home page<br/>Next.js page<br/>[page.tsx]"]
  node_history_gallery["History gallery<br/>UI component<br/>[HistoryGallery.tsx]"]
  node_identity_preview["Identity preview<br/>UI component"]
end

subgraph group_backend["FastAPI backend"]
  node_app_entry["API entry<br/>FastAPI app<br/>[app.py]"]
  node_http_routes["HTTP routes<br/>Router layer<br/>[routers.py]"]
  node_request_models["API models<br/>Schemas<br/>[models.py]"]
  node_llm_service["LLM service<br/>Orchestration<br/>[services.py]"]
  node_prompt_config["Prompt config<br/>Templates<br/>[config.py]"]
  node_external_clients["Provider clients<br/>SDK clients<br/>[dependencies.py]"]
  node_async_db[("Database<br/>Async SQLAlchemy<br/>[database.py]")]
  node_rate_limiter{{"Rate limiter<br/>Throttle<br/>[limiter.py]"}}
  node_telemetry["Telemetry<br/>Logging/observability<br/>[observability.py]"]
  node_dalle_worker["DALL-E worker<br/>ARQ worker<br/>[dalle_worker.py]"]
  node_gemini_worker["Gemini worker<br/>ARQ worker<br/>[gemini_worker.py]"]
  node_shared_utils["Shared utils<br/>Helpers<br/>[utils.py]"]
end

subgraph group_infra["Runtime dependencies"]
  node_redis_queue["Redis queue<br/>ARQ/Redis"]
  node_postgres[("PostgreSQL<br/>Persistence")]
  node_r2_storage[("R2 storage<br/>Object storage")]
  node_openai_api["OpenAI API<br/>External AI"]
  node_google_genai["Google GenAI<br/>External AI"]
end

node_frontend_shell -->|"hosts"| node_frontend_page
node_frontend_page -->|"renders"| node_history_gallery
node_frontend_page -->|"renders"| node_identity_preview
node_frontend_page -->|"calls API"| node_http_routes
node_app_entry -->|"mounts"| node_http_routes
node_http_routes -->|"validates"| node_request_models
node_http_routes -->|"guards"| node_rate_limiter

node_http_routes -->|"enqueues jobs"| node_redis_queue

node_dalle_worker -->|"consumes"| node_redis_queue
node_gemini_worker -->|"consumes"| node_redis_queue

node_dalle_worker -->|"uses"| node_llm_service
node_gemini_worker -->|"uses"| node_llm_service

node_llm_service -->|"uses"| node_prompt_config
node_llm_service -->|"uses"| node_external_clients
node_llm_service -->|"uses"| node_shared_utils
node_llm_service -->|"persists metadata"| node_async_db
node_llm_service -->|"uploads artifacts"| node_r2_storage
node_llm_service -->|"calls"| node_openai_api
node_llm_service -->|"calls"| node_google_genai

node_telemetry -.->|"observes"| node_app_entry
```

**Summary of edge changes:**
- Removed: `node_http_routes →"delegates"→ node_llm_service`
- Changed: `node_llm_service →"queues jobs"→ node_redis_queue` **→** `node_http_routes →"enqueues jobs"→ node_redis_queue`
- Added: `node_dalle_worker →"uses"→ node_llm_service`
- Added: `node_gemini_worker →"uses"→ node_llm_service`
- Added: `node_llm_service →"calls"→ node_openai_api`
- Added: `node_llm_service →"calls"→ node_google_genai`
- Removed: worker-to-API, worker-to-R2, worker-to-DB direct edges (these go through `LLMService`)

---

## Deployment order for these fixes

Apply in this sequence to avoid breaking production:

```
1. Fix 4 (echo=True)          — zero risk, one-line change, deploy immediately
2. Fix 3 (JWT shared function) — same behaviour, purely structural, safe to deploy
3. Fix 2 (R2 raise on failure) — slightly increases visible failure rate (previously
                                   silent failures are now explicit); monitor for alerts
4. Fix 5 (RequestIDFilter)     — additive logging improvement, no behaviour change
5. Fix 6 (Alembic)             — add to requirements + alembic init; do NOT remove
                                   the create_all guard yet; run first migration on staging
6. Fix 1 (WebSocket Pub/Sub)   — largest change; test on staging under concurrent load
                                   before rolling to production
```

---

**Last updated:** June 2026  
**Review reference:** `ARCHITECTURE_REVIEW.md` and `ARCHITECTURE_REVIEW_DASHBOARD.html`
