# Developer Migration Guide - Post-Audit Changes

> Guide for updating your local environment and understanding breaking changes

## Quick Start

### 1. Update Backend Dependencies
```bash
cd backend
pip install -r requirements.txt --upgrade
```

**New Packages Added**:
- `google-genai>=1.0.0` (was 0.3.0)
- `sentry-sdk>=1.40.0` (error tracking)
- `python-json-logger>=2.0.7` (structured logging)

### 2. Update Environment Variables

Copy the new template:
```bash
cp backend/.env.example backend/.env
```

**New Required Variables**:
```bash
ENV=development                  # Set to 'production' in prod
ALLOWED_ORIGINS=http://localhost:3000  # Your frontend URL(s)
CLERK_AUDIENCE=http://localhost:3000   # JWT audience (usually same as frontend)
```

**Already Existing** (Make sure these are set):
```bash
CLERK_JWKS_URL=...          # Clerk configuration
OPENAI_API_KEY=...          # DALL-E
GEMINI_API_KEY=...          # Gemini
REDIS_URL=...               # Job queue
DATABASE_URL=...            # PostgreSQL
```

### 3. Test Locally

```bash
# Terminal 1: Start backend
cd backend
python -m uvicorn app:app --reload

# Terminal 2: Start Redis (if not running)
redis-server

# Terminal 3: Start workers
cd backend
python -m arq dalle_worker.WorkerSettings
# In another terminal:
python -m arq gemini_worker.WorkerSettings

# Terminal 4: Start frontend
cd next-frontend
npm run dev

# Visit http://localhost:3000
```

---

## Breaking Changes Explained

### 1. CORS Configuration

**What Changed**:
- Removed: `allow_origins=["*"]` wildcard
- Added: `ALLOWED_ORIGINS` env var for explicit allowlist

**What You Need to Do**:
```bash
# In .env:
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

**Test It**:
```bash
curl -X OPTIONS http://localhost:8000/api/history \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"
# Should see: Access-Control-Allow-Origin: http://localhost:3000
```

---

### 2. Authentication Required on Protected Endpoints

**What Changed**:
- `/api/history` - Now requires Bearer token
- `/ws/progress/{job_id}` - Now requires token param

**What You Need to Do**:

If using the provided frontend: ✅ No changes needed (already handles auth)

If building custom client:
```python
# Add Authorization header to /history request
headers = {
    "Authorization": f"Bearer {token}"
}
response = requests.get("http://localhost:8000/api/history", headers=headers)

# WebSocket: pass token in query param
async with websockets.connect(
    f"ws://localhost:8000/api/ws/progress/{job_id}?token={token}"
) as ws:
    message = await ws.recv()
```

**Test It**:
```bash
# Without token - should fail
curl http://localhost:8000/api/history
# Returns: 403 Unauthorized

# With token - should work
curl -H "Authorization: Bearer $DEV_TOKEN" \
  http://localhost:8000/api/history
# Returns: [list of jobs]
```

---

### 3. Job Ownership Enforcement

**What Changed**:
- Users can only see their own jobs
- Job enumeration attacks prevented

**What This Means**:
```python
# Before: Could see all jobs by guessing UUIDs
GET /api/jobs/any-uuid-here  # ✅ Worked if job existed

# After: Can only see YOUR jobs
GET /api/jobs/their-uuid     # ❌ Returns 403 if not your job
GET /api/jobs/your-uuid      # ✅ Works if you created it
```

**Test It**:
```bash
# Generate 2 logos with same token
# They'll both succeed and show in /history

# Try to access another user's job (use different token)
curl -H "Authorization: Bearer $OTHER_TOKEN" \
  http://localhost:8000/api/jobs/first-users-job-id
# Returns: 403 Forbidden
```

---

### 4. Dev Token Only in Development

**What Changed**:
- `DEV_TOKEN` environment variable still works in dev
- Automatically rejected in production when `ENV=production`

**What You Need to Do**:

In development (local):
```bash
ENV=development
DEV_TOKEN=logo-forge-dev-2026
# ✅ Works fine
```

In production:
```bash
ENV=production
DEV_TOKEN=...  # ❌ Will be rejected even if set
# Use proper Clerk JWT instead
```

---

### 5. JWT Audience Validation

**What Changed**:
- JWT `aud` claim now validated in production
- Prevents token reuse across services

**What You Need to Do**:

Set `CLERK_AUDIENCE`:
```bash
# This should be your API URL (or frontend URL)
CLERK_AUDIENCE=http://localhost:3000

