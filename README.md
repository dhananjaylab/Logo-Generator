# 🎨 LogoForge AI: Brand Identity Architect

LogoForge AI is a modern, high-performance web application designed to generate deeply customizable, professional-grade logos using advanced Generative AI. It transitions beyond simple prompt-to-image generators by providing a structured design system and real-time visual identity previews.

---

## ✨ Features

- **Dual AI Generators**:
  - **GPT Image 2 (`gpt-image-2-2026-04-21`)**: High-fidelity logo generation with base64 image output.
  - **Gemini**: Lightning-fast iterations directly from Google's latest vision models.
- **Structured Customization**:
  - **Icon vs. Lettermark Modes**: Control the focus of your design.
  - **Artistic Styles**: Minimalist, Tech, Vintage, Abstract, Luxury, and more.
  - **Color Palettes**: Curated monochrome, ocean, sunset, forest, and neon schemes.
  - **Advanced Guidelines**: Specify taglines, typography, elements to include/avoid, and brand missions.
- **Real-time Experience**:
  - **WebSocket Progress**: Watch your generation advance stage-by-stage.
  - **Live Visual Identity Previews**: Instantly see your logo on business cards, app icons, and dark-mode UIs.
- **Persistence**:
  - **History Gallery**: Seamlessly load and reference past generations from a PostgreSQL-backed history.
  - **Cloudflare R2 Storage**: All designs are saved securely in high-performance cloud storage.
- **Security & Compliance**:
  - JWT tokens held in React memory only — never localStorage.
  - WebSocket auth via short-lived single-use tickets (not raw JWTs in URLs).
  - IP addresses stored as salted SHA-256 hashes, never raw.
  - Content moderation gate on every generation request (OpenAI Moderation API).
  - GDPR / CCPA right-to-deletion endpoint with automatic data-retention purge.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 16 (TypeScript, CSS Modules, Lucide React).
- **Backend**: FastAPI (Python 3.9+).
- **Asynchronous Tasks**: ARQ (Redis-backed task queueing).
- **Database**: PostgreSQL (SQLAlchemy + AsyncPG).
- **Storage**: Cloudflare R2 (Boto3 integration).
- **Real-time**: WebSockets for progress streaming.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.9+** and **Node.js 20+**
- **Redis** server (default port 6379)
- **PostgreSQL** database
- **Environment Keys**: Gemini API Key, OpenAI API Key, Cloudflare R2 Credentials.

### 2. Environment Setup

Create a `.env` file in the `backend/` directory by copying `.env.template`:

```bash
cp backend/.env.template backend/.env
```

Then fill in your real values. The critical variables are shown below with safe placeholder values — **never commit real secrets**.

```env
# AI API Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=sk-your_openai_api_key_here

# Gemini model override
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image

# Cloudflare R2
R2_ACCESS_KEY_ID=your_id
R2_SECRET_ACCESS_KEY=your_secret
R2_BUCKET_NAME=logo-forge
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_PUBLIC_DOMAIN=https://pub-<id>.r2.dev

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/logoforge

# Redis
REDIS_URL=redis://localhost:6379

# ARQ worker tuning
DALLE_WORKER_MAX_TRIES=3
DALLE_WORKER_TIMEOUT=100
DALLE_WORKER_MAX_JOBS=5
GEMINI_WORKER_MAX_TRIES=3
GEMINI_WORKER_TIMEOUT=60
GEMINI_WORKER_MAX_JOBS=10

# Per-user daily generation quota
USER_DAILY_QUOTA=50

# Prometheus multiprocess metrics
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

# Data retention (GDPR Article 5(1)(e))
DATA_RETENTION_DAYS=365
```

#### Security variables — local development only

> ⚠️ These variables must never appear in production or staging environments and must never be committed with real values.

```env
# Generate a unique value — never share or reuse:
#   python -c "import secrets; print(secrets.token_hex(32))"
DEV_TOKEN=replace-with-output-of-python-secrets-token-hex-32
ALLOW_DEV_TOKEN=true

# Salt for IP address pseudonymisation (GDPR / CCPA):
#   python -c "import secrets; print(secrets.token_hex(32))"
IP_HASH_SALT=replace-with-output-of-python-secrets-token-hex-32
```

#### Prometheus multiprocess: Local vs Production

- Local: use a writable temp folder, e.g. `/tmp/prometheus_multiproc` on macOS/Linux or `C:\tmp\prometheus_multiproc` on Windows.
- Production: use a shared runtime directory or mounted volume accessible by every API and worker process.
- Create the directory before starting the backend:
  ```bash
  mkdir -p /tmp/prometheus_multiproc
  ```

### 3. Start Backend & Workers

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run database migrations
alembic upgrade head

# 4. Start FastAPI server (terminal 1)
uvicorn app:app --reload --port 8000

# 5. Start generation workers (terminals 2 and 3)
arq openai_image_worker.WorkerSettings
arq gemini_worker.WorkerSettings

# 6. Start data-retention maintenance worker (terminal 4)
arq maintenance_worker.WorkerSettings
```

*API runs on: http://localhost:8000*

Useful backend endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/health` | Readiness and dependency checks |
| `GET /metrics` | Prometheus scraping |
| `GET /api/v1/admin/dlq?queue=dalle` | Dead-letter inspection |
| `DELETE /api/v1/me/data` | GDPR / CCPA user data erasure |

