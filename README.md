# 🎨 LogoForge AI: Brand Identity Architect

LogoForge AI is a modern, high-performance web application designed to generate deeply customizable, professional-grade logos using advanced Generative AI. It transitions beyond simple prompt-to-image generators by providing a structured design system and real-time visual identity previews.

---

## ✨ Features

- **Dual AI Generators**:
  - **DALL-E 3**: High-fidelity, artistic excellence with GPT-4 prompt refinement.
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
Create a `.env` file in the `backend/` directory:
```env
# AI API Keys
GEMINI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

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

# Security (Development)
DEV_TOKEN=logo-forge-dev-2026
```

### 3. Start Backend & Workers
In the `backend/` directory:
```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start FastAPI server (in one terminal)
uvicorn app:app --reload --port 8000

# 4. Start workers (in separate terminals)
arq dalle_worker.WorkerSettings
arq gemini_worker.WorkerSettings
```
*API runs on: http://localhost:8000*

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
| **`routers.py`** | API route handlers for health checks and logo generation. |
| **`services.py`** | The business logic layer, featuring the `LLMService` (Facade) which orchestrates `GeminiService` and `DALLEService`. |
| **`models.py`** | Pydantic models for request/response validation and type safety. |
| **`dependencies.py`** | Managed singleton for API clients (OpenAI, Google GenAI). |
| **`config.py`** | Centralized design tokens (styles, palettes) and prompt templates. |
| **`database.py`** | Async SQLAlchemy setup for persistent generation history. |

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

#### DALL-E 3 (Refined)
1.  **FastAPI** receives the request and validates via Pydantic.
2.  **LLMService** calls `GeminiService.refine_prompt()` to turn raw user inputs into a professional design prompt.
3.  **LLMService** calls `DALLEService.generate_logo()` with the refined prompt.
4.  The binary image is uploaded to **Cloudflare R2**, and the URL is returned.

#### Gemini (Direct)
1.  **FastAPI** validates the request.
2.  **LLMService** calls `GeminiService.generate_logo()` directly using the `gemini-2.0-flash-exp` model.
3.  The generated image is processed via **Pillow**, uploaded to **R2**, and the public link is returned.

---

## 🧪 Testing & Diagnostics

The backend includes a comprehensive test suite for validating API clients and generation pipelines.

```bash
# Run all backend unit tests
cd backend
python -m pytest test_backend.py -v
```

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.