# In production:
CLERK_AUDIENCE=https://api.yourdomain.com
```

**How to Check Your Token**:
```bash
# Decode your JWT (try jwt.io)
# Look for the "aud" (audience) claim
# It should match CLERK_AUDIENCE

{
  "aud": "http://localhost:3000",  # Should match CLERK_AUDIENCE
  "sat": 1234567890,
  "sub": "user_123",
  ...
}
```

---

## New Features to Use

### 1. Structured Logging

**How to Use**:
```python
from logging_config import get_logger

logger = get_logger(__name__)

logger.info(f"Processing job {job_id}")
logger.warning(f"Slow operation: {duration}s")
logger.error(f"Failed to upload: {error}")
```

**Output Format**:
- Development: `[2026-04-03 14:30:45] INFO     [app.py:100] Processing job xyz`
- Production: `{"timestamp":"2026-04-03T14:30:45Z","level":"INFO","message":"Processing job xyz"}`

### 2. Error Tracking (Sentry)

**How to Use**:
```bash
# Set in .env:
SENTRY_DSN=https://your-key@sentry.io/project-id
```

Errors are automatically captured:
- Unhandled exceptions
- 500 responses
- Performance traces

Manual capture:
```python
import sentry_sdk
sentry_sdk.capture_exception(error)
sentry_sdk.capture_message("Custom event")
```

### 3. Metrics Collection

**How to Use**:
```python
from observability import record_generation_latency, record_error

# Record success
elapsed = time.time() - start
record_generation_latency(elapsed, "dalle-3", "success")

# Record error
record_error("OpenAI API Error", "generate_dalle_endpoint")
```

**View Metrics**:
```python
from observability import metrics
summary = metrics.get_metric_summary("generation_latency_seconds")
print(summary)
# {
#   "count": 42,
#   "min": 3.2,
#   "max": 15.1,
#   "avg": 8.5,
#   "latest": 9.0
# }
```

---

## Code Changes Reference

### Files Modified

| File | Changes | Impact |
|------|---------|--------|
| [app.py](backend/app.py) | Added logging init, metrics middleware, CORS config | Security, Observability |
| [routers.py](backend/routers.py) | Added auth to endpoints, job ownership checks, WS backoff | Security, Reliability |
| [dependencies.py](backend/dependencies.py) | DEV_TOKEN gating, verify_aud enabled, structured logging | Security |
| [limiter.py](backend/limiter.py) | Redis-only config, production validation | Reliability |
| [dalle_worker.py](backend/dalle_worker.py) | Context reuse, result TTL, logging | Performance, Maintainability |
| [gemini_worker.py](backend/gemini_worker.py) | Context reuse, result TTL, logging | Performance, Maintainability |
| [requirements.txt](backend/requirements.txt) | Updated google-genai, added sentry/logging | Security, Observability |

### Files Added

| File | Purpose |
|------|---------|
| [logging_config.py](backend/logging_config.py) | Structured logging setup |
| [observability.py](backend/observability.py) | Metrics collection |
| [.env.example](backend/.env.example) | Env var documentation |
| [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) | Prod setup guide |
| [AUDIT_FIXES_SUMMARY.md](AUDIT_FIXES_SUMMARY.md) | Detailed change log |

---

## Testing Changes Locally

### Test 1: CORS is Enforced
```bash
# Should work (same origin)
curl -X GET http://localhost:8000/api/history \
  -H "Authorization: Bearer $DEV_TOKEN"
# ✅ Returns 200

# Should fail (wrong origin)
curl -X GET http://localhost:8000/api/history \
  -H "Authorization: Bearer $DEV_TOKEN" \
  -H "Origin: http://attacker.com"
# Check if Access-Control-Allow-Origin header is NOT present for attacker.com
```

### Test 2: Auth is Required
```bash
# Without token
curl http://localhost:8000/api/history
# ❌ Returns 403 Unauthorized

