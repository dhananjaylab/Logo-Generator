# 🎨 LogoForge AI: Brand Identity Architect

LogoForge AI is a modern, high-performance web application designed to generate deeply customizable, professional-grade logos using advanced Generative AI. It transitions beyond simple prompt-to-image generators by providing a structured design system and real-time visual identity previews.

---

## ✨ Features

- **Dual AI Generators**:
  - **GPT Image 2 (`gpt-image-2-2026-04-21`)**: High-fidelity logo generation with base64 image output.
  - **Gemini**: Lightning-fast iterations directly from Google's latest vision models.
- **Structured Customization**:
  - **Icon vs. Lettermark Modes**: Control the focus of your design.
  - **Artistic Styles**: Minimalist, Tech, Vintage, Abstract, luxury, and more.
  - **Color Palettes**: Curated monochrome, ocean, sunset, forest, and neon schemes.
  - **Advanced Guidelines**: Specify taglines, typography, elements to include/avoid, and brand missions.
- **Real-time Experience**:
  - **WebSocket Progress**: Watch your generation advance stage-by-stage.
  - **Live Visual Identity Previews**: Instantly see your logo on business cards, app icons, and dark-mode UIs.
- **Persistence**:
  - **History Gallery**: Seamlessly load and reference past generations from a PostgreSQL-backed history.
  - **Cloudflare R2 Storage**: All designs are saved securely in high-performance cloud storage.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 15 (TypeScript, CSS Modules, Lucide React).
- **Backend**: FastAPI (Python 3.9+).
- **Asynchronous Tasks**: ARQ (Redis-backed task queueing).
- **Database**: PostgreSQL (SQLAlchemy + AsyncPG).
- **Storage**: Cloudflare R2 (Boto3 integration).
- **Real-time**: WebSockets for progress streaming.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.9+** and **Node.js 18+**
- **Redis** server (Running on default port 6379)
- **PostgreSQL** database
- **Environment Keys**: Gemini API Key, OpenAI API Key, Cloudflare R2 Credentials, Clerk JWT Key.

### 2. Environment Setup
Create a `.env` file in the `backend/` directory. The app now supports the versioned API, worker tuning, and Prometheus multiprocess metrics:
```env
# AI API Keys
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

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

# Prometheus multiprocess metrics
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc

# Security (Development)
DEV_TOKEN=logo-forge-dev-2026
```

#### Prometheus multiprocess: Local vs Production

- Local: use a writable temp folder on your machine, for example `C:\tmp\prometheus_multiproc` on Windows or `/tmp/prometheus_multiproc` on macOS/Linux.
- Production: use a shared runtime directory or mounted volume that every API and worker process can access. Keep it outside the source tree.
- The API server and all workers must read the same `PROMETHEUS_MULTIPROC_DIR` value for metrics aggregation to work correctly.
- Create the directory before starting the backend processes, or have your deploy/startup script create it automatically.
- Do not point this variable at a repo folder unless you also exclude it from version control.

### 3. Start Backend & Workers
In the `backend/` directory:
```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Prepare Prometheus multiprocess directory
$env:PROMETHEUS_MULTIPROC_DIR = "$env:TEMP\prometheus_multiproc"
New-Item -ItemType Directory -Force $env:PROMETHEUS_MULTIPROC_DIR | Out-Null

echo $env:PROMETHEUS_MULTIPROC_DIR

# 4. Start FastAPI server (in one terminal)
uvicorn app:app --reload --port 8000

# 5. Start workers (in separate terminals)
arq openai_image_worker.WorkerSettings
arq gemini_worker.WorkerSettings
```
*API runs on: http://localhost:8000*

Useful backend endpoints:
- `GET /api/v1/health` for readiness and dependency checks
- `GET /metrics` for Prometheus scraping
- `GET /api/v1/admin/dlq?queue=dalle` for dead-letter inspection

### 4. Start Frontend
In the `next-frontend/` directory:
```bash
# 1. Install dependencies
npm install

# 2. Start Next.js dev server
npm run dev
```
*Frontend runs on: http://localhost:3000*

---

## 📖 Technical Architecture

LogoForge AI uses a modular, facade-based architecture to manage multiple AI generators while maintaining a clean API surface.

### 🧩 Core Modules

| Module | Purpose |
| :--- | :--- |
| **`app.py`** | FastAPI entry point, lifespan management, and CORS configuration. |
| **`routers.py`** | API route handlers for health checks, logo generation, DLQ inspection, and WebSocket progress streaming. |
| **`services.py`** | The business logic layer, featuring the `LLMService` (Facade) which orchestrates `GeminiService` and `OpenAIImageService`. |
| **`models.py`** | Pydantic models for request/response validation and type safety. |
| **`dependencies.py`** | Managed singleton for API clients (OpenAI, Google GenAI). |
| **`config.py`** | Centralized design tokens (styles, palettes) and prompt templates. |
| **`database.py`** | Async SQLAlchemy setup for persistent generation history. |
| **`repository.py`** | Persistence abstraction for saving generation history. |
| **`circuit_breaker.py`** | Per-process circuit breakers for OpenAI, Gemini, and R2. |
| **`prom_metrics.py`** | Shared Prometheus metric definitions for workers and API. |

### 🛠️ Module Dependencies

```mermaid
graph TD
    A[app.py] --> B[routers.py]
    B --> C[models.py]
    B --> D[services.py]
    B --> E[dependencies.py]
    D --> F[config.py]
    D --> G[utils.py]
    D --> H[External APIs]
```

### 🧬 Generation Flows

#### GPT Image 2
1.  **FastAPI** receives the request and validates via Pydantic.
2.  **LLMService** builds a logo-specific prompt with hard output constraints first.
3.  **LLMService** calls `OpenAIImageService.generate_logo()` with `model="gpt-image-2-2026-04-21"`.
4.  The base64 image payload is decoded, uploaded to **Cloudflare R2**, and the public URL is returned.

#### Gemini (Direct)
1.  **FastAPI** validates the request.
2.  **LLMService** calls `GeminiService.generate_logo()` directly using the configured `GEMINI_IMAGE_MODEL` value.
3.  The generated image is processed via **Pillow**, uploaded to **R2**, and the public link is returned.

#### Runtime Flow
1.  Client calls `POST /api/v1/generate`.
2.  Backend enqueues either `generate_openai_image_task` or `generate_gemini_task` onto the matching ARQ queue.
3.  Worker publishes completion or failure to Redis pub/sub for the WebSocket listener at `/api/v1/ws/progress/{job_id}`.
4.  The frontend can fall back to `GET /api/v1/jobs/{job_id}` if WebSocket delivery is interrupted.

---

## 🧪 Testing & Diagnostics

The backend includes a comprehensive test suite for validating API clients and generation pipelines.

```bash
# Run all backend unit tests
cd backend
python -m pytest test_backend.py -v
```

Common manual checks:
```bash
# Health and readiness
curl http://localhost:8000/api/v1/health

# Prometheus metrics
curl http://localhost:8000/metrics

# Frontend dev server
cd next-frontend
npm run dev
```

## 📊 Monitoring

Stakeholder-friendly Grafana assets live in [`monitoring/`](./monitoring).

- Dashboard: [`monitoring/grafana/dashboards/logoforge-stakeholder-dashboard.json`](./monitoring/grafana/dashboards/logoforge-stakeholder-dashboard.json)
- Metrics endpoint: `GET /metrics`
- Health endpoint: `GET /api/v1/health`

The dashboard is designed around five executive questions:
- Traffic
- Latency
- Reliability
- Readiness
- Capacity

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.