### 4. Start Frontend

```bash
cd next-frontend
npm install
npm run dev
```

*Frontend runs on: http://localhost:3000*

---

## 📖 Technical Architecture

LogoForge AI uses a modular, facade-based architecture to manage multiple AI generators while maintaining a clean API surface.

### 🧩 Core Modules

| Module | Purpose |
| :--- | :--- |
| **`app.py`** | FastAPI entry point, lifespan management, Redis pool with retry, CORS. |
| **`routers.py`** | API routes: generation, job status, history, GDPR deletion, WebSocket, DLQ. |
| **`services.py`** | `LLMService` facade orchestrating `GeminiService` and `OpenAIImageService`. Thread-local R2 client, magic-byte image validation, cost estimation. |
| **`models.py`** | Pydantic request/response models and `LogoGenerationParams` dataclass. |
| **`moderation.py`** | OpenAI Moderation API gate — runs on every generation request before enqueue. |
| **`dependencies.py`** | API client singletons (OpenAI, Gemini) and JWT/DEV_TOKEN auth dependency. |
| **`config.py`** | Design tokens, prompt templates, cost table, data retention constant. |
| **`database.py`** | Async SQLAlchemy setup. `LogoGeneration` and `AuditLog` ORM models. |
| **`repository.py`** | `LogoRepository` (save, delete) and `AuditRepository` (log, anonymise). |
| **`circuit_breaker.py`** | `RedisCircuitBreaker` — shared state across all processes via Redis keys. |
| **`maintenance_worker.py`** | ARQ cron-only worker: daily retention purge at 03:00 UTC. |
| **`prom_metrics.py`** | Shared Prometheus metric definitions (counters, histograms, gauges). |
| **`observability.py`** | `request_id_ctx` ContextVar and `metrics_middleware` for HTTP instrumentation. |
| **`logging_config.py`** | Structured JSON logging (production) / human-readable (dev), Sentry integration. |
| **`utils.py`** | `anonymise_ip()`, `sanitize_filename()`, path helpers. |

### 🧬 Generation Flows

#### GPT Image 2
1. `POST /api/v1/generate` receives and validates the request.
2. OpenAI Moderation API checks the user-supplied free-text fields.
3. Job is enqueued to `openai_image_queue`; `job_queue:{job_id}` key written to Redis.
4. Worker builds prompt via `build_logo_prompt()`, calls `OpenAIImageService.generate_logo()`.
5. Base64 response is decoded, validated via magic-byte prefix check, uploaded to R2.
6. Completion published to `job:complete:{job_id}` Redis channel; WebSocket delivers it to the client.

#### Gemini
1–3. Same as above (moderation, enqueue, job mapping).
4. Worker calls `GeminiService.generate_logo()`. If Gemini quota is exhausted, `LLMService` transparently falls back to the GPT Image 2 path using the same `LogoGenerationParams` object — no manual parameter reconstruction.
5. Image bytes validated via magic-byte prefix check, uploaded to R2.
6. Same WebSocket delivery.

#### Runtime fallback
- If the WebSocket connection drops, the frontend polls `GET /api/v1/jobs/{job_id}` every 2 s, using the same `job_queue:{job_id}` O(1) lookup internally.

---

## 🧪 Testing & Diagnostics

```bash
# Health and readiness
curl http://localhost:8000/api/v1/health

# Prometheus metrics
curl http://localhost:8000/metrics

# Frontend dev server
cd next-frontend && npm run dev
```

---

## 📊 Monitoring

Stakeholder-friendly Grafana assets live in [`monitoring/`](./monitoring).

- **Dashboard**: [`monitoring/grafana/dashboards/logoforge-stakeholder-dashboard.json`](./monitoring/grafana/dashboards/logoforge-stakeholder-dashboard.json)
- **Metrics endpoint**: `GET /metrics`
- **Health endpoint**: `GET /api/v1/health`

The dashboard covers seven panels across six operational questions:

| Panel | Question |
|---|---|
| Traffic | How many requests is the system handling? |
| Readiness | Are Redis, Postgres, OpenAI, and Gemini all healthy? |
| Latency | How long do generations and R2 uploads take? |
| Capacity | Are workers near their concurrency limits? |
| Reliability | How often do jobs fail, retry, or hit the DLQ? |
| Cost | What is the estimated USD spend per generator? |
| Safety | How many requests are blocked by content moderation? |

---

## 🛡️ Security & Privacy

| Feature | Implementation |
|---|---|
| JWT storage | React memory only (AuthContext) — never localStorage |
| WebSocket auth | Short-lived single-use tickets via `POST /ws/ticket`, not raw JWTs in URLs |
| DEV_TOKEN bypass | Blocked unconditionally in `production` and `staging` environments |
| IP addresses | Salted SHA-256 hash (16 hex chars) — raw IP never stored or logged |
| Content moderation | OpenAI Moderation API on every generation request, before enqueue |
| Data retention | Configurable `DATA_RETENTION_DAYS` enforced by daily maintenance cron |
| Right to erasure | `DELETE /api/v1/me/data` — hard-deletes rows and R2 objects, anonymises audit trail |

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.