# With token
curl -H "Authorization: Bearer $DEV_TOKEN" \
  http://localhost:8000/api/history
# ✅ Returns 200 with job list
```

### Test 3: Job Ownership Enforced
```bash
# Generate logo, get job_id
JOB_ID=$(curl -H "Authorization: Bearer $TOKEN1" \
  -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Test","generator":"dalle-3","style":"minimalist","palette":"monochrome"}' \
  | jq -r .job_id)

# Access with same user - should work
curl -H "Authorization: Bearer $TOKEN1" \
  http://localhost:8000/api/jobs/$JOB_ID
# ✅ Returns job status

# Access with different user - should fail
curl -H "Authorization: Bearer $TOKEN2" \
  http://localhost:8000/api/jobs/$JOB_ID
# ❌ Returns 403 Forbidden
```

### Test 4: WebSocket Auth Required
```bash
import websockets
import json

# Try without token - should fail
try:
    async with websockets.connect("ws://localhost:8000/api/ws/progress/some-job-id") as ws:
        pass
except Exception as e:
    print("Expected error:", e)

# With token - should work
async with websockets.connect(
    f"ws://localhost:8000/api/ws/progress/{job_id}?token={token}"
) as ws:
    message = await ws.recv()
    print(json.loads(message))
```

### Test 5: Logging Works
```bash
# Run backend with debug logging
ENV=development python -m uvicorn app:app --reload

# Make a request
curl http://localhost:8000/api/health

# Check console output - should see structured logs:
# [2026-04-03 14:30:45] INFO     [app.py:50] ✓ Database initialized
# [2026-04-03 14:30:45] INFO     [app.py:51] ✓ Redis pool created
```

---

## Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'logging_config'"
```bash
# Solution: Make sure you're running from backend directory
cd backend
python -m uvicorn app:app
```

### ❌ "CORS Error: No 'Access-Control-Allow-Origin' header"
```bash
# Solution: Check ALLOWED_ORIGINS env var
echo $ALLOWED_ORIGINS
# Should include your frontend URL

# If missing:
export ALLOWED_ORIGINS=http://localhost:3000
python -m uvicorn app:app --reload
```

### ❌ "KeyError: 'DEV_TOKEN' at startup"
```bash
# Solution: Set DEV_TOKEN in .env or export it
export DEV_TOKEN=logo-forge-dev-2026
# Or add to .env:
# DEV_TOKEN=logo-forge-dev-2026
```

### ❌ WebSocket connection fails immediately
```bash
# Check if token is being passed correctly in query string
# Try in browser console:
const ws = new WebSocket(`ws://localhost:8000/api/ws/progress/${jobId}?token=${encodeURIComponent(token)}`);
ws.onclose = () => console.log("Closed:", ws.closeCode, ws.closeReason);

# Code 1008 = Policy Violation (usually auth failure)
# Make sure token is valid and not expired
```

### ❌ "Redis connection refused"
```bash
# Solution: Check Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server

# Or check REDIS_URL is correct
echo $REDIS_URL
# Should be something like: redis://localhost:6379
```

---

## Rollback Plan

If you need to go back to the previous version:

```bash
# 1. Revert code
git checkout HEAD~1

# 2. Downgrade packages
pip install -r backend/requirements.txt
# This will downgrade google-genai to 0.3.0 automatically

# 3. Remove new env vars (or keep them - they're ignored)
# ALLOWED_ORIGINS, CLERK_AUDIENCE, SENTRY_DSN, LOG_FILE

# 4. Restart backend
python -m uvicorn app:app --reload
```

**Note**: If you had added new database fields or migrations, rollback may require reversing those too.

---

## Questions & Support

- 🐛 **Bug**: Check [AUDIT_FIXES_SUMMARY.md](AUDIT_FIXES_SUMMARY.md) for change details
- 📚 **Documentation**: See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for deployment
- 🔍 **Code Changes**: Run `git diff HEAD~1 backend/` to see all changes
- 💬 **Discussion**: Open an issue with specific error messages

---

**Last Updated**: April 3, 2026  
**Version**: 2.1.0 (Production-Ready)
